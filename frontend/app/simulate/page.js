'use client'

import dynamic from 'next/dynamic'
import Link from 'next/link'
import React, { useState } from 'react'
import V1SimulationForm from '../../src/components/V1SimulationForm'

// Plotly needs to be loaded client-side only (no SSR)
const V1ResultsDashboard = dynamic(
  () => import('../../src/components/V1ResultsDashboard'),
  { ssr: false }
)
const BodyDiagram = dynamic(
  () => import('../../src/components/BodyDiagram'),
  { ssr: false }
)

export default function SimulatePage() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Try multiple API endpoints: local dev, then production backend
  const API_URLS = [
    '/api/v1/simulate/offline',
    '/api/v1/simulate',
    'http://localhost:8000/api/v1/simulate/offline',
    'http://localhost:8000/api/v1/simulate',
  ]

  const runSimulation = async (payload) => {
    setLoading(true)
    setError(null)
    try {
      let data = null
      for (const url of API_URLS) {
        try {
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          })
          if (res.ok) {
            data = await res.json()
            break
          }
        } catch {
          continue
        }
      }
      if (!data) {
        throw new Error(
          'Simulation backend not available. ' +
          'The simulation engine requires a running Python backend. ' +
          'Run locally: PYTHONPATH=src python3 -m uvicorn theranostics.api.main:app --port 8000'
        )
      }
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const bodyDiagramResult = result?.simulation
    ? { biodistribution_at_optimal: result.simulation.biodistribution_at_optimal || {} }
    : null

  return (
    <div style={S.app}>
      <header style={S.header}>
        <div style={S.headerLeft}>
          <Link href="/" style={S.backBtn}>&larr;</Link>
          <div>
            <h1 style={S.title}>TheraPredict</h1>
            <p style={S.subtitle}>Simulation Dashboard</p>
          </div>
        </div>
        <div style={S.badge}>V1</div>
      </header>

      <main style={S.main}>
        <div style={S.leftPanel}>
          <V1SimulationForm onSubmit={runSimulation} loading={loading} />
        </div>

        <div style={S.rightPanel}>
          {error && (
            <div style={S.error}>
              <strong style={{display:'block',marginBottom:'8px'}}>Simulation unavailable</strong>
              <p style={{margin:0,fontSize:'13px',lineHeight:1.6}}>{error}</p>
              {error.includes('backend') && (
                <div style={{marginTop:'12px',padding:'12px',background:'rgba(0,0,0,0.2)',borderRadius:'6px',fontSize:'12px',fontFamily:'monospace',color:'#94a3b8'}}>
                  PYTHONPATH=src python3 -m uvicorn theranostics.api.main:app --port 8000
                </div>
              )}
            </div>
          )}

          {loading && (
            <div style={S.loadingContainer}>
              <div style={S.spinner} />
              <p style={{ color: '#e2e8f0' }}>Running V1 pipeline...</p>
              <p style={{ fontSize: '12px', color: '#64748b' }}>
                Normalizer &rarr; Knowledge &rarr; Parameters &rarr;
                PBPK &rarr; Dosimetry &rarr; PD &rarr; Decision
              </p>
            </div>
          )}

          {!loading && !result && !error && (
            <div style={S.placeholder}>
              <h2 style={S.placeholderTitle}>Ready to simulate</h2>
              <p style={S.placeholderText}>
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

const S = {
  app: { minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#020617', color: '#e2e8f0' },
  header: {
    background: 'rgba(2,6,23,0.95)', backdropFilter: 'blur(20px)',
    borderBottom: '1px solid rgba(52,211,153,0.1)', padding: '12px 24px',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: '12px' },
  backBtn: {
    background: 'rgba(51,65,85,0.3)', border: '1px solid #334155',
    borderRadius: '8px', color: '#94a3b8', fontSize: '18px',
    width: '36px', height: '36px', display: 'flex', alignItems: 'center',
    justifyContent: 'center', textDecoration: 'none',
  },
  title: {
    fontSize: '22px', fontWeight: 700, margin: 0,
    background: 'linear-gradient(90deg, #34d399, #06b6d4)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
  },
  subtitle: { fontSize: '12px', color: '#64748b', margin: 0 },
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
  placeholderTitle: { fontSize: '22px', color: '#f1f5f9', fontWeight: 700 },
  placeholderText: { color: '#94a3b8', maxWidth: '400px', lineHeight: 1.6, fontSize: '14px' },
}
