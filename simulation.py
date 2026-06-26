"""Poisson match model + Monte Carlo tournament simulation.

Ported from the original TypeScript. Elo ratings drive an expected-goals (xG)
model; goals are drawn from a Poisson distribution; the full 48-team tournament
is simulated thousands of times to estimate each team's odds at every stage.
"""

import math
import random

from worldcup2026 import WC2026_TEAMS, GROUPS, WCTeam

NUM_SIMULATIONS = 10_000
BASE_XG = 1.25  # average goals per team per game
ELO_SCALE = 400  # Elo scale factor


# ---------- Math helpers ----------

def poisson_sample(lam: float) -> int:
    """Knuth's algorithm for sampling a Poisson-distributed integer."""
    if lam <= 0:
        return 0
    target = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= target:
            break
    return k - 1


def expected_goals(elo_a: float, elo_b: float) -> tuple[float, float]:
    """Convert an Elo gap into expected goals for each side."""
    diff = (elo_a - elo_b) / ELO_SCALE
    mult = 10 ** diff
    ratio = min(max(math.sqrt(mult), 0.33), 3)  # cap dominance
    total = BASE_XG * 2  # share ~2.5 goals between the two teams
    xg_a = (total * ratio) / (1 + ratio)
    xg_b = total - xg_a
    return xg_a, xg_b


def simulate_match(elo_a: float, elo_b: float) -> tuple[int, int]:
    xg_a, xg_b = expected_goals(elo_a, elo_b)
    return poisson_sample(xg_a), poisson_sample(xg_b)


def match_probabilities(elo_a: float, elo_b: float, trials: int = 50_000) -> dict:
    """Monte Carlo win/draw/loss probabilities + xG + most likely scoreline."""
    xg_a, xg_b = expected_goals(elo_a, elo_b)
    win_a = draw = win_b = 0
    score_freq: dict[str, int] = {}

    for _ in range(trials):
        ga = poisson_sample(xg_a)
        gb = poisson_sample(xg_b)
        key = f"{ga}-{gb}"
        score_freq[key] = score_freq.get(key, 0) + 1
        if ga > gb:
            win_a += 1
        elif ga < gb:
            win_b += 1
        else:
            draw += 1

    most_likely = max(score_freq.items(), key=lambda kv: kv[1])[0] if score_freq else "1-1"

    return {
        "p_win_a": win_a / trials,
        "p_draw": draw / trials,
        "p_win_b": win_b / trials,
        "xg_a": round(xg_a, 2),
        "xg_b": round(xg_b, 2),
        "most_likely_score": most_likely,
    }


# ---------- Tournament ----------

class _Standing:
    __slots__ = ("team", "elo", "points", "gf", "ga")

    def __init__(self, team: WCTeam, elo: float):
        self.team = team
        self.elo = elo
        self.points = 0
        self.gf = 0
        self.ga = 0

    @property
    def gd(self) -> int:
        return self.gf - self.ga


def _simulate_group(group_teams: list[WCTeam], ratings: dict[str, float]) -> list[_Standing]:
    standings = [_Standing(t, ratings.get(t.name, 1000)) for t in group_teams]
    n = len(standings)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = standings[i], standings[j]
            ga, gb = simulate_match(a.elo, b.elo)
            a.gf += ga
            a.ga += gb
            b.gf += gb
            b.ga += ga
            if ga > gb:
                a.points += 3
            elif gb > ga:
                b.points += 3
            else:
                a.points += 1
                b.points += 1
    standings.sort(key=lambda s: (s.points, s.gd, s.gf), reverse=True)
    return standings


def _simulate_knockout(elo_a: float, elo_b: float) -> bool:
    """Return True if A advances. Ties go to a slightly-weighted penalty shootout."""
    ga, gb = simulate_match(elo_a, elo_b)
    if ga > gb:
        return True
    if gb > ga:
        return False
    pen_edge = min(0.6, 0.5 + (elo_a - elo_b) / 2000)
    return random.random() < pen_edge


def run_simulations(ratings: dict[str, float], num_simulations: int = NUM_SIMULATIONS) -> dict:
    names = [t.name for t in WC2026_TEAMS]
    result = {
        stage: {n: 0 for n in names}
        for stage in (
            "titles",
            "finals",
            "semi_finals",
            "quarter_finals",
            "round_of_16",
            "group_wins",
            "group_advances",
        )
    }

    groups_index = {g: [t for t in WC2026_TEAMS if t.group == g] for g in GROUPS}

    for _ in range(num_simulations):
        group_results = [_simulate_group(groups_index[g], ratings) for g in GROUPS]

        third_placers: list[_Standing] = []
        advancers: list[WCTeam] = []

        for standings in group_results:
            winner, second, third = standings[0], standings[1], standings[2]
            result["group_wins"][winner.team.name] += 1
            result["group_advances"][winner.team.name] += 1
            result["group_advances"][second.team.name] += 1
            advancers.append(winner.team)
            advancers.append(second.team)
            third_placers.append(third)

        # Best 8 third-place teams complete the 32-team knockout bracket.
        third_placers.sort(key=lambda s: (s.points, s.gd, s.gf), reverse=True)
        for s in third_placers[:8]:
            result["group_advances"][s.team.name] += 1
            advancers.append(s.team)

        pool = advancers[:]
        random.shuffle(pool)

        def knockout_round(teams: list[WCTeam]) -> list[WCTeam]:
            winners: list[WCTeam] = []
            for i in range(0, len(teams), 2):
                a, b = teams[i], teams[i + 1]
                a_wins = _simulate_knockout(ratings.get(a.name, 1000), ratings.get(b.name, 1000))
                winners.append(a if a_wins else b)
            return winners

        r16 = knockout_round(pool)
        for t in r16:
            result["round_of_16"][t.name] += 1

        qf = knockout_round(r16)
        for t in qf:
            result["quarter_finals"][t.name] += 1

        sf = knockout_round(qf)
        for t in sf:
            result["semi_finals"][t.name] += 1

        finalists = knockout_round(sf)
        for t in finalists:
            result["finals"][t.name] += 1

        champion = knockout_round(finalists)[0]
        result["titles"][champion.name] += 1

    return result
