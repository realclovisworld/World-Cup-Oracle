// All /api fetch calls in one place (IMPLEMENTATION.md §Phase 5).

const BASE = '/api'

export async function fetchStatus()  { return get('/status') }
export async function fetchTeams()   { return get('/teams') }
export async function fetchOdds()    { return get('/odds') }
export async function fetchBracket() { return get('/bracket') }

export async function fetchMatchup(teamA, teamB) {
  const res = await fetch(`${BASE}/matchup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ team_a: teamA, team_b: teamB }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function triggerRerun(nSims = 10_000) {
  const res = await fetch(`${BASE}/rerun?n_sims=${nSims}`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${path} → ${res.status}`)
  return res.json()
}
