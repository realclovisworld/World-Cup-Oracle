// Bracket — fixed-layout knockout tree with SVG connectors (IMPLEMENTATION.md §6.4 / DESIGN.md §5.4).

// Layout constants — do not change; the connector math depends on them.
const U = 40        // height of one R32 slot
const MH = 36       // match card height
const RW = 132      // round column width
const CW = 24       // connector gap width
const TH = 16 * U   // total bracket height (640)
const TW = 5 * RW + 4 * CW // total width (756)

const ROUND_FULL = {
  R32: 'Round of 32',
  R16: 'Round of 16',
  QF: 'Quarter-final',
  SF: 'Semi-final',
  Final: 'Final',
}

// Vertical centre of slot i in round r.
function gct(r, i) {
  const s = U * (1 << r)
  return i * s + s / 2
}

function ConnectorSVG({ rounds }) {
  const lines = []
  for (let r = 0; r < rounds.length - 1; r++) {
    const next = rounds[r + 1].matches
    for (let i = 0; i < next.length; i++) {
      const xR = r * (RW + CW) + RW
      const xC = xR + CW / 2
      const xN = (r + 1) * (RW + CW)
      const yT = gct(r, 2 * i)
      const yB = gct(r, 2 * i + 1)
      const yM = (yT + yB) / 2
      lines.push([xR, yT, xC, yT])
      lines.push([xR, yB, xC, yB])
      lines.push([xC, yT, xC, yB])
      lines.push([xC, yM, xN, yM])
    }
  }
  return (
    <svg
      width={TW}
      height={TH}
      aria-hidden="true"
      style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
    >
      {lines.map(([x1, y1, x2, y2], i) => (
        <line
          key={i}
          x1={x1}
          y1={y1}
          x2={x2}
          y2={y2}
          stroke="var(--border-strong)"
          strokeWidth="0.8"
        />
      ))}
    </svg>
  )
}

function Row({ flag, name, score, isWinner }) {
  return (
    <div
      style={{
        height: 17,
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '0 6px',
        background: isWinner ? 'var(--bg-accent)' : 'transparent',
      }}
    >
      <span style={{ fontSize: 11 }} aria-hidden="true">{flag}</span>
      <span
        style={{
          fontSize: 11,
          fontWeight: isWinner ? 500 : 400,
          color: isWinner ? 'var(--text-accent)' : 'var(--text-secondary)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          flex: 1,
        }}
      >
        {name}
      </span>
      <span
        style={{
          fontSize: 11,
          fontWeight: isWinner ? 500 : 400,
          color: isWinner ? 'var(--text-accent)' : 'var(--text-muted)',
        }}
      >
        {score}
      </span>
    </div>
  )
}

function MatchCard({ match, round, index, roundName, isFinal, selected, onSelect }) {
  const s = U * (1 << round)
  const top = index * s + (s - MH) / 2
  const left = round * (RW + CW)
  const aWins = match.winner === 'a'

  return (
    <button
      onClick={() => onSelect({ round, index, match })}
      aria-label={`${match.team_a} vs ${match.team_b}, ${ROUND_FULL[roundName]}`}
      style={{
        position: 'absolute',
        top,
        left,
        width: RW,
        height: MH,
        padding: 0,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 6,
        overflow: 'hidden',
        boxSizing: 'border-box',
        border: selected
          ? '0.5px solid var(--border-strong)'
          : isFinal
            ? '0.5px solid var(--border-accent)'
            : '0.5px solid var(--border)',
        background: 'var(--surface-2)',
        cursor: 'pointer',
      }}
    >
      {match.is_actual && (
        <div
          style={{ position: 'absolute', top: 2, right: 4, fontSize: 9, color: 'var(--text-muted)' }}
          aria-hidden="true"
        >
          FT
        </div>
      )}
      <Row flag={match.flag_a} name={match.team_a} score={match.score_a} isWinner={aWins} />
      <div style={{ height: 1, background: 'var(--border)' }} />
      <Row flag={match.flag_b} name={match.team_b} score={match.score_b} isWinner={!aWins} />
    </button>
  )
}

export default function Bracket({ data, selected, onSelect, nSims }) {
  return (
    <div className="card" style={{ padding: '1rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 12,
        }}
      >
        <span style={{ fontSize: 14, fontWeight: 500 }}>Predicted knockout bracket</span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {(nSims || 0).toLocaleString()} sims · click any match
        </span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        {/* Round labels */}
        <div style={{ display: 'flex', minWidth: TW, marginBottom: 6 }}>
          {data.rounds.map((round, r) => (
            <div key={round.name} style={{ display: 'flex' }}>
              <div
                style={{
                  width: RW,
                  textAlign: 'center',
                  fontSize: 11,
                  fontWeight: 500,
                  color: 'var(--text-muted)',
                }}
              >
                {round.name}
              </div>
              {r < data.rounds.length - 1 && <div style={{ width: CW }} />}
            </div>
          ))}
        </div>

        {/* Bracket body */}
        <div style={{ position: 'relative', height: TH, minWidth: TW }}>
          <ConnectorSVG rounds={data.rounds} />
          {data.rounds.map((round, r) =>
            round.matches.map((match, i) => (
              <MatchCard
                key={`${r}-${i}`}
                match={match}
                round={r}
                index={i}
                roundName={round.name}
                isFinal={round.name === 'Final'}
                selected={selected && selected.round === r && selected.index === i}
                onSelect={onSelect}
              />
            )),
          )}
        </div>
      </div>
    </div>
  )
}
