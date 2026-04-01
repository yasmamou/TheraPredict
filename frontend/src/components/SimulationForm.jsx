import React, { useState } from 'react'

const PRESET_AGENTS = [
  { key: 'trastuzumab-89Zr', label: 'Trastuzumab-89Zr (IgG, HER2, PET)' },
  { key: 'her2-nanobody-68Ga', label: 'HER2 Nanobody-68Ga (PET)' },
  { key: 'her2-fab', label: 'HER2 Fab Fragment' },
  { key: 'pertuzumab', label: 'Pertuzumab (IgG, HER2)' },
  { key: 'PSMA-617', label: 'PSMA-617 (177Lu, Therapy)' },
  { key: 'PSMA-617-68Ga', label: 'PSMA-617-68Ga (PET)' },
  { key: 'DOTATATE', label: 'DOTATATE (177Lu, PRRT)' },
  { key: 'DOTATATE-68Ga', label: 'DOTATATE-68Ga (PET)' },
  { key: 'rituximab', label: 'Rituximab (IgG, CD20)' },
]

const TUMOR_TYPES = [
  'breast', 'prostate', 'neuroendocrine', 'lymphoma',
  'colorectal', 'lung', 'gastric', 'melanoma', 'other',
]

export default function SimulationForm({ onSubmit, loading }) {
  const [params, setParams] = useState({
    agent_key: 'trastuzumab-89Zr',
    tumor_type: 'breast',
    dose_mbq: 37,
    patient_age: 60,
    patient_sex: 'female',
    patient_weight_kg: 70,
    patient_height_cm: 165,
    patient_egfr: 90,
    patient_liver_function: 1.0,
    tumor_volume_ml: 50,
    tumor_target_density: 100,
    n_metastases: 3,
    duration_hours: 168,
    n_monte_carlo: 100,
    time_step_hours: 1.0,
  })

  const update = (key, value) => {
    setParams(prev => ({ ...prev, [key]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit(params)
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <Section title="Target & Agent">
        <Field label="Agent">
          <select
            value={params.agent_key}
            onChange={e => update('agent_key', e.target.value)}
            style={styles.select}
          >
            {PRESET_AGENTS.map(a => (
              <option key={a.key} value={a.key}>{a.label}</option>
            ))}
          </select>
        </Field>

        <Field label="Tumor Type">
          <select
            value={params.tumor_type}
            onChange={e => update('tumor_type', e.target.value)}
            style={styles.select}
          >
            {TUMOR_TYPES.map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </Field>

        <Field label={`Dose: ${params.dose_mbq} MBq`}>
          <input
            type="range" min="1" max="10000" step="1"
            value={params.dose_mbq}
            onChange={e => update('dose_mbq', Number(e.target.value))}
            style={styles.range}
          />
        </Field>
      </Section>

      <Section title="Patient">
        <div style={styles.row}>
          <Field label="Age" half>
            <input
              type="number" min="18" max="100"
              value={params.patient_age}
              onChange={e => update('patient_age', Number(e.target.value))}
              style={styles.input}
            />
          </Field>
          <Field label="Sex" half>
            <select
              value={params.patient_sex}
              onChange={e => update('patient_sex', e.target.value)}
              style={styles.select}
            >
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </Field>
        </div>

        <div style={styles.row}>
          <Field label="Weight (kg)" half>
            <input
              type="number" min="30" max="200" step="0.5"
              value={params.patient_weight_kg}
              onChange={e => update('patient_weight_kg', Number(e.target.value))}
              style={styles.input}
            />
          </Field>
          <Field label="Height (cm)" half>
            <input
              type="number" min="120" max="220"
              value={params.patient_height_cm}
              onChange={e => update('patient_height_cm', Number(e.target.value))}
              style={styles.input}
            />
          </Field>
        </div>

        <Field label={`eGFR: ${params.patient_egfr} mL/min`}>
          <input
            type="range" min="5" max="150"
            value={params.patient_egfr}
            onChange={e => update('patient_egfr', Number(e.target.value))}
            style={styles.range}
          />
        </Field>
      </Section>

      <Section title="Tumor">
        <Field label={`Volume: ${params.tumor_volume_ml} mL`}>
          <input
            type="range" min="0.1" max="500" step="0.1"
            value={params.tumor_volume_ml}
            onChange={e => update('tumor_volume_ml', Number(e.target.value))}
            style={styles.range}
          />
        </Field>

        <Field label={`Target Density: ${params.tumor_target_density} nM`}>
          <input
            type="range" min="0" max="500" step="1"
            value={params.tumor_target_density}
            onChange={e => update('tumor_target_density', Number(e.target.value))}
            style={styles.range}
          />
        </Field>

        <Field label="Metastases">
          <input
            type="number" min="0" max="100"
            value={params.n_metastases}
            onChange={e => update('n_metastases', Number(e.target.value))}
            style={styles.input}
          />
        </Field>
      </Section>

      <Section title="Simulation">
        <Field label={`Duration: ${params.duration_hours}h (${(params.duration_hours/24).toFixed(0)}d)`}>
          <input
            type="range" min="1" max="336" step="1"
            value={params.duration_hours}
            onChange={e => update('duration_hours', Number(e.target.value))}
            style={styles.range}
          />
        </Field>

        <Field label={`Monte Carlo: ${params.n_monte_carlo} samples`}>
          <input
            type="range" min="10" max="500" step="10"
            value={params.n_monte_carlo}
            onChange={e => update('n_monte_carlo', Number(e.target.value))}
            style={styles.range}
          />
        </Field>
      </Section>

      <button type="submit" disabled={loading} style={{
        ...styles.button,
        opacity: loading ? 0.6 : 1,
      }}>
        {loading ? 'Running...' : 'Run Simulation'}
      </button>
    </form>
  )
}

function Section({ title, children }) {
  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>{title}</h3>
      {children}
    </div>
  )
}

function Field({ label, children, half }) {
  return (
    <div style={{ ...styles.field, width: half ? '48%' : '100%' }}>
      <label style={styles.label}>{label}</label>
      {children}
    </div>
  )
}

const styles = {
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  section: {
    background: '#0f172a',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '8px',
  },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#38bdf8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '12px',
  },
  field: {
    marginBottom: '10px',
  },
  label: {
    display: 'block',
    fontSize: '12px',
    color: '#94a3b8',
    marginBottom: '4px',
  },
  input: {
    width: '100%',
    padding: '8px 10px',
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#e2e8f0',
    fontSize: '14px',
    outline: 'none',
  },
  select: {
    width: '100%',
    padding: '8px 10px',
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#e2e8f0',
    fontSize: '14px',
    outline: 'none',
  },
  range: {
    width: '100%',
    accentColor: '#38bdf8',
  },
  row: {
    display: 'flex',
    gap: '12px',
  },
  button: {
    width: '100%',
    padding: '14px',
    background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: '8px',
  },
}
