import React, { useMemo } from 'react'
import Plot from 'react-plotly.js'

export default function ResultsDashboard({ result }) {
  if (!result) return null

  return (
    <div style={styles.dashboard}>
      <MetricsCards result={result} />
      <TimeActivityChart result={result} />
      <BiodistributionBar result={result} />
      {result.dosimetry && <DosimetryTable dosimetry={result.dosimetry} />}
      <ConfidencePanel confidence={result.confidence} />
    </div>
  )
}

function MetricsCards({ result }) {
  const metrics = [
    {
      label: 'Tumor Uptake',
      value: result.tumor_uptake_percent_id_per_g?.value?.toFixed(2) || '—',
      unit: 'nM',
      ci: result.tumor_uptake_percent_id_per_g
        ? `[${result.tumor_uptake_percent_id_per_g.ci_low?.toFixed(2)} - ${result.tumor_uptake_percent_id_per_g.ci_high?.toFixed(2)}]`
        : '',
      color: '#38bdf8',
    },
    {
      label: 'Tumor-to-Background',
      value: result.tumor_to_background_ratio?.value?.toFixed(1) || '—',
      unit: 'ratio',
      ci: result.tumor_to_background_ratio
        ? `[${result.tumor_to_background_ratio.ci_low?.toFixed(1)} - ${result.tumor_to_background_ratio.ci_high?.toFixed(1)}]`
        : '',
      color: '#a78bfa',
    },
    {
      label: 'Optimal Imaging',
      value: result.optimal_imaging_time_hours?.value?.toFixed(0) || '—',
      unit: 'hours',
      ci: result.optimal_imaging_time_hours
        ? `[${result.optimal_imaging_time_hours.ci_low?.toFixed(0)} - ${result.optimal_imaging_time_hours.ci_high?.toFixed(0)}]`
        : '',
      color: '#34d399',
    },
    {
      label: 'Plasma Half-Life',
      value: result.plasma_half_life_hours?.toFixed(1) || '—',
      unit: 'hours',
      ci: '',
      color: '#fb923c',
    },
  ]

  return (
    <div style={styles.cards}>
      {metrics.map((m, i) => (
        <div key={i} style={styles.card}>
          <div style={{ ...styles.cardLabel, color: m.color }}>{m.label}</div>
          <div style={styles.cardValue}>
            {m.value} <span style={styles.cardUnit}>{m.unit}</span>
          </div>
          {m.ci && <div style={styles.cardCI}>90% CI: {m.ci}</div>}
        </div>
      ))}
    </div>
  )
}

function TimeActivityChart({ result }) {
  const organResults = result.organ_results || []

  const keyOrgans = ['plasma', 'liver', 'kidneys', 'spleen', 'tumor', 'muscle', 'lungs']
  const colors = {
    plasma: '#ef4444',
    liver: '#f59e0b',
    kidneys: '#10b981',
    spleen: '#8b5cf6',
    tumor: '#ec4899',
    muscle: '#6b7280',
    lungs: '#06b6d4',
  }

  const traces = keyOrgans
    .map(name => {
      const organ = organResults.find(o => o.organ_name === name)
      if (!organ) return null
      // Subsample for performance
      const step = Math.max(1, Math.floor(organ.times_hours.length / 200))
      const times = organ.times_hours.filter((_, i) => i % step === 0)
      const concs = organ.concentrations_total.filter((_, i) => i % step === 0)
      return {
        x: times,
        y: concs,
        name: name === 'tumor' ? 'TUMOR' : name.charAt(0).toUpperCase() + name.slice(1),
        type: 'scatter',
        mode: 'lines',
        line: {
          color: colors[name] || '#94a3b8',
          width: name === 'tumor' ? 3 : 1.5,
          dash: name === 'tumor' ? 'solid' : undefined,
        },
      }
    })
    .filter(Boolean)

  return (
    <div style={styles.chartContainer}>
      <Plot
        data={traces}
        layout={{
          title: { text: 'Time-Activity Curves', font: { color: '#e2e8f0', size: 14 } },
          paper_bgcolor: '#1e293b',
          plot_bgcolor: '#0f172a',
          xaxis: {
            title: 'Time (hours)',
            color: '#94a3b8',
            gridcolor: '#1e293b',
          },
          yaxis: {
            title: 'Concentration (nM)',
            color: '#94a3b8',
            gridcolor: '#1e293b',
            type: 'log',
          },
          legend: { font: { color: '#94a3b8' }, bgcolor: 'transparent' },
          margin: { l: 60, r: 20, t: 40, b: 50 },
          height: 350,
        }}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%' }}
      />
    </div>
  )
}

function BiodistributionBar({ result }) {
  const biodist = result.biodistribution_at_optimal || {}
  const entries = Object.entries(biodist)
    .filter(([k, v]) => v > 0 && k !== 'rest_of_body')
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)

  const names = entries.map(([k]) => k === 'tumor' ? 'TUMOR' : k.charAt(0).toUpperCase() + k.slice(1).replace('_', ' '))
  const values = entries.map(([, v]) => v)
  const colors = entries.map(([k]) => k === 'tumor' ? '#ec4899' : '#38bdf8')

  return (
    <div style={styles.chartContainer}>
      <Plot
        data={[{
          x: names,
          y: values,
          type: 'bar',
          marker: { color: colors, opacity: 0.85 },
        }]}
        layout={{
          title: { text: 'Biodistribution at Optimal Time', font: { color: '#e2e8f0', size: 14 } },
          paper_bgcolor: '#1e293b',
          plot_bgcolor: '#0f172a',
          xaxis: { color: '#94a3b8', tickangle: -45 },
          yaxis: { title: '%ID/g', color: '#94a3b8', gridcolor: '#1e293b' },
          margin: { l: 60, r: 20, t: 40, b: 80 },
          height: 300,
        }}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%' }}
      />
    </div>
  )
}

function DosimetryTable({ dosimetry }) {
  const organs = Object.entries(dosimetry.organ_doses_gy_per_gbq || {})
    .filter(([k]) => k !== 'plasma')
    .sort((a, b) => b[1] - a[1])

  return (
    <div style={styles.tableContainer}>
      <h3 style={styles.sectionTitle}>Dosimetry (Gy/GBq)</h3>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Organ</th>
            <th style={styles.th}>Dose (Gy/GBq)</th>
            <th style={styles.th}>Status</th>
          </tr>
        </thead>
        <tbody>
          {organs.map(([organ, dose]) => (
            <tr key={organ}>
              <td style={styles.td}>
                {organ === dosimetry.dose_limiting_organ
                  ? `${organ} (DLO)`
                  : organ}
              </td>
              <td style={styles.td}>{dose.toFixed(4)}</td>
              <td style={styles.td}>
                {organ === dosimetry.dose_limiting_organ
                  ? <span style={{ color: '#fbbf24' }}>Dose-limiting</span>
                  : <span style={{ color: '#34d399' }}>OK</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={styles.dosimetryMeta}>
        <span>Tumor dose: <b>{dosimetry.tumor_dose_gy_per_gbq?.toFixed(4)}</b> Gy/GBq</span>
        {dosimetry.therapeutic_index && (
          <span> | Therapeutic index: <b>{dosimetry.therapeutic_index}</b></span>
        )}
        {dosimetry.tumor_to_kidney_ratio && (
          <span> | Tumor/Kidney: <b>{dosimetry.tumor_to_kidney_ratio}</b></span>
        )}
      </div>
    </div>
  )
}

function ConfidencePanel({ confidence }) {
  if (!confidence) return null

  const levelColors = {
    high: '#34d399',
    moderate: '#fbbf24',
    low: '#fb923c',
    very_low: '#ef4444',
  }

  return (
    <div style={styles.confidencePanel}>
      <h3 style={styles.sectionTitle}>Confidence Assessment</h3>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        <span style={{
          padding: '4px 12px',
          borderRadius: '12px',
          background: levelColors[confidence.level] || '#6b7280',
          color: '#0f172a',
          fontWeight: 600,
          fontSize: '13px',
        }}>
          {confidence.level?.toUpperCase()}
        </span>
        <span style={{ color: '#94a3b8', fontSize: '13px' }}>
          Data support: {confidence.data_support}
        </span>
      </div>
      <ul style={styles.factorList}>
        {(confidence.factors || []).map((f, i) => (
          <li key={i} style={styles.factor}>{f}</li>
        ))}
      </ul>
      <p style={styles.recommendation}>{confidence.recommendation}</p>
    </div>
  )
}

const styles = {
  dashboard: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  cards: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '12px',
  },
  card: {
    background: '#1e293b',
    borderRadius: '10px',
    padding: '16px',
  },
  cardLabel: {
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '4px',
  },
  cardValue: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#f1f5f9',
  },
  cardUnit: {
    fontSize: '14px',
    color: '#64748b',
    fontWeight: 400,
  },
  cardCI: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '4px',
  },
  chartContainer: {
    background: '#1e293b',
    borderRadius: '12px',
    padding: '16px',
    overflow: 'hidden',
  },
  tableContainer: {
    background: '#1e293b',
    borderRadius: '12px',
    padding: '16px',
  },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '12px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    textAlign: 'left',
    padding: '8px 12px',
    fontSize: '12px',
    color: '#64748b',
    borderBottom: '1px solid #334155',
  },
  td: {
    padding: '8px 12px',
    fontSize: '13px',
    color: '#cbd5e1',
    borderBottom: '1px solid #1e293b',
  },
  dosimetryMeta: {
    marginTop: '12px',
    fontSize: '12px',
    color: '#94a3b8',
  },
  confidencePanel: {
    background: '#1e293b',
    borderRadius: '12px',
    padding: '16px',
  },
  factorList: {
    listStyle: 'none',
    padding: 0,
  },
  factor: {
    fontSize: '13px',
    color: '#cbd5e1',
    padding: '4px 0',
    paddingLeft: '12px',
    borderLeft: '2px solid #334155',
    marginBottom: '4px',
  },
  recommendation: {
    marginTop: '12px',
    fontSize: '12px',
    color: '#94a3b8',
    fontStyle: 'italic',
    lineHeight: '1.5',
  },
}
