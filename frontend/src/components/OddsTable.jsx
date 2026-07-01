// OddsTable — sortable per-team stage odds (IMPLEMENTATION.md §6.2 / DESIGN.md §5.2).
import { useMemo, useState } from 'react'

const PROB_COLS = [
  { key: 'p_r16', label: 'R16' },
  { key: 'p_qf', label: 'QF' },
  { key: 'p_sf', label: 'SF' },
  { key: 'p_final', label: 'Final' },
  { key: 'p_title', label: 'Title' },
]

function Bar({ value }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
      <div
        style={{
          width: 40,
          height: 5,
          borderRadius: 3,
          background: 'var(--surface-1)',
          overflow: 'hidden',
        }}
      >
        <div
          role="meter"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={100}
          style={{ width: `${value}%`, height: '100%', background: 'rgba(55,138,221,0.7)' }}
        />
      </div>
      <span style={{ fontSize: 12, minWidth: 28, textAlign: 'right' }}>{value}%</span>
    </div>
  )
}

function Th({ children, sortable, active, dir, onClick, align = 'left' }) {
  return (
    <th
      onClick={sortable ? onClick : undefined}
      style={{
        fontSize: 12,
        fontWeight: 500,
        color: active ? 'var(--text-primary)' : 'var(--text-muted)',
        textAlign: align,
        padding: '6px 0',
        borderBottom: '0.5px solid var(--border)',
        cursor: sortable ? 'pointer' : 'default',
        position: 'sticky',
        top: 0,
        background: 'var(--surface-2)',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
      {active ? (dir === 'desc' ? ' ▼' : ' ▲') : ''}
    </th>
  )
}

export default function OddsTable({ rows }) {
  const [sortKey, setSortKey] = useState('p_title')
  const [sortDir, setSortDir] = useState('desc')

  const sorted = useMemo(() => {
    const out = [...rows].sort((a, b) => {
      const d = a[sortKey] - b[sortKey]
      return sortDir === 'desc' ? -d : d
    })
    return out
  }, [rows, sortKey, sortDir])

  const onSort = (key) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  return (
    <div className="card">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
        }}
      >
        <span style={{ fontSize: 14, fontWeight: 500 }}>Title odds</span>
      </div>

      <div style={{ maxHeight: 480, overflow: 'auto' }}>
        <table style={{ width: '100%', minWidth: 560, borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              <Th align="right">#</Th>
              <Th>Team</Th>
              <Th align="center">Grp</Th>
              <Th
                sortable
                align="right"
                active={sortKey === 'elo'}
                dir={sortDir}
                onClick={() => onSort('elo')}
              >
                Elo
              </Th>
              {PROB_COLS.map((c) => (
                <Th
                  key={c.key}
                  sortable
                  align="right"
                  active={sortKey === c.key}
                  dir={sortDir}
                  onClick={() => onSort(c.key)}
                >
                  {c.label}
                </Th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr
                key={r.code}
                style={{ borderTop: '0.5px solid var(--border)' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface-1)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={{ width: 28, textAlign: 'right', color: 'var(--text-muted)', fontWeight: 500 }}>
                  {i + 1}
                </td>
                <td
                  style={{
                    minWidth: 140,
                    maxWidth: 180,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    color: 'var(--text-secondary)',
                    padding: '4px 8px 4px 0',
                  }}
                >
                  <span aria-hidden="true">{r.flag}</span> {r.name}
                </td>
                <td style={{ width: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
                  {r.group}
                </td>
                <td style={{ width: 52, textAlign: 'right', color: 'var(--text-muted)' }}>{r.elo}</td>
                {PROB_COLS.map((c) => (
                  <td key={c.key} style={{ padding: '4px 0' }}>
                    <Bar value={r[c.key]} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
