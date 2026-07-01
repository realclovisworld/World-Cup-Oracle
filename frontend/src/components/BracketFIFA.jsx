// FIFA-style center-converging knockout bracket.
// Uses the app-wide DESIGN.md tokens (uniform colour scheme + dark mode) and
// scales to fit its container so the page never needs a horizontal scrollbar.
import { useEffect, useRef, useState } from 'react'
import { flagUrl } from '../flagCodes'
import { formatMatchDateTime } from '../utils'

// ── Layout constants ──────────────────────────────────────────────────────────
const CARD_W = 120
const ROW_H = 32
const CARD_H = ROW_H * 2 + 1 // 65
const META_H = 22
const UNIT = 100
const CONN_W = 48
const COL_W = CARD_W + CONN_W // 168
const FINAL_W = 148
const SF_GAP = 24

const TOTAL_H = 8 * UNIT // 800
const leftCardLeft = (r) => r * COL_W
const leftCardRight = (r) => leftCardLeft(r) + CARD_W
const leftSFx = 3 * COL_W // 504
const finalX = leftSFx + CARD_W + SF_GAP // 648
const rightSFx = finalX + FINAL_W + SF_GAP // 820
const rightCardLeft = (r) => rightSFx + (3 - r) * COL_W
const rightCardRight = (r) => rightCardLeft(r) + CARD_W
const TOTAL_W = rightCardLeft(0) + CARD_W // 1444

const slotH = (r) => UNIT * Math.pow(2, r)
const centreY = (r, i) => i * slotH(r) + slotH(r) / 2
const CENTRE = TOTAL_H / 2 // 400
const groupTop = (cy) => cy - META_H - CARD_H / 2

// ── Flag with emoji fallback ──────────────────────────────────────────────────
function Flag({ code, emoji, w = 20, h = 14 }) {
  const [err, setErr] = useState(false)
  const url = flagUrl(code)
  if (err || !url) return <span style={{ fontSize: h, lineHeight: 1, flexShrink: 0 }}>{emoji}</span>
  return (
    <img src={url} alt="" width={w} height={h} onError={() => setErr(true)}
      style={{ objectFit: 'cover', borderRadius: 2, flexShrink: 0 }} />
  )
}

// ── Team row (winner highlighted per DESIGN §5.4) ─────────────────────────────
function TeamRow({ code, name, emoji, score, pens, isWinner, isPh }) {
  const color = isPh
    ? 'var(--text-muted)'
    : isWinner
      ? 'var(--text-accent)'
      : 'var(--text-secondary)'
  return (
    <div
      style={{
        height: ROW_H,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '0 8px',
        background: isWinner && !isPh ? 'var(--bg-accent)' : 'transparent',
      }}
    >
      {!isPh && <Flag code={code} emoji={emoji} />}
      <span
        style={{
          flex: 1,
          fontSize: 12,
          fontWeight: isWinner && !isPh ? 600 : 400,
          color,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {isPh ? name : code || name}
      </span>
      {pens != null && <span style={{ fontSize: 11, color, opacity: 0.85, flexShrink: 0 }}>({pens})</span>}
      <span
        style={{
          fontSize: 13,
          fontWeight: isWinner && !isPh ? 700 : 400,
          color: isWinner && !isPh ? 'var(--text-accent)' : 'var(--text-muted)',
          minWidth: 12,
          textAlign: 'right',
          fontVariantNumeric: 'tabular-nums',
          flexShrink: 0,
        }}
      >
        {score != null ? score : ''}
      </span>
    </div>
  )
}

function MatchCard({ match, selected, isFinal, onClick, width = CARD_W }) {
  const wA = match.winner === 'a'
  const border = selected
    ? 'var(--border-strong)'
    : isFinal
      ? 'var(--border-accent)'
      : 'var(--border)'
  return (
    <button
      onClick={onClick}
      aria-label={`${match.team_a} vs ${match.team_b}${match.match_no ? ', ' + match.match_no : ''}`}
      style={{
        width,
        height: CARD_H,
        background: 'var(--surface-2)',
        border: `1px solid ${border}`,
        borderRadius: 6,
        padding: 0,
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        textAlign: 'left',
      }}
    >
      <TeamRow code={match.code_a} name={match.team_a} emoji={match.flag_a}
        score={match.score_a} pens={match.pens_a} isWinner={wA} isPh={!match.team_a} />
      <div style={{ height: 1, background: 'var(--border)', flexShrink: 0 }} />
      <TeamRow code={match.code_b} name={match.team_b} emoji={match.flag_b}
        score={match.score_b} pens={match.pens_b} isWinner={!wA} isPh={!match.team_b} />
    </button>
  )
}

function MatchGroup({ match, selected, isFinal, onClick, width = CARD_W }) {
  const status = match.is_actual ? 'Full time' : formatMatchDateTime(match.date, match.time)
  const meta = [match.match_no, status].filter(Boolean).join(' · ')
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width }}>
      <span
        style={{
          fontSize: 11,
          height: META_H,
          display: 'flex',
          alignItems: 'flex-end',
          paddingBottom: 2,
          color: 'var(--text-muted)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
        }}
      >
        {meta}
      </span>
      <MatchCard match={match} selected={selected} isFinal={isFinal} onClick={onClick} width={width} />
    </div>
  )
}

// ── Connector geometry ────────────────────────────────────────────────────────
function fourLines(x1, x2, yT, yB, yM, xDest) {
  const xMid = (x1 + x2) / 2
  return [
    [x1, yT, xMid, yT],
    [x1, yB, xMid, yB],
    [xMid, yT, xMid, yB],
    [xMid, yM, xDest, yM],
  ]
}

function buildLines(left, right) {
  const lines = []
  for (let r = 0; r <= 1; r++) {
    const dest = r === 0 ? left.r16 : left.qf
    for (let i = 0; i < dest.length; i++) {
      const yT = centreY(r, 2 * i)
      const yB = centreY(r, 2 * i + 1)
      lines.push(...fourLines(leftCardRight(r), leftCardLeft(r + 1), yT, yB, (yT + yB) / 2, leftCardLeft(r + 1)))
    }
  }
  if (left.sf) {
    lines.push(...fourLines(leftCardRight(2), leftSFx, centreY(2, 0), centreY(2, 1), CENTRE, leftSFx))
    lines.push([leftSFx + CARD_W, CENTRE, finalX, CENTRE])
  }
  for (let r = 0; r <= 1; r++) {
    const dest = r === 0 ? right.r16 : right.qf
    for (let i = 0; i < dest.length; i++) {
      const yT = centreY(r, 2 * i)
      const yB = centreY(r, 2 * i + 1)
      lines.push(...fourLines(rightCardLeft(r), rightCardRight(r + 1), yT, yB, (yT + yB) / 2, rightCardRight(r + 1)))
    }
  }
  if (right.sf) {
    lines.push(...fourLines(rightCardLeft(2), rightSFx + CARD_W, centreY(2, 0), centreY(2, 1), CENTRE, rightSFx + CARD_W))
    lines.push([rightSFx, CENTRE, finalX + FINAL_W, CENTRE])
  }
  return lines
}

function Placed({ left, cy, width, children }) {
  return <div style={{ position: 'absolute', left, top: groupTop(cy), width }}>{children}</div>
}

// ── Detail panel ──────────────────────────────────────────────────────────────
function TeamSummary({ code, name, emoji, score, pens, isWinner }) {
  const color = isWinner ? 'var(--text-accent)' : 'var(--text-secondary)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <Flag code={code} emoji={emoji} w={28} h={20} />
      <div>
        <div style={{ fontSize: 13, fontWeight: isWinner ? 700 : 400, color }}>
          {name}{pens != null && <span style={{ fontSize: 11 }}> ({pens})</span>}
        </div>
        {score != null && <div style={{ fontSize: 26, fontWeight: 700, lineHeight: 1, color }}>{score}</div>}
      </div>
    </div>
  )
}

function MatchDetailPanel({ match, onClose }) {
  const wA = match.winner === 'a'
  return (
    <div style={{ marginTop: 16, background: 'var(--surface-2)', border: '0.5px solid var(--border)', borderRadius: 10, padding: '1rem 1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <TeamSummary code={match.code_a} name={match.team_a} emoji={match.flag_a} score={match.score_a} pens={match.pens_a} isWinner={wA && match.is_actual} />
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>vs</span>
          <TeamSummary code={match.code_b} name={match.team_b} emoji={match.flag_b} score={match.score_b} pens={match.pens_b} isWinner={!wA && match.is_actual} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--surface-1)', borderRadius: 20, padding: '3px 10px' }}>{match.match_no ?? ''}</span>
          <button onClick={onClose} aria-label="Close" style={{ border: 'none', background: 'none', fontSize: 18, color: 'var(--text-muted)', cursor: 'pointer', lineHeight: 1 }}>×</button>
        </div>
      </div>
      {match.is_actual ? (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', paddingTop: 4 }}>
          Full time{match.venue ? ` · ${match.venue}` : ''}
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', height: 6, borderRadius: 4, overflow: 'hidden', marginBottom: 6 }}>
            <div style={{ background: '#378ADD', width: `${wA ? match.win_prob : 100 - match.win_prob}%` }} />
            <div style={{ background: '#D85A30', width: `${wA ? 100 - match.win_prob : match.win_prob}%` }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 14 }}>
            <span>{match.team_a} {wA ? match.win_prob : (100 - match.win_prob).toFixed(1)}%</span>
            <span style={{ fontSize: 10 }}>10k sim</span>
            <span>{match.team_b} {wA ? (100 - match.win_prob).toFixed(1) : match.win_prob}%</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
            {[
              { label: `xG — ${match.team_a}`, value: match.xg_a?.toFixed(1) },
              { label: 'Likely score', value: `${match.score_a} – ${match.score_b}` },
              { label: `xG — ${match.team_b}`, value: match.xg_b?.toFixed(1) },
            ].map(({ label, value }) => (
              <div key={label} style={{ background: 'var(--surface-1)', border: '0.5px solid var(--border)', borderRadius: 8, padding: '10px 0', textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>{value ?? '–'}</div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 10 }}>
            Predicted winner: <span style={{ color: 'var(--text-accent)', fontWeight: 600 }}>{wA ? match.team_a : match.team_b}</span>
          </div>
        </>
      )}
    </div>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────────
export default function BracketFIFA({ data }) {
  const [sel, setSel] = useState(null)
  const wrapRef = useRef(null)
  const [scale, setScale] = useState(1)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const measure = () => setScale(Math.min(1, el.clientWidth / TOTAL_W))
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  if (!data) return null

  const R = (n) => data.rounds[n]?.matches ?? []
  const left = { r32: R(0).slice(0, 8), r16: R(1).slice(0, 4), qf: R(2).slice(0, 2), sf: R(3)[0] ?? null }
  const right = { r32: R(0).slice(8, 16), r16: R(1).slice(4, 8), qf: R(2).slice(2, 4), sf: R(3)[1] ?? null }
  const final_ = R(4)[0] ?? null

  const click = (key, match) => setSel((s) => (s && s.key === key ? null : { key, match }))
  const isSel = (key) => sel && sel.key === key
  const lines = buildLines(left, right)

  const arm = (side, cols, xOf) =>
    cols.map((matches, r) =>
      matches.map((m, i) => {
        const key = `${side}-${r}-${i}`
        return (
          <Placed key={key} left={xOf(r)} cy={centreY(r, i)} width={CARD_W}>
            <MatchGroup match={m} selected={isSel(key)} onClick={() => click(key, m)} />
          </Placed>
        )
      })
    )

  return (
    <div className="card" style={{ padding: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12, flexWrap: 'wrap', gap: 6 }}>
        <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Predicted knockout bracket</span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>real results · predictions · click any match</span>
      </div>

      {/* Fit-to-width: scale the fixed-size bracket down so the page never scrolls sideways. */}
      <div ref={wrapRef} style={{ width: '100%' }}>
        <div style={{ width: TOTAL_W * scale, height: TOTAL_H * scale, margin: '0 auto' }}>
          <div style={{ width: TOTAL_W, height: TOTAL_H, position: 'relative', transform: `scale(${scale})`, transformOrigin: 'top left' }}>
            <svg aria-hidden="true" style={{ position: 'absolute', top: 0, left: 0, width: TOTAL_W, height: TOTAL_H, pointerEvents: 'none', overflow: 'visible' }}>
              {lines.map(([x1, y1, x2, y2], i) => (
                <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--border-strong)" strokeWidth="1" />
              ))}
            </svg>

            {arm('left', [left.r32, left.r16, left.qf], leftCardLeft)}
            {arm('right', [right.r32, right.r16, right.qf], rightCardLeft)}

            {left.sf && (
              <Placed left={leftSFx} cy={CENTRE} width={CARD_W}>
                <MatchGroup match={left.sf} selected={isSel('sf-left')} onClick={() => click('sf-left', left.sf)} />
              </Placed>
            )}
            {right.sf && (
              <Placed left={rightSFx} cy={CENTRE} width={CARD_W}>
                <MatchGroup match={right.sf} selected={isSel('sf-right')} onClick={() => click('sf-right', right.sf)} />
              </Placed>
            )}
            {final_ && (
              <Placed left={finalX} cy={CENTRE} width={FINAL_W}>
                <span style={{ fontSize: 13, color: 'var(--text-muted)', display: 'block', marginBottom: 2 }}>Final</span>
                <MatchGroup match={final_} selected={isSel('final')} isFinal onClick={() => click('final', final_)} width={FINAL_W} />
              </Placed>
            )}
          </div>
        </div>
      </div>

      {sel && <MatchDetailPanel match={sel.match} onClose={() => setSel(null)} />}
    </div>
  )
}
