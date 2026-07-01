"""Precompute the app's data into static JSON for the Vercel static build.

Runs the full Elo -> Poisson -> Monte Carlo pipeline once and writes
frontend/public/data/{meta,teams,odds,bracket}.json. The frontend reads those
files directly (no backend), and does head-to-head prediction in the browser
from the model coefficients in meta.json.

Run from the repo root:  python scripts/build_data.py
Regenerate + redeploy whenever you want to refresh the snapshot.
"""

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import api.pipeline as pipeline  # noqa: E402
from api.bracket import build_bracket  # noqa: E402
from api.live_results import get_completed_matches, get_last_result_date  # noqa: E402
from poisson_model import ELO_DIFF_SCALE  # noqa: E402
from worldcup2026 import WC2026_TEAMS, find_team  # noqa: E402

OUT_DIR = os.path.join(ROOT, "frontend", "public", "data")
STAGE_KEYS = {
    "p_r16": "round_of_16",
    "p_qf": "quarter_finals",
    "p_sf": "semi_finals",
    "p_final": "finals",
    "p_title": "titles",
}


def _eliminated() -> set:
    out = set()
    for m in get_completed_matches():
        if m["stage"] in ("r32", "r16", "qf", "sf") and m["score_a"] != m["score_b"]:
            loser = m["team_a"] if m["score_a"] < m["score_b"] else m["team_b"]
            t = find_team(loser)
            out.add(t.name if t else loser)
    return out


def main() -> None:
    n_sims = int(os.environ.get("WC_SIMS", 10_000))
    print(f"Running pipeline for static snapshot ({n_sims:,} sims)...")
    pipeline.initialise(n_sims=n_sims)
    s = pipeline.get_state()

    teams = [
        {"code": t.code, "name": t.name, "flag": t.flag, "group": t.group,
         "elo": int(s.ratings.get(t.name, 0))}
        for t in WC2026_TEAMS
    ]

    eliminated = _eliminated()
    n = s.n_sims or 1
    odds = []
    for t in WC2026_TEAMS:
        if t.name in eliminated:
            probs = {k: 0.0 for k in STAGE_KEYS}
        else:
            probs = {
                k: round(s.results.get(stage, {}).get(t.name, 0) / n * 100, 1)
                for k, stage in STAGE_KEYS.items()
            }
        odds.append({"code": t.code, "name": t.name, "flag": t.flag, "group": t.group,
                     "elo": int(s.ratings.get(t.name, 0)), **probs})
    odds.sort(key=lambda r: r["p_title"], reverse=True)

    bracket = build_bracket(s.ratings, s.results, s.n_sims).model_dump()

    m = s.model
    meta = {
        "n_sims": s.n_sims,
        "generated_at": time.time(),
        "last_result_date": get_last_result_date(),
        # Coefficients for in-browser head-to-head (see frontend/src/api.js).
        "model": {
            "intercept": m.intercept,
            "elo_coef": m.elo_coef,
            "home_coef": m.home_coef,
            "elo_scale": float(ELO_DIFF_SCALE),
        },
        # Ratings by team name, so the browser can look up Elo for any matchup.
        "ratings": {t.name: s.ratings.get(t.name, 1000) for t in WC2026_TEAMS},
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    for name, data in (("teams", teams), ("odds", odds), ("bracket", bracket), ("meta", meta)):
        path = os.path.join(OUT_DIR, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        print(f"  wrote {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
