"""Modal predicted knockout bracket (IMPLEMENTATION.md §1.5).

The bracket *structure* is fixed (simulation.R32_BRACKET), but its slots
(("W", group), ("R", group), ("T", i)) only resolve to concrete teams once the
group stage is played. Rather than a random draw, this builds a deterministic
"chalk" bracket: each group is ranked by Elo to fill winner / runner-up / third
slots, the eight best third-placers complete the 32-team field via the same
seeding-protection logic the simulation uses (simulation._assign_thirds), and
each knockout tie is decided by the modal outcome of match_probabilities — the
same engine oracle.py and /api/matchup use, so it agrees with them.

Note: ``results`` and ``n_sims`` are accepted for interface symmetry but the
chalk path is derived from Elo + the fixed template, not the per-stage tallies.
"""

from api.live_results import get_knockout_fixtures, get_result_for
from api.models import BracketData, BracketMatch, BracketRound
from simulation import R32_BRACKET, _assign_thirds, match_probabilities
from worldcup2026 import GROUPS, WC2026_TEAMS, WCTeam, find_team

ROUND_NAMES = ["R32", "R16", "QF", "SF", "Final"]
_STAGE_ORDER = ["r32", "r16", "qf", "sf", "final"]
_STAGE_LABEL = {"r32": "R32", "r16": "R16", "qf": "QF", "sf": "SF", "final": "Final"}
# Official FIFA match numbering (IMPLEMENTATION_FIFA §4): first match of each round.
_ROUND_START = {"R32": 73, "R16": 89, "QF": 97, "SF": 101, "Final": 104}
_TRIALS = 10_000


def _match_no(round_name: str, i: int) -> str | None:
    start = _ROUND_START.get(round_name)
    return f"M{start + i}" if start is not None else None


def _parse_score(score: str) -> tuple[int, int]:
    try:
        a, b = score.split("-", 1)
        return int(a), int(b)
    except (ValueError, AttributeError):
        return 0, 0


def _seed_pool(ratings: dict) -> list[WCTeam]:
    """Resolve the fixed R32 template into 32 concrete teams, Elo-seeded.

    Returns the teams in bracket order (pool[2i], pool[2i+1] are one R32 tie).
    """
    def elo(t: WCTeam) -> float:
        return ratings.get(t.name, 1000)

    winners_by_group: dict[str, WCTeam] = {}
    runners_by_group: dict[str, WCTeam] = {}
    thirds_with_elo: list[tuple[WCTeam, float]] = []

    for g in GROUPS:
        ranked = sorted(
            (t for t in WC2026_TEAMS if t.group == g), key=elo, reverse=True
        )
        winners_by_group[g] = ranked[0]
        runners_by_group[g] = ranked[1]
        thirds_with_elo.append((ranked[2], elo(ranked[2])))

    # Eight best third-placers, ranked, then placed into the eight ("T", i)
    # slots with the same own-group-avoidance rule the simulation uses.
    best_thirds = [t for t, _ in sorted(thirds_with_elo, key=lambda x: x[1], reverse=True)[:8]]
    thirds = _assign_thirds(best_thirds)

    def resolve(slot: tuple) -> WCTeam:
        kind, key = slot
        if kind == "W":
            return winners_by_group[key]
        if kind == "R":
            return runners_by_group[key]
        return thirds[key]  # ("T", i)

    pool: list[WCTeam] = []
    for slot_a, slot_b in R32_BRACKET:
        pool.append(resolve(slot_a))
        pool.append(resolve(slot_b))
    return pool


def _play_round(teams: list[WCTeam], ratings: dict, round_name: str) -> tuple[list[BracketMatch], list[WCTeam]]:
    """Play one knockout round. Returns (match cards, advancing teams)."""
    matches: list[BracketMatch] = []
    winners: list[WCTeam] = []

    for idx, i in enumerate(range(0, len(teams), 2)):
        a, b = teams[i], teams[i + 1]
        fixture = get_result_for(a.name, b.name) or {"score_a": None, "score_b": None}
        m, w = _fixture_match(a, b, fixture, ratings, round_name, idx)
        matches.append(m)
        winners.append(w)
    return matches, winners


def _team_obj(name: str) -> WCTeam:
    """Resolve a fixture team name to a WCTeam (placeholder if unknown)."""
    t = find_team(name)
    if t:
        return t
    return WCTeam(csv_name=name, name=name, code=name[:3].upper(), group="", flag="")


def _played_winner(fixture: dict, a: WCTeam, b: WCTeam, ratings: dict) -> bool:
    """True if side A advances from a played tie. Level ties use the CSV
    ``winner`` column ('a'/'b'/team name); absent that, the higher Elo."""
    sa, sb = fixture["score_a"], fixture["score_b"]
    if sa != sb:
        return sa > sb
    pa, pb = fixture.get("pens_a"), fixture.get("pens_b")
    if pa is not None and pb is not None and pa != pb:
        return pa > pb
    w = fixture.get("winner", "").strip().lower()
    if w in ("a", a.name.lower(), a.code.lower()):
        return True
    if w in ("b", b.name.lower(), b.code.lower()):
        return False
    return ratings.get(a.name, 1000) >= ratings.get(b.name, 1000)


def _fixture_match(
    a: WCTeam, b: WCTeam, fixture: dict, ratings: dict, round_name: str, index: int
) -> tuple[BracketMatch, WCTeam]:
    """Build one BracketMatch (real result or prediction) and its winner."""
    common = dict(
        team_a=a.name, team_b=b.name, flag_a=a.flag, flag_b=b.flag,
        code_a=a.code, code_b=b.code, date=fixture.get("date"),
        venue=fixture.get("venue"), match_no=_match_no(round_name, index),
    )
    if fixture["score_a"] is not None:  # played
        a_wins = _played_winner(fixture, a, b, ratings)
        return (
            BracketMatch(
                **common,
                score_a=fixture["score_a"], score_b=fixture["score_b"],
                pens_a=fixture.get("pens_a"), pens_b=fixture.get("pens_b"),
                winner="a" if a_wins else "b",
                win_prob=100.0, xg_a=None, xg_b=None, is_actual=True,
            ),
            a if a_wins else b,
        )
    # upcoming — predict with current Elo
    r = match_probabilities(ratings.get(a.name, 1000), ratings.get(b.name, 1000), trials=_TRIALS)
    a_wins = r["p_win_a"] >= r["p_win_b"]
    score_a, score_b = _parse_score(r["most_likely_score"])
    return (
        BracketMatch(
            **common,
            score_a=score_a, score_b=score_b,
            winner="a" if a_wins else "b",
            win_prob=round((r["p_win_a"] if a_wins else r["p_win_b"]) * 100, 1),
            xg_a=round(r["xg_a"], 1), xg_b=round(r["xg_b"], 1), is_actual=False,
        ),
        a if a_wins else b,
    )


def _build_from_fixtures(ko: list[dict], ratings: dict) -> BracketData:
    """Bracket seeded from real knockout fixtures. Listed ties (played or
    upcoming) are used verbatim; once a round runs out of listed ties, the
    actual winners are auto-paired into the next round and predicted."""
    rounds_out: list[BracketRound] = []
    prev_winners: list[WCTeam] | None = None
    started = False

    for stage in _STAGE_ORDER:
        listed = [f for f in ko if f["stage"] == stage]
        if listed:
            pairs = [(_team_obj(f["team_a"]), _team_obj(f["team_b"]), f) for f in listed]
        elif started and prev_winners and len(prev_winners) >= 2 and len(prev_winners) % 2 == 0:
            blank = {"score_a": None, "score_b": None, "winner": ""}
            pairs = [
                (prev_winners[i], prev_winners[i + 1], blank)
                for i in range(0, len(prev_winners), 2)
            ]
        elif not started:
            continue  # skip empty early rounds until the first listed stage
        else:
            break

        round_name = _STAGE_LABEL[stage]
        matches, winners = [], []
        for idx, (a, b, f) in enumerate(pairs):
            m, w = _fixture_match(a, b, f, ratings, round_name, idx)
            matches.append(m)
            winners.append(w)
        rounds_out.append(BracketRound(name=round_name, matches=matches))
        prev_winners = winners
        started = True
        if stage == "final":
            break

    return BracketData(rounds=rounds_out)


def build_bracket(ratings: dict, results: dict, n_sims: int) -> BracketData:
    """Real-results bracket when knockout fixtures exist; otherwise the
    full Elo-seeded predicted (chalk) bracket, R32 -> Final."""
    ko = get_knockout_fixtures()
    if ko:
        bd = _build_from_fixtures(ko, ratings)
        if bd.rounds:
            return bd

    teams = _seed_pool(ratings)
    rounds_out: list[BracketRound] = []
    for name in ROUND_NAMES:
        matches, winners = _play_round(teams, ratings, name)
        rounds_out.append(BracketRound(name=name, matches=matches))
        teams = winners
    return BracketData(rounds=rounds_out)
