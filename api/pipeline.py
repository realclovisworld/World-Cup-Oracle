"""Wraps the Elo -> Poisson -> Monte Carlo pipeline (IMPLEMENTATION.md §1.2).

Call ``initialise(n_sims)`` once at startup; call ``get_state()`` to read
results. Call ``rerun(n_sims)`` to refresh only the Monte Carlo step (the Elo
replay and the fitted goal model are cached and reused).

This is the only module that imports the existing read-only model files. The
spec's placeholder signatures have been corrected to the real ones:
    elo.compute_elo_ratings(record_history=True) -> (ratings, count, history)
    elo.get_wc_team_ratings(all_ratings)         -> {display_name: int}
    poisson_model.train_poisson_model(history)   -> PoissonGoalModel
    simulation.run_simulations(ratings, num_simulations) -> per-stage dict
"""

import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

# Existing modules live in the project root, one level up from api/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from elo import compute_elo_ratings, expected_score, get_wc_team_ratings  # noqa: E402
from poisson_model import train_poisson_model  # noqa: E402
from simulation import run_simulations, set_goal_model  # noqa: E402
from worldcup2026 import find_team  # noqa: E402

# Importance multiplier for a World Cup match (matches elo.k_factor's WC value).
_WC_K = 60.0


def _apply_live_results(ratings: dict, history: list) -> tuple[dict, list]:
    """Replay completed 2026 matches through Elo, after the historical replay.

    elo.py has no extracted single-match update function (the update is inline in
    compute_elo_ratings), and the model files are read-only — so this mirrors
    that exact update using elo.expected_score. World Cup matches are neutral
    (no +75 home bonus) and use K=60, per ARCHITECTURE.md.

    Mutates ``ratings`` (display-name keyed) in place and appends one training
    row per match to ``history`` in the schema poisson_model.build_training_table
    expects (home_elo/away_elo/neutral/home_score/away_score).
    """
    from api.live_results import get_completed_matches

    for m in sorted(get_completed_matches(), key=lambda x: x["date"]):
        a = _resolve(m["team_a"], ratings)
        b = _resolve(m["team_b"], ratings)
        if a is None or b is None:
            continue  # team name not among the 48 — skip
        elo_a, elo_b = ratings[a], ratings[b]
        sa, sb = m["score_a"], m["score_b"]

        # Pre-match snapshot becomes Poisson training data (no leakage).
        history.append(
            {"home_elo": elo_a, "away_elo": elo_b, "neutral": True,
             "home_score": sa, "away_score": sb}
        )

        exp_a = expected_score(elo_a, elo_b)  # neutral: no home adjustment
        exp_b = 1 - exp_a
        if sa > sb:
            act_a, act_b = 1.0, 0.0
        elif sa < sb:
            act_a, act_b = 0.0, 1.0
        else:
            act_a, act_b = 0.5, 0.5
        gd = abs(sa - sb)
        gd_mult = 1.0 if gd <= 1 else 1.5 if gd == 2 else 1.75

        ratings[a] = elo_a + _WC_K * gd_mult * (act_a - exp_a)
        ratings[b] = elo_b + _WC_K * gd_mult * (act_b - exp_b)
    return ratings, history


def _resolve(name: str, ratings: dict) -> str | None:
    """Map a live-results team name to its key in the display-name ratings."""
    if name in ratings:
        return name
    t = find_team(name)
    return t.name if t and t.name in ratings else None


@dataclass
class AppState:
    ratings: dict = field(default_factory=dict)  # {display_name: elo:int}
    results: dict = field(default_factory=dict)  # per-stage {stage: {name: count}}
    model: object = None
    n_sims: int = 0
    ready: bool = False
    running: bool = False
    cached_at: Optional[float] = None  # time.time() of last run


_state = AppState()
_lock = threading.Lock()


def get_state() -> AppState:
    return _state


def initialise(n_sims: int = 10_000, force_refresh: bool = False) -> None:
    """Full cold start: Elo replay + goal-model fit + simulation.

    ``force_refresh`` re-checks the upstream historical dataset (bypassing the
    cache-age window) — used by /api/refresh-results.
    """
    with _lock:
        _state.running = True
        _state.ready = False
    try:
        all_ratings, _match_count, history = compute_elo_ratings(
            record_history=True, force_refresh=force_refresh
        )
        ratings = get_wc_team_ratings(all_ratings)
        ratings, history = _apply_live_results(ratings, history)  # live 2026 results
        model = train_poisson_model(history)
        set_goal_model(model)
        results = run_simulations(ratings, n_sims)
        with _lock:
            _state.ratings = ratings
            _state.model = model
            _state.results = results
            _state.n_sims = n_sims
            _state.cached_at = time.time()
            _state.ready = True
    finally:
        with _lock:
            _state.running = False


def rerun(n_sims: int = 10_000) -> None:
    """Re-run only the Monte Carlo step; Elo and the goal model are reused."""
    with _lock:
        if not _state.ready:
            raise RuntimeError("Pipeline not yet initialised — call initialise() first.")
        _state.running = True
    try:
        results = run_simulations(_state.ratings, n_sims)
        with _lock:
            _state.results = results
            _state.n_sims = n_sims
            _state.cached_at = time.time()
    finally:
        with _lock:
            _state.running = False
