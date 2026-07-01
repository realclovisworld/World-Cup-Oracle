// MatchDetail — expanded view of a clicked bracket match (IMPLEMENTATION.md §6.5 / DESIGN.md §5.4).

const ROUND_FULL = {
  R32: 'Round of 32',
  R16: 'Round of 16',
  QF: 'Quarter-final',
  SF: 'Semi-final',
  Final: 'Final',
}
const ROUND_ORDER = ['R32', 'R16', 'QF', 'SF', 'Final']

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

export default function MatchDetail({ selection }) {
  if (!selection) return null

  const { round, match } = selection
  const roundName = ROUND_ORDER[round] ?? ''
  const winnerLabel =
    match.winner === 'a'
      ? `${match.flag_a} ${match.team_a}`
      : `${match.flag_b} ${match.team_b}`

  // Played match: show the real final score, not a prediction.
  if (match.is_actual) {
    return (
      <div className="card">
        <div
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12 }}
        >
          <span style={{ fontSize: 14, fontWeight: 500 }}>
            {match.flag_a} {match.team_a} vs {match.flag_b} {match.team_b}
            <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 8 }}>
              {ROUND_FULL[roundName] ?? roundName}
            </span>
          </span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Full time</span>
        </div>
        <div
          style={{ textAlign: 'center', background: 'var(--surface-1)', borderRadius: 'var(--radius)', padding: 14 }}
        >
          <div style={{ fontSize: 28, fontWeight: 500 }}>
            {match.score_a} – {match.score_b}
          </div>
        </div>
        <div style={{ marginTop: 10, fontSize: 12 }}>
          <span style={{ color: 'var(--text-muted)' }}>Winner: </span>
          <span style={{ color: 'var(--text-accent)', fontWeight: 500 }}>{winnerLabel}</span>
        </div>
      </div>
    )
  }

  const aWins = match.winner === 'a'
  const winA = aWins ? match.win_prob : 100 - match.win_prob
  const winB = 100 - winA
  const winner = aWins ? { flag: match.flag_a, name: match.team_a } : { flag: match.flag_b, name: match.team_b }

  return (
    <div className="card">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 12,
        }}
      >
        <span style={{ fontSize: 14, fontWeight: 500 }}>
          {match.flag_a} {match.team_a} vs {match.flag_b} {match.team_b}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {ROUND_FULL[roundName] ?? roundName} · 10k sim
        </span>
      </div>

      <div
        role="meter"
        aria-valuenow={Math.round(winA)}
        aria-valuemin={0}
        aria-valuemax={100}
        style={{ height: 8, borderRadius: 6, overflow: 'hidden', display: 'flex' }}
      >
        <div style={{ width: `${winA}%`, background: '#378ADD' }} />
        <div style={{ width: `${winB}%`, background: '#D85A30' }} />
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
        <span>{match.flag_a} {match.team_a} {winA.toFixed(1)}%</span>
        <span>{winB.toFixed(1)}% {match.team_b} {match.flag_b}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginTop: 12 }}>
        <Metric label={`xG — ${match.team_a}`} value={match.xg_a} />
        <Metric label="likely score" value={`${match.score_a} – ${match.score_b}`} />
        <Metric label={`xG — ${match.team_b}`} value={match.xg_b} />
      </div>

      <div style={{ marginTop: 12, fontSize: 12 }}>
        <span style={{ color: 'var(--text-muted)' }}>Predicted winner: </span>
        <span style={{ color: 'var(--text-accent)', fontWeight: 500 }}>
          {winner.flag} {winner.name}
        </span>
      </div>
    </div>
  )
}
