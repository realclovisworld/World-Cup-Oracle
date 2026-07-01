// Header — app name, status chip, re-run button (IMPLEMENTATION.md §6.1 / DESIGN.md §5.1).

function minutesAgo(ts) {
  if (!ts) return 0
  return Math.floor((Date.now() / 1000 - ts) / 60)
}

export default function Header({ nSims, cachedAt, running, onRerun, lastResultDate }) {
  const chip = running
    ? 'Simulating…'
    : `${(nSims || 0).toLocaleString()} sims · ${minutesAgo(cachedAt)}m ago`

  return (
    <header
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 10,
        borderBottom: '0.5px solid var(--border)',
        paddingBottom: '1rem',
        marginBottom: '1.5rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 20 }} aria-hidden="true">🏆</span>
        <span style={{ fontSize: 18, fontWeight: 500, color: 'var(--text-primary)' }}>
          World Cup Oracle
        </span>
        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          2026 FIFA World Cup predictions
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }} aria-live="polite">
            {chip}
          </span>
          <button onClick={onRerun} disabled={running} aria-label="Re-run simulation">
            ↻ Re-run
          </button>
        </div>
        {lastResultDate && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Results current through {lastResultDate}
          </span>
        )}
      </div>
    </header>
  )
}
