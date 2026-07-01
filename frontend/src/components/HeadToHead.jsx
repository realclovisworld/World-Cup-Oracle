// HeadToHead — team picker + matchup result card (IMPLEMENTATION.md §6.3 / DESIGN.md §5.3).
import { useState } from 'react'
import { fetchMatchup } from '../api'

function Metric({ label, value }) {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        borderRadius: 'var(--radius)',
        padding: 10,
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)' }}>{value}</div>
    </div>
  )
}

function ResultCard({ a, b, result }) {
  const winnerIsA = result.win_a >= result.win_b
  const winner = winnerIsA ? a : b

  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Win probability</div>
      <div
        role="meter"
        aria-valuenow={Math.round(result.win_a)}
        aria-valuemin={0}
        aria-valuemax={100}
        style={{ height: 8, borderRadius: 6, overflow: 'hidden', display: 'flex' }}
      >
        <div style={{ width: `${result.win_a}%`, background: '#378ADD' }} />
        <div style={{ width: `${result.draw}%`, background: 'var(--surface-0)' }} />
        <div style={{ width: `${result.win_b}%`, background: '#D85A30' }} />
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 12,
          color: 'var(--text-muted)',
          marginTop: 6,
        }}
      >
        <span>{a.flag} {a.name} {result.win_a}%</span>
        <span>{result.win_b}% {b.name} {b.flag}</span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 10,
          marginTop: 12,
        }}
      >
        <Metric label={`xG — ${a.name}`} value={result.xg_a} />
        <Metric label="Score" value={`${result.score_a} – ${result.score_b}`} />
        <Metric label={`xG — ${b.name}`} value={result.xg_b} />
      </div>

      <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>
        Draw: {result.draw}%
      </div>
      <div style={{ marginTop: 4, fontSize: 12 }}>
        <span style={{ color: 'var(--text-muted)' }}>Predicted winner: </span>
        <span style={{ color: 'var(--text-accent)', fontWeight: 500 }}>
          {winner.flag} {winner.name}
        </span>
      </div>
    </div>
  )
}

export default function HeadToHead({ teams }) {
  const [codeA, setCodeA] = useState(teams[0]?.code ?? '')
  const [codeB, setCodeB] = useState(teams[1]?.code ?? '')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const teamA = teams.find((t) => t.code === codeA)
  const teamB = teams.find((t) => t.code === codeB)
  const sameTeam = codeA === codeB

  const predict = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await fetchMatchup(codeA, codeB)
      setResult(r)
    } catch (e) {
      setError(e.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const selectStyle = { flex: 1 }

  return (
    <div className="card">
      <span style={{ fontSize: 14, fontWeight: 500 }}>Head to head</span>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
        <label htmlFor="team-a" style={{ position: 'absolute', left: -9999 }}>Team A</label>
        <select id="team-a" value={codeA} onChange={(e) => setCodeA(e.target.value)} style={selectStyle}>
          {teams.map((t) => (
            <option key={t.code} value={t.code}>{t.flag} {t.name}</option>
          ))}
        </select>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>vs</span>
        <label htmlFor="team-b" style={{ position: 'absolute', left: -9999 }}>Team B</label>
        <select id="team-b" value={codeB} onChange={(e) => setCodeB(e.target.value)} style={selectStyle}>
          {teams.map((t) => (
            <option key={t.code} value={t.code}>{t.flag} {t.name}</option>
          ))}
        </select>
        <button onClick={predict} disabled={sameTeam || loading}>
          {loading ? '⟳' : 'Predict ↗'}
        </button>
      </div>

      {error && (
        <div style={{ marginTop: 12, fontSize: 13, color: 'var(--text-danger)' }}>
          Prediction unavailable — check team names.
        </div>
      )}

      {result && teamA && teamB && !error && (
        <ResultCard a={teamA} b={teamB} result={result} />
      )}
    </div>
  )
}
