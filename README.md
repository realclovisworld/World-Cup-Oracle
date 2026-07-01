# World Cup Oracle

Predicts the 2026 FIFA World Cup. It computes **Elo ratings** from ~49,000
historical international matches, trains a **Poisson-regression** goal model on
those matches, and runs a **Monte Carlo** simulation of the full 48-team
tournament (10,000 runs by default) to estimate every team's odds of winning the
title, reaching the final, and reaching the semis.

It ships in two editions:

- **Terminal** (`oracle.py`) — prints the title-odds table, then an interactive
  head-to-head predictor.
- **Web** (`api/` + `frontend/`) — a FastAPI + React app with a sortable odds
  table, a head-to-head panel, and a responsive FIFA-style knockout bracket.
  It folds in **live tournament results**: played matches show the real score
  and advance the real winner, while upcoming ties are predicted (see
  [Live tournament results](#live-tournament-results)).

Docs: system design in [`ARCHITECTURE.md`](ARCHITECTURE.md); the web build plan
in [`DESIGN.md`](DESIGN.md) and [`IMPLEMENTATION.md`](IMPLEMENTATION.md); the
live-results and FIFA-bracket phases in [`IMPLEMENTATION_LIVE.md`](IMPLEMENTATION_LIVE.md)
and [`IMPLEMENTATION_FIFA.md`](IMPLEMENTATION_FIFA.md).

## Requirements

Python 3.10+. Install dependencies into a virtualenv:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

This pulls in **scikit-learn** + **numpy** (the ML goal model), **fastapi** +
**uvicorn** (the web API), and **requests**/**certifi** (data download). The web
edition also needs **Node 18+** for the frontend build.

## Terminal edition

```bash
python oracle.py
```

Options:

```bash
python oracle.py --sims 2000     # fewer simulations = faster, a bit noisier
```

### Historical dataset

Elo is computed from [`martj42/international_results`](https://github.com/martj42/international_results)
(~49k matches, `date,home_team,away_team,home_score,away_score,tournament,city,country,neutral`).
It's community-maintained and updated continuously — including live 2026 World
Cup results — so the app keeps it current automatically:

- First run downloads and caches it (`.cache_results.csv`, ~3.7 MB).
- After the cache is **12 hours old** it re-checks upstream with a conditional
  request (ETag); if nothing changed GitHub returns `304 Not Modified` and the
  cached copy is kept, so the check is cheap.
- If you're offline, the cached copy is used regardless.

Tune it with env vars: `WC_RESULTS_TTL=<seconds>` changes the 12-hour window,
and `WC_RESULTS_REFRESH=1` forces an upstream check on the next run. Deleting
`.cache_results.csv` still forces a full re-download. Fixtures not yet played
carry no score and are ignored.

### Using the prompt

```
> Brazil vs France      # head-to-head match prediction
> titles                # reprint the full title-odds table
> teams                 # list all 48 qualified teams + groups
> quit
```

Team names are matched loosely — `Brazil`, `BRA`, or `bra` all work.

## Web edition

Build the frontend, then serve everything from FastAPI:

```bash
cd frontend && npm install && npm run build && cd ..
uvicorn api.main:app --port 8000
```

Open <http://localhost:8000>. The first request triggers a one-time cold start
(Elo replay + model fit + simulation), which the loading screen waits out.

For development with hot-reloading frontend + live backend:

```bash
# Terminal 1
uvicorn api.main:app --reload --port 8000
# Terminal 2
cd frontend && npm run dev      # proxies /api/* to :8000
```

### API endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/api/status` | pipeline readiness, sim count, cache time |
| GET | `/api/teams` | the 48 teams with Elo |
| GET | `/api/odds` | per-team stage probabilities (sorted by title odds) |
| POST | `/api/matchup` | head-to-head prediction for two teams |
| GET | `/api/bracket` | the knockout bracket — real results where played, predictions elsewhere |
| POST | `/api/rerun` | re-run the Monte Carlo simulation in the background |
| POST | `/api/refresh-results` | reload `live_results.csv` + re-check the historical dataset, re-apply Elo, refit + re-simulate |

Interactive docs are auto-generated at <http://localhost:8000/docs>.

## Deploy

This is a **stateful server**, not a set of serverless functions: it runs the
Elo → Poisson → Monte Carlo pipeline once on boot and keeps the result warm in
memory. Deploy it on a host that runs a long-lived process — **Render, Railway,
or Fly.io** — not on serverless platforms (Vercel/Lambda), where the cold-start
pipeline exceeds time/memory limits and in-memory state doesn't persist.

A `Dockerfile` builds the frontend and serves everything from one container:

- **Render** — push to GitHub, then *New → Blueprint* pointed at this repo
  (`render.yaml` is included). Health check: `/api/status`.
- **Railway** — *New Project → Deploy from repo*; it auto-detects the `Dockerfile`.
- **Fly.io** — `fly launch --no-deploy` once, then `fly deploy` (`fly.toml` included).

The pipeline warms up in the background, so the container is reachable
immediately; `/api/status` reports `ready:false` until it finishes. Useful env
vars: `WC_SIMS` (simulations per tournament; lower it on small instances),
`WC_RESULTS_TTL` (dataset re-check window, seconds), `WC_CACHE_DIR` (writable
cache dir — the image sets it to `/tmp`).

### Static snapshot (Vercel / any static host)

The live backend can't run on serverless (Vercel/Lambda). For those, build a
**static snapshot**: precompute the data, and the frontend reads it directly
with head-to-head computed in the browser — no functions, no cold start.

```bash
python scripts/build_data.py     # -> frontend/public/data/*.json
```

Commit the generated JSON. `vercel.json` + `.vercelignore` are set up so Vercel
builds only the frontend (the Python code is excluded, so no serverless
functions are created). Deploy: push, then import the repo on Vercel — it reads
`vercel.json` and outputs `frontend/dist`. The trade-off is that it's a snapshot
(no live *Re-run* / *Refresh*); re-run `build_data.py` and redeploy to update it.

## Live tournament results

`live_results.csv` holds played and upcoming 2026 matches. Completed matches
feed straight into the Elo ratings and the Poisson training data; in the
bracket, played ties show the real score and advance the real winner, while
unplayed ties (and the rounds beyond them) are predicted with the updated Elo.

Columns: `date,team_a,team_b,score_a,score_b,stage,winner,pens_a,pens_b`

- `stage` is `group` or a knockout round (`r32`, `r16`, `qf`, `sf`, `final`).
- Leave `score_a`/`score_b` blank for a fixture that hasn't been played yet.
- For a level knockout tie, put the shootout scores in `pens_a`/`pens_b`
  (or the advancing side in `winner`); group results only need the scores.
- Team names must match the display names in the [Teams & groups](#teams--groups)
  table (e.g. `USA`, `Bosnia & Herz.`, `Czech Republic`).

After editing the file, apply it without restarting:

```bash
curl -X POST http://localhost:8000/api/refresh-results
```

This also force-checks the upstream historical dataset (a cheap conditional
request), so one call refreshes both data sources.

With no knockout rows present, the bracket falls back to a fully Elo-seeded
prediction.

## Teams & groups

The 48 teams and their groups follow the **official FIFA final draw** held on
5 December 2025 in Washington, D.C.

| | | | |
|---|---|---|---|
| **A** Mexico · South Africa · South Korea · Czech Republic | **B** Canada · Bosnia & Herz. · Qatar · Switzerland | **C** Brazil · Morocco · Haiti · Scotland | **D** USA · Paraguay · Australia · Turkey |
| **E** Germany · Curaçao · Ivory Coast · Ecuador | **F** Netherlands · Japan · Sweden · Tunisia | **G** Belgium · Egypt · Iran · New Zealand | **H** Spain · Cape Verde · Saudi Arabia · Uruguay |
| **I** France · Senegal · Iraq · Norway | **J** Argentina · Algeria · Austria · Jordan | **K** Portugal · DR Congo · Uzbekistan · Colombia | **L** England · Croatia · Ghana · Panama |

## How it works

| File | Responsibility |
|------|----------------|
| `elo.py` | Downloads results, replays them chronologically, computes Elo strength ratings (and pre-match snapshots for training). |
| `poisson_model.py` | Trains a Poisson regression mapping Elo gap + home field to expected goals. |
| `simulation.py` | Poisson expected-goals model + Monte Carlo group stage and knockout bracket. |
| `worldcup2026.py` | The 48 qualified teams, group assignments, and dataset name mapping. |
| `oracle.py` | The terminal CLI — wires it together and renders the tables / prompt. |
| `api/` | FastAPI app: model pipeline, live-results feed, and bracket builder as JSON endpoints. |
| `frontend/` | React + Vite single-page app served by FastAPI (responsive FIFA-style bracket). |
| `live_results.csv` | Played + upcoming 2026 matches (see [Live tournament results](#live-tournament-results)). |

### The model in brief

- **Elo:** every historical match nudges each team's rating toward its result,
  weighted by match importance (World Cup > continental > qualifier > friendly),
  goal margin, and home advantage. Teams start at 1000.
- **Expected goals:** a Poisson regression learned from ~49k matches maps the Elo
  gap (and home field) to each side's expected goals. A hand-coded fallback
  formula is used if the model isn't installed.
- **Match outcome:** each side's goals are drawn from a Poisson distribution.
- **Tournament:** 12 groups of 4 play round-robin; the top two of each group
  plus the eight best third-place teams advance to a 32-team knockout bracket.
  The bracket uses a **fixed template** that follows the real format — group
  winners are protected from each other in the Round of 32, and a group's winner
  and runner-up sit in opposite halves so they can only meet again in the final
  — rather than a random draw, so finishing position actually shapes a team's
  path. (FIFA's exact third-place lookup table is approximated.) Knockout ties
  are decided by a lightly Elo-weighted penalty shootout. Repeat 10,000 times
  and count how often each team reaches each stage.
- **Live results:** any completed 2026 match in `live_results.csv` is replayed
  through the same Elo update, shifting ratings toward real tournament form. The
  web bracket then shows real scores for played ties and predicts the rest.

> Predictions are a probabilistic model for entertainment, not betting advice.
