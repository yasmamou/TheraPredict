import React, { useState } from 'react'
import LandingPage from './components/LandingPage'
import V1SimulationForm from './components/V1SimulationForm'
import V1ResultsDashboard from './components/V1ResultsDashboard'
import BodyDiagram from './components/BodyDiagram'

const API_BASE = '/api'

export default function App() {
  const [page, setPage] = useState('landing') // 'landing' | 'dashboard'
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const runV1Simulation = async (payload) => {
    setLoading(true)
    setError(null)
    try {
      // Try offline first, then online
      let res = await fetch(`${API_BASE}/v1/simulate/offline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        // Fallback to online
        res = await fetch(`${API_BASE}/v1/simulate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      }
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(detail.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Landing page
  if (page === 'landing') {
    document.body.style.background = '#fafafa'
    return <LandingPage onEnter={() => setPage('dashboard')} />
  }

  // Dashboard: dark mode
  document.body.style.background = '#020617'

  // Dashboard
  const bodyDiagramResult = result?.simulation ? {
    biodistribution_at_optimal: result.simulation.biodistribution_at_optimal || {},
  } : null

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <button onClick={() => setPage('landing')} style={styles.backBtn}>
            &larr;
          </button>
          <div>
            <h1 style={styles.title}>TheraPredict</h1>
            <p style={styles.subtitle}>Simulation Dashboard</p>
          </div>
        </div>
        <div style={styles.badge}>V1</div>
      </header>

      <main style={styles.main}>
        <div style={styles.leftPanel}>
          <V1SimulationForm onSubmit={runV1Simulation} loading={loading} />
        </div>

        <div style={styles.rightPanel}>
          {error && (
            <div style={styles.error}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {loading && (
            <div style={styles.loadingContainer}>
              <div style={styles.spinner} />
              <p style={{ color: '#e2e8f0' }}>Running V1 pipeline...</p>
              <p style={{ fontSize: '12px', color: '#64748b' }}>
                Normalizer &rarr; Knowledge &rarr; Parameters &rarr;
                PBPK &rarr; Dosimetry &rarr; PD &rarr; Decision
              </p>
            </div>
          )}

          {!loading && !result && !error && (
            <div style={styles.placeholder}>
              <div style={styles.placeholderIcon}>
                <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                  <circle cx="32" cy="32" r="30" stroke="#1e293b" strokeWidth="2" />
                  <circle cx="32" cy="32" r="20" stroke="#334155" strokeWidth="1" strokeDasharray="4 4">
                    <animateTransform attributeName="transform" type="rotate" from="0 32 32" to="360 32 32" dur="20s" repeatCount="indefinite" />
                  </circle>
                  <circle cx="32" cy="12" r="4" fill="#34d399">
                    <animateTransform attributeName="transform" type="rotate" from="0 32 32" to="360 32 32" dur="8s" repeatCount="indefinite" />
                  </circle>
                  <circle cx="32" cy="32" r="3" fill="#06b6d4" />
                </svg>
              </div>
              <h2 style={styles.placeholderTitle}>Ready to simulate</h2>
              <p style={styles.placeholderText}>
                Select a preset or configure your agent on the left panel,
                then click <strong>Run V1 Simulation</strong>.
              </p>
            </div>
          )}

          {!loading && result && (
            <>
              {bodyDiagramResult && <BodyDiagram result={bodyDiagramResult} />}
              <V1ResultsDashboard result={result} />
            </>
          )}
        </div>
      </main>
    </div>
  )
}

const styles = {
  app: { minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#020617' },
  header: {
    background: 'rgba(2,6,23,0.95)', backdropFilter: 'blur(20px)',
    borderBottom: '1px solid rgba(52,211,153,0.1)', padding: '12px 24px',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: '12px' },
  backBtn: {
    background: 'rgba(51,65,85,0.3)', border: '1px solid #334155',
    borderRadius: '8px', color: '#94a3b8', fontSize: '18px',
    width: '36px', height: '36px', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  title: {
    fontSize: '22px', fontWeight: 700,
    background: 'linear-gradient(90deg, #34d399, #06b6d4)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
  },
  subtitle: { fontSize: '12px', color: '#64748b' },
  badge: {
    background: '#065f46', color: '#6ee7b7', padding: '4px 14px',
    borderRadius: '12px', fontSize: '13px', fontWeight: 700,
  },
  main: { flex: 1, display: 'flex', overflow: 'hidden' },
  leftPanel: {
    width: '400px', minWidth: '400px', background: 'rgba(15,23,42,0.8)',
    borderRight: '1px solid rgba(51,65,85,0.3)', overflowY: 'auto', padding: '20px',
  },
  rightPanel: { flex: 1, overflowY: 'auto', padding: '24px', background: '#0f172a' },
  error: {
    background: 'rgba(127,29,29,0.5)', border: '1px solid #dc2626',
    borderRadius: '8px', padding: '12px 16px', marginBottom: '16px', color: '#fca5a5',
  },
  loadingContainer: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', height: '300px', gap: '12px',
  },
  spinner: {
    width: '40px', height: '40px', border: '3px solid #1e293b',
    borderTop: '3px solid #34d399', borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  placeholder: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', height: '400px', textAlign: 'center',
  },
  placeholderIcon: { marginBottom: '24px' },
  placeholderTitle: { fontSize: '22px', color: '#f1f5f9', marginBottom: '8px', fontWeight: 700 },
  placeholderText: { color: '#94a3b8', maxWidth: '400px', lineHeight: 1.6, fontSize: '14px' },
}
