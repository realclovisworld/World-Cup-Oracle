// App shell — data loading, status polling, layout (IMPLEMENTATION.md §Phase 7).
import { useState, useEffect, useCallback } from 'react'
import {
  fetchOdds,
  fetchTeams,
  fetchBracket,
  fetchStatus,
  triggerRerun,
} from './api'
import Header from './components/Header'
import OddsTable from './components/OddsTable'
import HeadToHead from './components/HeadToHead'
import BracketFIFA from './components/BracketFIFA'
import './styles.css'

export default function App() {
  const [status, setStatus] = useState(null)
  const [odds, setOdds] = useState([])
  const [teams, setTeams] = useState([])
  const [bracket, setBracket] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      const [s, o, t, b] = await Promise.all([
        fetchStatus(),
        fetchOdds(),
        fetchTeams(),
        fetchBracket(),
      ])
      setStatus(s)
      setOdds(o)
      setTeams(t)
      setBracket(b)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  // Initial load: poll status until ready, then fetch the data.
  useEffect(() => {
    let cancelled = false
    const boot = async () => {
      try {
        let s = await fetchStatus()
        while (!s.ready && !cancelled) {
          await new Promise((r) => setTimeout(r, 2000))
          s = await fetchStatus()
        }
        if (!cancelled) load()
      } catch (e) {
        if (!cancelled) setError(e.message)
      }
    }
    boot()
    return () => {
      cancelled = true
    }
  }, [load])

  // Poll status while a re-run is in progress, then reload data.
  useEffect(() => {
    if (!status?.running) return
    const id = setInterval(async () => {
      const s = await fetchStatus()
      setStatus(s)
      if (!s.running) {
        clearInterval(id)
        load()
      }
    }, 2000)
    return () => clearInterval(id)
  }, [status?.running, load])

  const handleRerun = async () => {
    try {
      await triggerRerun(10_000)
      setStatus((s) => ({ ...s, running: true }))
    } catch (e) {
      setError(e.message)
    }
  }

  if (error) {
    return <div style={{ padding: '2rem', color: 'var(--text-danger)' }}>{error}</div>
  }
  if (!status?.ready) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          color: 'var(--text-muted)',
          fontSize: 14,
        }}
        aria-live="polite"
      >
        ⟳ Simulating tournament…
      </div>
    )
  }

  return (
    <div style={{ width: '100%', maxWidth: 1600, margin: '0 auto', padding: '1.5rem' }}>
      <Header
        nSims={status.n_sims}
        cachedAt={status.cached_at}
        running={status.running}
        onRerun={handleRerun}
        lastResultDate={status.last_result_date}
      />

      <div
        className="two-col"
        style={{
          display: 'grid',
          // Asymmetric: the odds table needs ~650px to show every stage column
          // without scrolling; the head-to-head panel is comfortable narrower.
          // (DESIGN's literal 1fr/1fr hides the Title column — see note.)
          gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)',
          gap: '1.5rem',
          marginBottom: '1.5rem',
        }}
      >
        <OddsTable rows={odds} />
        <HeadToHead teams={teams} />
      </div>

      {bracket && <BracketFIFA data={bracket} />}
    </div>
  )
}
