"""FastAPI app entry point (IMPLEMENTATION.md §1.4).

Wires the startup pipeline and schemas into the /api/* endpoints and mounts the
built frontend. Imports and result-dict access are adapted to the real model
modules (per-stage tally dict, display-name-keyed ratings, Elo-based
match_probabilities).
"""

import os
import threading
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from api.models import (
    MatchupRequest,
    MatchupResult,
    OddsRow,
    StatusResponse,
    TeamRow,
)
from api.live_results import (
    clear_cache,
    get_completed_matches,
    get_last_result_date,
)
from api.pipeline import get_state, initialise, rerun
from simulation import match_probabilities
from worldcup2026 import WC2026_TEAMS, find_team

# Mapping from the OddsRow fields to the per-stage keys in the simulation
# results dict (see simulation.run_simulations).
_STAGE_KEYS = {
    "p_r16": "round_of_16",
    "p_qf": "quarter_finals",
    "p_sf": "semi_finals",
    "p_final": "finals",
    "p_title": "titles",
}


# ── Startup ───────────────────────────────────────────────────────────────────

# Simulations per tournament — lower it on small/free hosts with WC_SIMS.
_SIMS = int(os.environ.get("WC_SIMS", 10_000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kick off the cold start in a background thread and return immediately, so
    # the server accepts connections (and health checks pass) while the pipeline
    # warms up. /api/status reports ready=false until it finishes; the frontend
    # shows its loading screen in the meantime.
    threading.Thread(target=lambda: initialise(n_sims=_SIMS), daemon=True).start()
    yield


app = FastAPI(title="World Cup Oracle API", lifespan=lifespan)


# ── Helpers ───────────────────────────────────────────────────────────────────

def require_ready():
    state = get_state()
    if not state.ready:
        raise HTTPException(503, "Simulation not yet ready — try again shortly.")
    return state


def _parse_score(score: str) -> tuple[int, int]:
    """'2-1' -> (2, 1). Falls back to (0, 0) on any malformed value."""
    try:
        a, b = score.split("-", 1)
        return int(a), int(b)
    except (ValueError, AttributeError):
        return 0, 0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/status", response_model=StatusResponse)
def status():
    s = get_state()
    return StatusResponse(
        ready=s.ready,
        running=s.running,
        n_sims=s.n_sims,
        cached_at=s.cached_at,
        last_result_date=get_last_result_date(),
    )


@app.get("/api/teams", response_model=list[TeamRow])
def teams():
    """All 48 World Cup teams (name, code, flag, group, Elo)."""
    state = require_ready()
    return [
        TeamRow(
            code=t.code,
            name=t.name,
            flag=t.flag,
            group=t.group,
            elo=int(state.ratings.get(t.name, 0)),
        )
        for t in WC2026_TEAMS
    ]


def _eliminated_teams() -> set[str]:
    """Teams with a completed knockout-stage loss (decided in normal time).

    Note: does not yet handle shootout winners on a draw, nor group-stage
    elimination — extend live_results.csv (and this check) when that data lands.
    """
    eliminated: set[str] = set()
    for m in get_completed_matches():
        if m["stage"] in ("r32", "r16", "qf", "sf") and m["score_a"] != m["score_b"]:
            loser = m["team_a"] if m["score_a"] < m["score_b"] else m["team_b"]
            t = find_team(loser)
            eliminated.add(t.name if t else loser)
    return eliminated


@app.get("/api/odds", response_model=list[OddsRow])
def odds():
    """Per-team stage probabilities, sorted by title odds descending.

    Teams already eliminated by a real result show 0% across all stages rather
    than a stale pre-tournament number.
    """
    state = require_ready()
    n = state.n_sims or 1
    eliminated = _eliminated_teams()
    rows = []
    for t in WC2026_TEAMS:
        if t.name in eliminated:
            probs = {field: 0.0 for field in _STAGE_KEYS}
        else:
            probs = {
                field: round(state.results.get(stage, {}).get(t.name, 0) / n * 100, 1)
                for field, stage in _STAGE_KEYS.items()
            }
        rows.append(
            OddsRow(
                code=t.code,
                name=t.name,
                flag=t.flag,
                group=t.group,
                elo=int(state.ratings.get(t.name, 0)),
                **probs,
            )
        )
    return sorted(rows, key=lambda r: r.p_title, reverse=True)


@app.post("/api/matchup", response_model=MatchupResult)
def matchup(body: MatchupRequest):
    """Head-to-head prediction via a 50,000-trial Monte Carlo (simulation.py)."""
    state = require_ready()
    team_a = find_team(body.team_a)
    team_b = find_team(body.team_b)
    if team_a is None or team_b is None:
        raise HTTPException(404, "One or both teams not found.")
    if team_a.name == team_b.name:
        raise HTTPException(400, "Pick two different teams.")

    elo_a = state.ratings.get(team_a.name, 1000)
    elo_b = state.ratings.get(team_b.name, 1000)
    r = match_probabilities(elo_a, elo_b, trials=50_000)
    score_a, score_b = _parse_score(r["most_likely_score"])

    return MatchupResult(
        win_a=round(r["p_win_a"] * 100, 1),
        draw=round(r["p_draw"] * 100, 1),
        win_b=round(r["p_win_b"] * 100, 1),
        xg_a=round(r["xg_a"], 2),
        xg_b=round(r["xg_b"], 2),
        score_a=score_a,
        score_b=score_b,
    )


@app.post("/api/refresh-results")
def refresh_results(background_tasks: BackgroundTasks):
    """Reload live_results.csv AND re-check the upstream historical dataset,
    then re-apply Elo, refit the model, and re-simulate.

    Use after editing live_results.csv (Option C) or from a scheduled job
    (Option A). Runs the full pipeline in the background because new Elo ratings
    change the odds — a re-sim is required for them to take effect. Passes
    force_refresh so martj42/international_results is re-fetched regardless of
    cache age (a conditional GET, so it's cheap when nothing changed).
    """
    if get_state().running:
        raise HTTPException(409, "A simulation is already running.")
    clear_cache()  # live_results.csv
    background_tasks.add_task(initialise, get_state().n_sims or 10_000, force_refresh=True)
    return {"message": "Live + historical results reloaded; pipeline refreshing."}


@app.get("/api/bracket")
def bracket():
    """The modal predicted bracket path. Implemented in Phase 3 (api/bracket.py)."""
    state = require_ready()
    try:
        from api.bracket import build_bracket
    except ImportError:
        raise HTTPException(501, "Bracket extractor not yet implemented (Phase 3).")
    try:
        return build_bracket(state.ratings, state.results, state.n_sims)
    except NotImplementedError:
        raise HTTPException(501, "Bracket extractor not yet implemented (Phase 3).")


@app.post("/api/rerun")
def rerun_simulation(background_tasks: BackgroundTasks, n_sims: int = 10_000):
    """Kick off a background re-run of the Monte Carlo simulation."""
    if get_state().running:
        raise HTTPException(409, "A simulation is already running.")
    background_tasks.add_task(rerun, n_sims)
    return {"message": f"Re-run started with {n_sims} simulations."}


# ── Static file serving ───────────────────────────────────────────────────────
# Mounted after the API routes so /api/* takes precedence. Only present once the
# frontend has been built (Phase 8).

DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(DIST):
    app.mount("/", StaticFiles(directory=DIST, html=True), name="static")
