import React, { useState } from 'react'

const TARGETS = ['PSMA', 'SSTR2', 'HER2', 'FAP', 'CD20']
const AGENT_CLASSES = ['small_molecule', 'peptide', 'nanobody', 'Fab', 'IgG']
const ISOTOPES = ['Ga-68', 'F-18', 'Lu-177', 'Y-90', 'Ac-225', 'Zr-89', 'I-131']
const TUMOR_TYPES = [
  'prostate', 'breast', 'neuroendocrine', 'lymphoma',
  'colorectal', 'lung', 'gastric', 'pancreatic', 'other',
]

const PRESETS = {
  'PSMA-617 (Lu-177)': {
    target: 'PSMA', agent: { name: 'PSMA-617', class: 'small_molecule', size_kDa: 1.0, kd_nM: 2.3, isotope: 'Lu-177', internalization: true },
    dose: { activity_GBq: 7.4 }, tumor: { type: 'prostate', volume_ml: 50 },
  },
  'DOTATATE (Ga-68)': {
    target: 'SSTR2', agent: { name: 'DOTATATE-68Ga', class: 'peptide', size_kDa: 1.5, kd_nM: 2.0, isotope: 'Ga-68', internalization: true },
    dose: { activity_MBq: 185 }, tumor: { type: 'neuroendocrine', volume_ml: 30 },
  },
  'DOTATATE (Lu-177)': {
    target: 'SSTR2', agent: { name: 'DOTATATE', class: 'peptide', size_kDa: 1.4, kd_nM: 1.5, isotope: 'Lu-177', internalization: true },
    dose: { activity_GBq: 7.4 }, tumor: { type: 'neuroendocrine', volume_ml: 30 },
  },
  'Trastuzumab (Zr-89)': {
    target: 'HER2', agent: { name: 'Trastuzumab-89Zr', class: 'IgG', size_kDa: 150.0, kd_nM: 0.5, isotope: 'Zr-89', internalization: true, has_fc_region: true },
    dose: { activity_MBq: 37 }, tumor: { type: 'breast', volume_ml: 50 },
  },
  'FAPI-46 (Ga-68)': {
    target: 'FAP', agent: { name: 'FAPI-46', class: 'small_molecule', size_kDa: 0.9, kd_nM: 6.5, isotope: 'Ga-68', internalization: true },
    dose: { activity_MBq: 200 }, tumor: { type: 'pancreatic', volume_ml: 40 },
  },
  'Rituximab (no isotope)': {
    target: 'CD20', agent: { name: 'Rituximab', class: 'IgG', size_kDa: 145.0, kd_nM: 8.0, has_fc_region: true },
    dose: { mass_mg: 500 }, tumor: { type: 'lymphoma', volume_ml: 100 },
  },
}

export default function V1SimulationForm({ onSubmit, loading }) {
  const [target, setTarget] = useState('PSMA')
  const [agentName, setAgentName] = useState('PSMA-617')
  const [agentClass, setAgentClass] = useState('small_molecule')
  const [sizeKDa, setSizeKDa] = useState(1.0)
  const [kdNM, setKdNM] = useState(2.3)
  const [isotope, setIsotope] = useState('Lu-177')
  const [internalization, setInternalization] = useState(true)
  const [doseGBq, setDoseGBq] = useState(7.4)
  const [tumorType, setTumorType] = useState('prostate')
  const [tumorVolume, setTumorVolume] = useState(50)
  const [patientWeight, setPatientWeight] = useState(70)
  const [patientAge, setPatientAge] = useState(65)
  const [patientSex, setPatientSex] = useState('male')
  const [renalFunction, setRenalFunction] = useState('normal')
  const [nMC, setNMC] = useState(100)
  const [duration, setDuration] = useState(168)

  const applyPreset = (presetName) => {
    const p = PRESETS[presetName]
    if (!p) return
    setTarget(p.target)
    setAgentName(p.agent.name)
    setAgentClass(p.agent.class)
    setSizeKDa(p.agent.size_kDa)
    setKdNM(p.agent.kd_nM || '')
    setIsotope(p.agent.isotope || '')
    setInternalization(p.agent.internalization !== false)
    setDoseGBq(p.dose.activity_GBq || (p.dose.activity_MBq ? p.dose.activity_MBq / 1000 : ''))
    setTumorType(p.tumor.type)
    setTumorVolume(p.tumor.volume_ml)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const payload = {
      target,
      agent: {
        name: agentName,
        class: agentClass,
        size_kDa: Number(sizeKDa),
        kd_nM: kdNM ? Number(kdNM) : undefined,
        isotope: isotope || undefined,
        internalization,
      },
      dose: doseGBq ? { activity_GBq: Number(doseGBq) } : {},
      tumor: { type: tumorType, volume_ml: Number(tumorVolume) },
      patient: {
        weight_kg: Number(patientWeight),
        age: Number(patientAge),
        sex: patientSex,
        renal_function: renalFunction,
      },
      n_monte_carlo: Number(nMC),
      duration_hours: Number(duration),
    }
    onSubmit(payload)
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      {/* Presets */}
      <Section title="Quick Presets">
        <div style={styles.presetGrid}>
          {Object.keys(PRESETS).map(name => (
            <button key={name} type="button" onClick={() => applyPreset(name)}
              style={styles.presetBtn}>{name}</button>
          ))}
        </div>
      </Section>

      <Section title="Target & Agent">
        <Field label="Target">
          <select value={target} onChange={e => setTarget(e.target.value)} style={styles.select}>
            {TARGETS.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>
        <Field label="Agent Name">
          <input type="text" value={agentName} onChange={e => setAgentName(e.target.value)} style={styles.input} />
        </Field>
        <div style={styles.row}>
          <Field label="Agent Class" half>
            <select value={agentClass} onChange={e => setAgentClass(e.target.value)} style={styles.select}>
              {AGENT_CLASSES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Size (kDa)" half>
            <input type="number" step="0.1" value={sizeKDa} onChange={e => setSizeKDa(e.target.value)} style={styles.input} />
          </Field>
        </div>
        <div style={styles.row}>
          <Field label="Kd (nM)" half>
            <input type="number" step="0.1" value={kdNM} onChange={e => setKdNM(e.target.value)} style={styles.input} placeholder="optional" />
          </Field>
          <Field label="Isotope" half>
            <select value={isotope} onChange={e => setIsotope(e.target.value)} style={styles.select}>
              <option value="">None</option>
              {ISOTOPES.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
          </Field>
        </div>
        <Field label={`Dose: ${doseGBq} GBq`}>
          <input type="range" min="0.05" max="15" step="0.05" value={doseGBq}
            onChange={e => setDoseGBq(e.target.value)} style={styles.range} />
        </Field>
      </Section>

      <Section title="Tumor">
        <Field label="Type">
          <select value={tumorType} onChange={e => setTumorType(e.target.value)} style={styles.select}>
            {TUMOR_TYPES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
          </select>
        </Field>
        <Field label={`Volume: ${tumorVolume} mL`}>
          <input type="range" min="1" max="500" step="1" value={tumorVolume}
            onChange={e => setTumorVolume(e.target.value)} style={styles.range} />
        </Field>
      </Section>

      <Section title="Patient">
        <div style={styles.row}>
          <Field label="Age" half>
            <input type="number" min="18" max="100" value={patientAge}
              onChange={e => setPatientAge(e.target.value)} style={styles.input} />
          </Field>
          <Field label="Sex" half>
            <select value={patientSex} onChange={e => setPatientSex(e.target.value)} style={styles.select}>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </Field>
        </div>
        <Field label={`Weight: ${patientWeight} kg`}>
          <input type="range" min="30" max="150" value={patientWeight}
            onChange={e => setPatientWeight(e.target.value)} style={styles.range} />
        </Field>
        <Field label="Renal Function">
          <select value={renalFunction} onChange={e => setRenalFunction(e.target.value)} style={styles.select}>
            <option value="normal">Normal</option>
            <option value="mild_impairment">Mild Impairment</option>
            <option value="moderate_impairment">Moderate Impairment</option>
            <option value="severe_impairment">Severe Impairment</option>
          </select>
        </Field>
      </Section>

      <Section title="Simulation">
        <Field label={`MC Samples: ${nMC}`}>
          <input type="range" min="10" max="500" step="10" value={nMC}
            onChange={e => setNMC(e.target.value)} style={styles.range} />
        </Field>
        <Field label={`Duration: ${duration}h (${Math.round(duration/24)}d)`}>
          <input type="range" min="1" max="336" value={duration}
            onChange={e => setDuration(e.target.value)} style={styles.range} />
        </Field>
      </Section>

      <button type="submit" disabled={loading} style={{ ...styles.button, opacity: loading ? 0.6 : 1 }}>
        {loading ? 'Running V1 Pipeline...' : 'Run V1 Simulation'}
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
  form: { display: 'flex', flexDirection: 'column', gap: '8px' },
  section: { background: '#0f172a', borderRadius: '8px', padding: '16px', marginBottom: '8px' },
  sectionTitle: { fontSize: '13px', fontWeight: 600, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' },
  field: { marginBottom: '10px' },
  label: { display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' },
  input: { width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#e2e8f0', fontSize: '14px', outline: 'none', boxSizing: 'border-box' },
  select: { width: '100%', padding: '8px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#e2e8f0', fontSize: '14px', outline: 'none', boxSizing: 'border-box' },
  range: { width: '100%', accentColor: '#38bdf8' },
  row: { display: 'flex', gap: '12px' },
  button: { width: '100%', padding: '14px', background: 'linear-gradient(135deg, #2563eb, #7c3aed)', border: 'none', borderRadius: '8px', color: 'white', fontSize: '16px', fontWeight: 600, cursor: 'pointer', marginTop: '8px' },
  presetGrid: { display: 'flex', flexWrap: 'wrap', gap: '6px' },
  presetBtn: { padding: '6px 10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#94a3b8', fontSize: '11px', cursor: 'pointer' },
}
