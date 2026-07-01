"""Elo ratings — the team "strength index".

Downloads ~49k historical international match results and replays them
chronologically, updating each team's Elo rating after every match. This is a
direct port of the original TypeScript implementation.
"""

import csv
import io
import os
import ssl
import time
import urllib.error
import urllib.request

from worldcup2026 import WC2026_TEAMS

# martj42/international_results is community-maintained and updated continuously
# (new matches, including live 2026 results, land via pull requests). We cache it
# locally but re-check upstream once the cache goes stale so those updates flow in.
CSV_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
CACHE_PATH = os.path.join(os.path.dirname(__file__), ".cache_results.csv")
ETAG_PATH = CACHE_PATH + ".etag"

# How long a cached copy is trusted before we re-check upstream. Override with
# the WC_RESULTS_TTL env var (seconds); set WC_RESULTS_REFRESH=1 to force a check.
CACHE_TTL_SECONDS = int(os.environ.get("WC_RESULTS_TTL", 12 * 3600))


def k_factor(tournament: str) -> float:
    """Match importance multiplier — bigger competitions move ratings more."""
    t = tournament.lower()
    if "fifa world cup" in t and "qualif" not in t:
        return 60
    if any(
        c in t
        for c in (
            "copa america",
            "uefa euro",
            "africa cup",
            "afc asian cup",
            "gold cup",
            "concacaf nations",
        )
    ):
        return 50
    if "qualif" in t or "qualification" in t:
        return 40
    if "nations league" in t or "confederation" in t:
        return 35
    return 20  # Friendly


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def _ssl_context() -> ssl.SSLContext:
    """Verified TLS where possible; fall back to unverified on misconfigured
    macOS Python builds that ship without root certificates."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        ctx = ssl.create_default_context()
        # Probe whether the default trust store actually works.
        return ctx
    except Exception:
        return ssl._create_unverified_context()


def _read_cache() -> str:
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _write_cache(raw: str, etag: str | None) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        f.write(raw)
    if etag:
        with open(ETAG_PATH, "w", encoding="utf-8") as f:
            f.write(etag)


def _cache_fresh() -> bool:
    if not os.path.exists(CACHE_PATH):
        return False
    return (time.time() - os.path.getmtime(CACHE_PATH)) < CACHE_TTL_SECONDS


def _http_get(headers: dict):
    """GET CSV_URL, retrying without TLS verification only if the host's Python
    has no usable CA bundle (some macOS builds)."""
    req = urllib.request.Request(CSV_URL, headers=headers)
    try:
        return urllib.request.urlopen(req, timeout=60, context=_ssl_context())
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            return urllib.request.urlopen(req, timeout=60, context=ssl._create_unverified_context())
        raise


def _download_csv(force: bool = False) -> str:
    """Return the results CSV, refreshing the cache when it has gone stale.

    - No cache -> download in full.
    - Fresh cache (within CACHE_TTL_SECONDS) -> use it, no network.
    - Stale cache -> conditional GET (If-None-Match). A 304 keeps the cache and
      resets its clock; a 200 replaces it. Any network error falls back to the
      cached copy so the app still runs offline.
    """
    force = force or os.environ.get("WC_RESULTS_REFRESH", "").strip() not in ("", "0")
    have_cache = os.path.exists(CACHE_PATH)
    if have_cache and _cache_fresh() and not force:
        return _read_cache()

    headers = {"User-Agent": "world-cup-oracle"}
    if have_cache and os.path.exists(ETAG_PATH):
        etag = _read_etag()
        if etag:
            headers["If-None-Match"] = etag

    print(
        "Checking martj42/international_results for updates..."
        if have_cache
        else "Downloading international results CSV (~49k matches)..."
    )
    try:
        with _http_get(headers) as resp:
            raw = resp.read().decode("utf-8")
            _write_cache(raw, resp.headers.get("ETag"))
            return raw
    except urllib.error.HTTPError as e:
        if e.code == 304 and have_cache:
            os.utime(CACHE_PATH, None)  # unchanged upstream — reset freshness clock
            return _read_cache()
        if have_cache:
            return _read_cache()
        raise
    except urllib.error.URLError:
        if have_cache:
            return _read_cache()  # offline — use whatever we have
        raise


def _read_etag() -> str:
    try:
        with open(ETAG_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _parse_csv(raw: str) -> list[dict]:
    rows: list[dict] = []
    reader = csv.reader(io.StringIO(raw))
    header = next(reader, None)  # skip header
    for parts in reader:
        if len(parts) < 9:
            continue
        try:
            home_score = int(parts[3])
            away_score = int(parts[4])
        except ValueError:
            continue
        rows.append(
            {
                "date": parts[0],
                "home_team": parts[1],
                "away_team": parts[2],
                "home_score": home_score,
                "away_score": away_score,
                "tournament": parts[5],
                "neutral": parts[8].strip().upper() == "TRUE",
            }
        )
    return rows


def compute_elo_ratings(record_history: bool = False, force_refresh: bool = False):
    """Replay all matches in date order and return {team: rating}, match_count.

    ``force_refresh`` re-checks the upstream dataset regardless of cache age.

    If ``record_history`` is True, also return a third value: a list of
    pre-match snapshots (each team's Elo *as it stood on match day*, before the
    result was applied) alongside the final score. That snapshot is exactly the
    training data the Poisson regression learns from — using the rating at the
    time of the match avoids leaking future information into the features.
    """
    raw = _download_csv(force=force_refresh)
    rows = _parse_csv(raw)
    rows.sort(key=lambda r: r["date"])

    ratings: dict[str, float] = {}
    history: list[dict] | None = [] if record_history else None

    def get_rating(team: str) -> float:
        return ratings.setdefault(team, 1000.0)

    for r in rows:
        home_elo = get_rating(r["home_team"])
        away_elo = get_rating(r["away_team"])
        if history is not None:
            history.append(
                {
                    "home_elo": home_elo,
                    "away_elo": away_elo,
                    "neutral": r["neutral"],
                    "home_score": r["home_score"],
                    "away_score": r["away_score"],
                }
            )

        home_adv = 0 if r["neutral"] else 75
        r_a = home_elo + home_adv
        r_b = away_elo

        expected_a = expected_score(r_a, r_b)
        expected_b = 1 - expected_a

        if r["home_score"] > r["away_score"]:
            actual_a, actual_b = 1.0, 0.0
        elif r["home_score"] < r["away_score"]:
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a, actual_b = 0.5, 0.5

        k = k_factor(r["tournament"])
        goal_diff = abs(r["home_score"] - r["away_score"])
        # Goal-difference multiplier (FIFA-style), capped at 1.75x.
        gd_mult = 1.0 if goal_diff <= 1 else 1.5 if goal_diff == 2 else 1.75

        ratings[r["home_team"]] = home_elo + k * gd_mult * (actual_a - expected_a)
        ratings[r["away_team"]] = away_elo + k * gd_mult * (actual_b - expected_b)

    if history is not None:
        return ratings, len(rows), history
    return ratings, len(rows)


def get_wc_team_ratings(all_ratings: dict[str, float]) -> dict[str, float]:
    """Map the full rating table down to the 48 qualified teams, by display name."""
    return {t.name: round(all_ratings.get(t.csv_name, 1000.0)) for t in WC2026_TEAMS}
