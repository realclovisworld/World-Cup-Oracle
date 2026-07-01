"""Live 2026 World Cup results feed (Implementation_live.md §1–2).

Data source: **Option C** — a manually-maintained CSV (`live_results.csv`).
Honest stopgap with a clear upgrade path: swap only this module's body for a
sports-data API (Option A) and nothing else changes, because every other module
consumes results through this interface.

Exposes:
    get_completed_matches() -> list[dict]
        Each: { date, team_a, team_b, score_a, score_b, stage }. Only matches
        with both scores present (i.e. actually played).
    get_result_for(team_a, team_b) -> dict | None
        The completed result for a fixture, checking both orderings; None if not
        yet played.
    get_last_result_date() -> str | None
        Max date across completed matches (data-freshness display).
    clear_cache()
        Drop the cached CSV read so a refresh picks up edits without a restart.

Do NOT scrape fifa.com — its standings page is JS-rendered and returns no match
data to a plain fetch.
"""

import csv
import os
from functools import lru_cache

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "live_results.csv")


@lru_cache(maxsize=1)
def _load_raw() -> list[dict]:
    rows: list[dict] = []
    if not os.path.exists(CSV_PATH):
        return rows
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def clear_cache() -> None:
    _load_raw.cache_clear()


def _played(row: dict) -> bool:
    return row.get("score_a", "").strip() != "" and row.get("score_b", "").strip() != ""


def _opt_int(row: dict, key: str) -> int | None:
    v = (row.get(key, "") or "").strip()
    return int(v) if v != "" else None


def get_completed_matches() -> list[dict]:
    out: list[dict] = []
    for row in _load_raw():
        if not _played(row):
            continue
        out.append(
            {
                "date": row["date"],
                "team_a": row["team_a"],
                "team_b": row["team_b"],
                "score_a": int(row["score_a"]),
                "score_b": int(row["score_b"]),
                "pens_a": _opt_int(row, "pens_a"),
                "pens_b": _opt_int(row, "pens_b"),
                "stage": row.get("stage", ""),
                "venue": (row.get("venue", "") or "").strip() or None,
            }
        )
    return out


def get_result_for(team_a: str, team_b: str) -> dict | None:
    for m in get_completed_matches():
        if {m["team_a"], m["team_b"]} == {team_a, team_b}:
            if m["team_a"] == team_a:
                return m
            # Normalise orientation to the requested (team_a, team_b) order.
            return {
                **m,
                "team_a": team_a,
                "team_b": team_b,
                "score_a": m["score_b"],
                "score_b": m["score_a"],
                "pens_a": m["pens_b"],
                "pens_b": m["pens_a"],
            }
    return None


def get_last_result_date() -> str | None:
    dates = [m["date"] for m in get_completed_matches()]
    return max(dates) if dates else None


_KO_STAGES = ("r32", "r16", "qf", "sf", "final")


def get_knockout_fixtures() -> list[dict]:
    """Knockout ties in CSV order, played and upcoming alike.

    Each: { stage, team_a, team_b, score_a|None, score_b|None, winner }.
    score_* is None when the tie hasn't been played yet. ``winner`` is an
    optional CSV column ('a'/'b' or a team name) used only to break a level
    real score (a shootout) — blank otherwise.
    """
    out: list[dict] = []
    for row in _load_raw():
        stage = row.get("stage", "").strip().lower()
        if stage not in _KO_STAGES:
            continue
        played = _played(row)
        out.append(
            {
                "stage": stage,
                "team_a": row["team_a"],
                "team_b": row["team_b"],
                "score_a": int(row["score_a"]) if played else None,
                "score_b": int(row["score_b"]) if played else None,
                "pens_a": _opt_int(row, "pens_a"),
                "pens_b": _opt_int(row, "pens_b"),
                "winner": (row.get("winner", "") or "").strip(),
                "date": (row.get("date", "") or "").strip() or None,
                "venue": (row.get("venue", "") or "").strip() or None,
            }
        )
    return out
