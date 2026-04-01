import React, { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'

const TAB_LIST = ['Results', 'PK', 'Dosimetry', 'Effect', 'Logs', 'Sources']

export default function V1ResultsDashboard({ result }) {
  const [activeTab, setActiveTab] = useState('Results')
  if (!result) return null

  const sim = result.simulation || {}
  const dosimetry = result.dosimetry || null
  const pd = result.pd_effect || {}
  const knowledge = result.knowledge || {}
  const params = result.parameters || {}
  const decision = result.decision || {}
  const confidence = result.confidence_per_module || {}
  const logs = result.execution_trace || []
  const warnings = result.warnings || []

  return (
    <div style={styles.dashboard}>
      {/* Tabs */}
      <div style={styles.tabs}>
        {TAB_LIST.map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            style={{ ...styles.tab, ...(activeTab === tab ? styles.tabActive : {}) }}>
            {tab}
          </button>
        ))}
      </div>

      {/* Warnings banner */}
      {warnings.length > 0 && (
        <div style={styles.warningBanner}>
          <strong>Warnings ({warnings.length}):</strong>
          <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
            {warnings.slice(0, 5).map((w, i) => <li key={i} style={{ fontSize: '12px' }}>{w}</li>)}
            {warnings.length > 5 && <li style={{ fontSize: '12px', color: '#94a3b8' }}>...and {warnings.length - 5} more</li>}
          </ul>
        </div>
      )}

      {activeTab === 'Results' && <ResultsTab sim={sim} decision={decision} confidence={confidence} pd={pd} />}
      {activeTab === 'PK' && <PKTab sim={sim} params={params} />}
      {activeTab === 'Dosimetry' && <DosimetryTab dosimetry={dosimetry} />}
      {activeTab === 'Effect' && <EffectTab pd={pd} />}
      {activeTab === 'Logs' && <LogsTab logs={logs} />}
      {activeTab === 'Sources' && <SourcesTab knowledge={knowledge} params={params} />}
    </div>
  )
}

// === Results Tab ===
function ResultsTab({ sim, decision, confidence, pd }) {
  const metrics = [
    { label: 'Tumor Peak', value: sim.tumor_peak_concentration_nM?.toFixed(2), unit: 'nM', ci: sim.mc_ci_tumor, color: '#38bdf8' },
    { label: 'TBR Peak', value: sim.tbr_peak?.toFixed(1), unit: 'ratio', ci: sim.mc_ci_tbr, color: '#a78bfa' },
    { label: 'Optimal Time', value: sim.optimal_imaging_time_h?.toFixed(1), unit: 'hours', color: '#34d399' },
    { label: 'Plasma t1/2', value: sim.plasma_half_life_h?.toFixed(1), unit: 'hours', color: '#fb923c' },
  ]

  return (
    <div style={styles.tabContent}>
      <div style={styles.cards}>
        {metrics.map((m, i) => (
          <div key={i} style={styles.card}>
            <div style={{ ...styles.cardLabel, color: m.color }}>{m.label}</div>
            <div style={styles.cardValue}>{m.value || '--'} <span style={styles.cardUnit}>{m.unit}</span></div>
            {m.ci && m.ci[0] > 0 && <div style={styles.cardCI}>90% CI: [{m.ci[0]?.toFixed(2)} - {m.ci[1]?.toFixed(2)}]</div>}
          </div>
        ))}
      </div>

      {/* Decision summary */}
      {decision.summary && (
        <Panel title="Decision">
          <p style={{ color: '#e2e8f0', fontSize: '14px', margin: 0 }}>{decision.summary}</p>
          {decision.score?.aggregated && (
            <div style={{ display: 'flex', gap: '16px', marginTop: '12px', flexWrap: 'wrap' }}>
              <ScoreBadge label="Efficacy" value={decision.score.aggregated.efficacy} />
              <ScoreBadge label="Safety" value={decision.score.aggregated.safety} />
              <ScoreBadge label="Practicality" value={decision.score.aggregated.practicality} />
              <ScoreBadge label="Confidence" value={decision.score.aggregated.confidence} />
              <ScoreBadge label="Combined" value={decision.score.aggregated.combined} highlight />
            </div>
          )}
          {decision.why?.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <span style={{ fontSize: '11px', color: '#34d399' }}>Strengths: </span>
              <span style={{ fontSize: '12px', color: '#cbd5e1' }}>{decision.why.join(' | ')}</span>
            </div>
          )}
          {decision.why_not?.length > 0 && (
            <div style={{ marginTop: '4px' }}>
              <span style={{ fontSize: '11px', color: '#f87171' }}>Concerns: </span>
              <span style={{ fontSize: '12px', color: '#cbd5e1' }}>{decision.why_not.join(' | ')}</span>
            </div>
          )}
        </Panel>
      )}

      {/* PD Effect summary */}
      {pd.effect_direction && (
        <Panel title="Biological Effect">
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
            <Tag color="#818cf8">{pd.effect_type}</Tag>
            <Tag color="#38bdf8">{pd.effect_direction?.replace(/_/g, ' ')}</Tag>
            {pd.occupancy_estimate != null && (
              <Tag color="#34d399">Occupancy: {(pd.occupancy_estimate * 100).toFixed(0)}%</Tag>
            )}
          </div>
          {pd.rationale_text && <p style={{ fontSize: '12px', color: '#94a3b8', marginTop: '8px', lineHeight: 1.5 }}>{pd.rationale_text}</p>}
        </Panel>
      )}

      {/* Confidence per module */}
      <Panel title="Confidence per Module">
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {Object.entries(confidence).map(([mod, score]) => (
            <div key={mod} style={styles.confBox}>
              <div style={styles.confLabel}>{mod}</div>
              <div style={{ ...styles.confBar, width: `${Math.round(score * 100)}%`, background: score > 0.6 ? '#34d399' : score > 0.4 ? '#fbbf24' : '#f87171' }} />
              <div style={styles.confValue}>{(score * 100).toFixed(0)}%</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  )
}

// === PK Tab ===
function PKTab({ sim, params }) {
  const organTS = sim.organ_timeseries || {}
  const keyOrgans = ['plasma', 'tumor', 'kidney', 'liver', 'spleen', 'muscle', 'salivary_glands', 'bone_marrow']
  const colors = { plasma: '#ef4444', tumor: '#ec4899', kidney: '#10b981', liver: '#f59e0b', spleen: '#8b5cf6', muscle: '#6b7280', salivary_glands: '#06b6d4', bone_marrow: '#a78bfa' }

  const timePoints = sim.time_points || []
  const step = Math.max(1, Math.floor(timePoints.length / 300))
  const sampledTimes = timePoints.filter((_, i) => i % step === 0)

  const traces = keyOrgans.map(name => {
    const ts = organTS[name]
    if (!ts) return null
    const total = ts.total || []
    const sampledVals = total.filter((_, i) => i % step === 0)
    return {
      x: sampledTimes, y: sampledVals,
      name: name === 'tumor' ? 'TUMOR' : name.replace(/_/g, ' '),
      type: 'scatter', mode: 'lines',
      line: { color: colors[name] || '#94a3b8', width: name === 'tumor' ? 3 : 1.5 },
    }
  }).filter(Boolean)

  const biodist = sim.biodistribution_at_optimal || {}
  const biodistEntries = Object.entries(biodist).filter(([k, v]) => v > 0 && k !== 'rest_of_body').sort((a, b) => b[1] - a[1]).slice(0, 12)

  return (
    <div style={styles.tabContent}>
      <div style={styles.chartContainer}>
        <Plot data={traces} layout={{
          title: { text: 'Time-Activity Curves', font: { color: '#e2e8f0', size: 14 } },
          paper_bgcolor: '#1e293b', plot_bgcolor: '#0f172a',
          xaxis: { title: 'Time (hours)', color: '#94a3b8', gridcolor: '#1e293b' },
          yaxis: { title: 'Concentration (nM)', color: '#94a3b8', gridcolor: '#1e293b', type: 'log' },
          legend: { font: { color: '#94a3b8' }, bgcolor: 'transparent' },
          margin: { l: 60, r: 20, t: 40, b: 50 }, height: 380,
        }} config={{ responsive: true, displayModeBar: false }} style={{ width: '100%' }} />
      </div>

      <div style={styles.chartContainer}>
        <Plot data={[{
          x: biodistEntries.map(([k]) => k === 'tumor' ? 'TUMOR' : k.replace(/_/g, ' ')),
          y: biodistEntries.map(([, v]) => v),
          type: 'bar',
          marker: { color: biodistEntries.map(([k]) => k === 'tumor' ? '#ec4899' : '#38bdf8'), opacity: 0.85 },
        }]} layout={{
          title: { text: `Biodistribution at t=${sim.optimal_imaging_time_h?.toFixed(1)}h`, font: { color: '#e2e8f0', size: 14 } },
          paper_bgcolor: '#1e293b', plot_bgcolor: '#0f172a',
          xaxis: { color: '#94a3b8', tickangle: -45 },
          yaxis: { title: 'Concentration (nM)', color: '#94a3b8', gridcolor: '#1e293b' },
          margin: { l: 60, r: 20, t: 40, b: 100 }, height: 320,
        }} config={{ responsive: true, displayModeBar: false }} style={{ width: '100%' }} />
      </div>

      {/* Parameters summary */}
      <Panel title="PK Parameters">
        <KVTable data={{
          'Clearance route': params.pk_params?.clearance_route,
          'Half-life': `${params.pk_params?.half_life_h} h`,
          'Total CL': `${params.pk_params?.total_clearance_l_per_h} L/h`,
          'BBB permeability': params.pk_params?.bbb_permeability,
          'Kd': `${params.binding_params?.kd_nM} nM`,
          'Kon': `${params.binding_params?.kon_per_M_per_s} M-1s-1`,
          'Koff': `${params.binding_params?.koff_per_s} s-1`,
        }} />
      </Panel>
    </div>
  )
}

// === Dosimetry Tab ===
function DosimetryTab({ dosimetry }) {
  if (!dosimetry) return <Panel title="Dosimetry"><p style={{ color: '#94a3b8' }}>No dosimetry data (diagnostic isotope or no isotope).</p></Panel>

  const organs = Object.entries(dosimetry.organ_doses_total_gy || {})
    .filter(([k]) => k !== 'plasma')
    .sort((a, b) => b[1] - a[1])

  return (
    <div style={styles.tabContent}>
      <Panel title="Organ Doses">
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Organ</th>
              <th style={styles.th}>Dose (Gy)</th>
              <th style={styles.th}>Gy/GBq</th>
              <th style={styles.th}>Status</th>
            </tr>
          </thead>
          <tbody>
            {organs.map(([organ, dose]) => (
              <tr key={organ}>
                <td style={styles.td}>{organ === dosimetry.dose_limiting_organ ? `${organ} (DLO)` : organ}</td>
                <td style={styles.td}>{dose.toFixed(3)}</td>
                <td style={styles.td}>{(dosimetry.organ_doses_gy_per_gbq?.[organ] || 0).toFixed(4)}</td>
                <td style={styles.td}>
                  {organ === dosimetry.dose_limiting_organ
                    ? <span style={{ color: '#fbbf24' }}>Dose-limiting</span>
                    : <span style={{ color: '#34d399' }}>OK</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
      <Panel title="Summary">
        <KVTable data={{
          'Tumor dose': `${dosimetry.tumor_dose_total_gy?.toFixed(2)} Gy`,
          'Dose-limiting organ': dosimetry.dose_limiting_organ,
          'Therapeutic index': dosimetry.therapeutic_index?.toFixed(2),
          'Tumor/Kidney': dosimetry.tumor_to_kidney_ratio?.toFixed(2),
          'Injected': `${dosimetry.injected_gbq} GBq`,
        }} />
      </Panel>
      {dosimetry.hypotheses?.length > 0 && (
        <Panel title="Hypotheses">
          <ul style={{ margin: 0, padding: '0 0 0 16px' }}>
            {dosimetry.hypotheses.map((h, i) => <li key={i} style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>{h}</li>)}
          </ul>
        </Panel>
      )}
    </div>
  )
}

// === Effect Tab ===
function EffectTab({ pd }) {
  return (
    <div style={styles.tabContent}>
      <Panel title="PD / Biological Effect">
        <KVTable data={{
          'Effect type': pd.effect_type,
          'Effect direction': pd.effect_direction?.replace(/_/g, ' '),
          'Target engagement': `${((pd.target_engagement_score || 0) * 100).toFixed(0)}%`,
          'Plausibility': `${((pd.biological_plausibility_score || 0) * 100).toFixed(0)}%`,
          'Confidence': `${((pd.confidence_score || 0) * 100).toFixed(0)}%`,
          'Occupancy': pd.occupancy_estimate != null ? `${(pd.occupancy_estimate * 100).toFixed(0)}%` : 'N/A',
        }} />
      </Panel>
      {pd.rationale_text && <Panel title="Rationale"><p style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: 1.6, margin: 0 }}>{pd.rationale_text}</p></Panel>}
      {pd.toxicity_risks?.length > 0 && (
        <Panel title="Toxicity Risks">
          <table style={styles.table}>
            <thead><tr><th style={styles.th}>Organ</th><th style={styles.th}>Effect</th><th style={styles.th}>Severity</th></tr></thead>
            <tbody>
              {pd.toxicity_risks.map((r, i) => (
                <tr key={i}>
                  <td style={styles.td}>{r.organ}</td>
                  <td style={styles.td}>{r.effect || `${r.estimated_dose_gy?.toFixed(1)} / ${r.threshold_gy} Gy`}</td>
                  <td style={styles.td}><span style={{ color: r.severity === 'high' ? '#ef4444' : r.severity === 'moderate' ? '#fbbf24' : '#94a3b8' }}>{r.severity}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
      {pd.formulas_used?.length > 0 && (
        <Panel title="Formulas Used">
          {pd.formulas_used.map((f, i) => <div key={i} style={{ fontSize: '12px', color: '#94a3b8', fontFamily: 'monospace', marginBottom: '4px' }}>{f}</div>)}
        </Panel>
      )}
      {pd.rules_activated?.length > 0 && (
        <Panel title="Rules Activated">
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {pd.rules_activated.map((r, i) => <Tag key={i} color="#475569">{r}</Tag>)}
          </div>
        </Panel>
      )}
    </div>
  )
}

// === Logs Tab ===
function LogsTab({ logs }) {
  const [filter, setFilter] = useState('ALL')
  const levels = ['ALL', 'AUDIT', 'INFO', 'WARNING', 'ERROR']
  const filtered = filter === 'ALL' ? logs : logs.filter(l => l.level === filter)

  return (
    <div style={styles.tabContent}>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        {levels.map(lv => (
          <button key={lv} onClick={() => setFilter(lv)}
            style={{ ...styles.filterBtn, ...(filter === lv ? { background: '#334155', color: '#e2e8f0' } : {}) }}>
            {lv} {lv === 'ALL' ? `(${logs.length})` : `(${logs.filter(l => l.level === lv).length})`}
          </button>
        ))}
      </div>
      <div style={styles.logList}>
        {filtered.map((log, i) => (
          <div key={i} style={styles.logEntry}>
            <div style={styles.logHeader}>
              <span style={{ ...styles.logLevel, color: logLevelColor(log.level) }}>{log.level}</span>
              <span style={styles.logModule}>{log.module}</span>
              <span style={styles.logEvent}>{log.event}</span>
              {log.duration_ms && <span style={styles.logDuration}>{log.duration_ms}ms</span>}
              {log.confidence != null && <span style={styles.logConfidence}>conf: {(log.confidence * 100).toFixed(0)}%</span>}
            </div>
            {log.data && Object.keys(log.data).length > 0 && (
              <pre style={styles.logData}>{JSON.stringify(log.data, null, 2)}</pre>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// === Sources Tab ===
function SourcesTab({ knowledge, params }) {
  const sources = knowledge?.sources_used || []
  const conflicts = knowledge?.conflicts || []
  const hypotheses = params?.hypotheses || []
  const rulesApplied = params?.rules_applied || []

  return (
    <div style={styles.tabContent}>
      <Panel title="Data Sources Used">
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {sources.map((s, i) => <Tag key={i} color="#2563eb">{s}</Tag>)}
        </div>
      </Panel>
      {knowledge?.target_profile && (
        <Panel title="Target Profile">
          <KVTable data={{
            'Target': knowledge.target_profile.target,
            'Tumor expression': knowledge.target_profile.tumor_expression_score?.toFixed(2),
            'Accessibility': knowledge.target_profile.accessibility_score?.toFixed(2),
            'Internalization': knowledge.target_profile.internalization_score?.toFixed(2),
            'Evidence level': knowledge.target_profile.evidence_level,
          }} />
          {knowledge.target_profile.normal_tissue_expression && (
            <div style={{ marginTop: '12px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase' }}>Normal Tissue Expression</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {Object.entries(knowledge.target_profile.normal_tissue_expression)
                  .sort((a, b) => b[1] - a[1])
                  .map(([tissue, score]) => (
                    <span key={tissue} style={{ ...styles.exprTag, opacity: 0.3 + score * 0.7 }}>
                      {tissue}: {score.toFixed(2)}
                    </span>
                  ))}
              </div>
            </div>
          )}
        </Panel>
      )}
      {conflicts.length > 0 && (
        <Panel title="Data Conflicts">
          <ul style={{ margin: 0, padding: '0 0 0 16px' }}>
            {conflicts.map((c, i) => <li key={i} style={{ fontSize: '12px', color: '#fbbf24', marginBottom: '4px' }}>{c}</li>)}
          </ul>
        </Panel>
      )}
      {hypotheses.length > 0 && (
        <Panel title="Hypotheses">
          <ul style={{ margin: 0, padding: '0 0 0 16px' }}>
            {hypotheses.map((h, i) => <li key={i} style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>{h}</li>)}
          </ul>
        </Panel>
      )}
      {rulesApplied.length > 0 && (
        <Panel title="Rules Applied">
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {rulesApplied.map((r, i) => <Tag key={i} color="#475569">{r}</Tag>)}
          </div>
        </Panel>
      )}
    </div>
  )
}

// === Shared components ===
function Panel({ title, children }) {
  return (
    <div style={styles.panel}>
      <h3 style={styles.panelTitle}>{title}</h3>
      {children}
    </div>
  )
}

function Tag({ children, color }) {
  return <span style={{ ...styles.tag, background: color }}>{children}</span>
}

function ScoreBadge({ label, value, highlight }) {
  const pct = ((value || 0) * 100).toFixed(0)
  const color = value > 0.7 ? '#34d399' : value > 0.4 ? '#fbbf24' : '#f87171'
  return (
    <div style={styles.scoreBadge}>
      <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: highlight ? '20px' : '16px', fontWeight: 700, color: highlight ? color : '#e2e8f0' }}>{pct}%</div>
    </div>
  )
}

function KVTable({ data }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 16px' }}>
      {Object.entries(data).filter(([, v]) => v != null).map(([k, v]) => (
        <React.Fragment key={k}>
          <span style={{ fontSize: '12px', color: '#64748b' }}>{k}</span>
          <span style={{ fontSize: '12px', color: '#e2e8f0' }}>{String(v)}</span>
        </React.Fragment>
      ))}
    </div>
  )
}

function logLevelColor(level) {
  return { AUDIT: '#818cf8', INFO: '#38bdf8', WARNING: '#fbbf24', ERROR: '#ef4444', DEBUG: '#64748b' }[level] || '#94a3b8'
}

const styles = {
  dashboard: { display: 'flex', flexDirection: 'column', gap: '16px' },
  tabs: { display: 'flex', gap: '4px', background: '#1e293b', borderRadius: '8px', padding: '4px' },
  tab: { padding: '8px 16px', background: 'transparent', border: 'none', borderRadius: '6px', color: '#94a3b8', fontSize: '13px', fontWeight: 500, cursor: 'pointer' },
  tabActive: { background: '#334155', color: '#e2e8f0' },
  tabContent: { display: 'flex', flexDirection: 'column', gap: '16px' },
  warningBanner: { background: '#78350f', border: '1px solid #f59e0b', borderRadius: '8px', padding: '12px', color: '#fde68a', fontSize: '13px' },
  cards: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' },
  card: { background: '#1e293b', borderRadius: '10px', padding: '16px' },
  cardLabel: { fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' },
  cardValue: { fontSize: '26px', fontWeight: 700, color: '#f1f5f9' },
  cardUnit: { fontSize: '13px', color: '#64748b', fontWeight: 400 },
  cardCI: { fontSize: '11px', color: '#64748b', marginTop: '4px' },
  panel: { background: '#1e293b', borderRadius: '12px', padding: '16px' },
  panelTitle: { fontSize: '12px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', margin: '0 0 12px 0' },
  chartContainer: { background: '#1e293b', borderRadius: '12px', padding: '16px', overflow: 'hidden' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '8px 12px', fontSize: '12px', color: '#64748b', borderBottom: '1px solid #334155' },
  td: { padding: '8px 12px', fontSize: '13px', color: '#cbd5e1', borderBottom: '1px solid #1e293b' },
  tag: { display: 'inline-block', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', color: '#e2e8f0', fontWeight: 500 },
  scoreBadge: { textAlign: 'center', padding: '8px 12px', background: '#0f172a', borderRadius: '8px', minWidth: '60px' },
  confBox: { flex: 1, minWidth: '80px' },
  confLabel: { fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '4px' },
  confBar: { height: '6px', borderRadius: '3px', transition: 'width 0.3s' },
  confValue: { fontSize: '11px', color: '#cbd5e1', marginTop: '2px' },
  exprTag: { display: 'inline-block', padding: '2px 6px', background: '#1e293b', border: '1px solid #334155', borderRadius: '4px', fontSize: '10px', color: '#cbd5e1' },
  logList: { maxHeight: '500px', overflowY: 'auto' },
  logEntry: { borderBottom: '1px solid #1e293b', padding: '8px 0' },
  logHeader: { display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' },
  logLevel: { fontSize: '10px', fontWeight: 700, textTransform: 'uppercase' },
  logModule: { fontSize: '11px', color: '#94a3b8' },
  logEvent: { fontSize: '11px', color: '#cbd5e1', fontWeight: 500 },
  logDuration: { fontSize: '10px', color: '#64748b' },
  logConfidence: { fontSize: '10px', color: '#fbbf24' },
  logData: { fontSize: '10px', color: '#64748b', margin: '4px 0 0 0', padding: '8px', background: '#0f172a', borderRadius: '4px', overflow: 'auto', maxHeight: '150px', whiteSpace: 'pre-wrap' },
  filterBtn: { padding: '4px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#94a3b8', fontSize: '11px', cursor: 'pointer' },
}
