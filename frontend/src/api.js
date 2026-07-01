// Static data client. This build has no backend: the odds/bracket/teams are
// precomputed JSON (scripts/build_data.py), and head-to-head is computed in the
// browser from the Poisson model coefficients in meta.json.

const DATA = `${import.meta.env.BASE_URL}data`
const _cache = {}

async function loadJSON(name) {
  if (!_cache[name]) {
    const res = await fetch(`${DATA}/${name}.json`)
    if (!res.ok) throw new Error(`${name}.json → ${res.status}`)
    _cache[name] = await res.json()
  }
  return _cache[name]
}

export async function fetchStatus() {
  const m = await loadJSON('meta')
  return {
    ready: true,
    running: false,
    n_sims: m.n_sims,
    cached_at: m.generated_at,
    last_result_date: m.last_result_date,
  }
}

export async function fetchTeams() {
  return loadJSON('teams')
}

export async function fetchOdds() {
  return loadJSON('odds')
}

export async function fetchBracket() {
  return loadJSON('bracket')
}

// ── In-browser head-to-head (mirrors simulation.match_probabilities) ──────────

function poissonPmf(k, lam) {
  let p = Math.exp(-lam)
  for (let i = 1; i <= k; i++) p *= lam / i
  return p
}

function expectedGoals(eloA, eloB, model) {
  const d = (eloA - eloB) / model.elo_scale
  return [
    Math.exp(model.intercept + model.elo_coef * d),
    Math.exp(model.intercept + model.elo_coef * -d),
  ]
}

export async function fetchMatchup(teamA, teamB) {
  const meta = await loadJSON('meta')
  const teams = await loadJSON('teams')
  const byKey = (q) => teams.find((t) => t.code === q || t.name === q)
  const a = byKey(teamA)
  const b = byKey(teamB)
  if (!a || !b) throw new Error('team not found')

  const model = meta.model
  const eloA = meta.ratings[a.name] ?? a.elo
  const eloB = meta.ratings[b.name] ?? b.elo
  const [xgA, xgB] = expectedGoals(eloA, eloB, model)

  const MAX = 12
  const pa = Array.from({ length: MAX + 1 }, (_, i) => poissonPmf(i, xgA))
  const pb = Array.from({ length: MAX + 1 }, (_, i) => poissonPmf(i, xgB))

  let winA = 0, draw = 0, winB = 0
  const best = { a: { p: -1, s: [1, 1] }, draw: { p: -1, s: [1, 1] }, b: { p: -1, s: [1, 1] } }
  for (let i = 0; i <= MAX; i++) {
    for (let j = 0; j <= MAX; j++) {
      const p = pa[i] * pb[j]
      const bucket = i > j ? 'a' : i < j ? 'b' : 'draw'
      if (bucket === 'a') winA += p
      else if (bucket === 'b') winB += p
      else draw += p
      if (p > best[bucket].p) best[bucket] = { p, s: [i, j] }
    }
  }
  const tot = winA + draw + winB || 1
  winA /= tot; draw /= tot; winB /= tot

  const outcome = winA >= draw && winA >= winB ? 'a' : winB >= draw ? 'b' : 'draw'
  const [score_a, score_b] = best[outcome].s
  const r1 = (x) => Math.round(x * 10) / 10
  const r2 = (x) => Math.round(x * 100) / 100
  return {
    win_a: r1(winA * 100),
    draw: r1(draw * 100),
    win_b: r1(winB * 100),
    xg_a: r2(xgA),
    xg_b: r2(xgB),
    score_a,
    score_b,
  }
}

// No live re-run in a static build.
export async function triggerRerun() {
  return { message: 'Static snapshot — redeploy to refresh.' }
}
