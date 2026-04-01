import React, { useMemo } from 'react'

const ORGAN_POSITIONS = {
  brain: { x: 200, y: 30, w: 50, h: 35, label: 'Brain' },
  salivary_glands: { x: 155, y: 55, w: 40, h: 20, label: 'Salivary' },
  lungs: { x: 175, y: 100, w: 100, h: 55, label: 'Lungs' },
  heart: { x: 230, y: 115, w: 30, h: 30, label: 'Heart' },
  liver: { x: 155, y: 170, w: 70, h: 45, label: 'Liver' },
  spleen: { x: 250, y: 175, w: 35, h: 30, label: 'Spleen' },
  kidney: { x: 200, y: 210, w: 50, h: 30, label: 'Kidney' },
  gut: { x: 190, y: 255, w: 60, h: 40, label: 'Gut' },
  bone_marrow: { x: 120, y: 200, w: 30, h: 70, label: 'Marrow' },
  bone: { x: 95, y: 280, w: 25, h: 50, label: 'Bone' },
  muscle: { x: 290, y: 200, w: 30, h: 80, label: 'Muscle' },
  tumor: { x: 260, y: 140, w: 30, h: 30, label: 'TUMOR' },
  skin: { x: 110, y: 100, w: 25, h: 80, label: 'Skin' },
  plasma: { x: 200, y: 320, w: 50, h: 25, label: 'Blood' },
}

function getColor(value, maxVal) {
  if (!value || value <= 0) return '#1e293b'
  const ratio = Math.min(value / Math.max(maxVal, 1e-6), 1.0)
  if (ratio < 0.2) return `rgba(56, 189, 248, ${0.2 + ratio * 2})`
  if (ratio < 0.5) return `rgba(250, 204, 21, ${0.3 + ratio})`
  return `rgba(239, 68, 68, ${0.5 + ratio * 0.5})`
}

export default function BodyDiagram({ result }) {
  const biodist = result?.biodistribution_at_optimal || {}

  const maxVal = useMemo(() => {
    const vals = Object.values(biodist).filter(v => v > 0)
    return vals.length > 0 ? Math.max(...vals) : 1
  }, [biodist])

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Biodistribution Map (at optimal imaging time)</h3>
      <svg viewBox="0 0 420 380" style={styles.svg}>
        {/* Body outline */}
        <ellipse cx="210" cy="35" rx="35" ry="30" fill="none" stroke="#334155" strokeWidth="1.5" />
        <path d="M175 65 Q130 80 110 150 L105 300 Q105 340 140 340 L170 340 L170 280 L250 280 L250 340 L280 340 Q315 340 315 300 L310 150 Q290 80 245 65 Z"
              fill="none" stroke="#334155" strokeWidth="1.5" />

        {/* Organs */}
        {Object.entries(ORGAN_POSITIONS).map(([name, pos]) => {
          const value = biodist[name] || 0
          const color = getColor(value, maxVal)
          const isTumor = name === 'tumor'

          return (
            <g key={name}>
              <rect
                x={pos.x} y={pos.y}
                width={pos.w} height={pos.h}
                rx="4" ry="4"
                fill={color}
                stroke={isTumor ? '#ef4444' : '#475569'}
                strokeWidth={isTumor ? 2 : 1}
                strokeDasharray={isTumor ? '4,2' : 'none'}
              />
              <text
                x={pos.x + pos.w / 2}
                y={pos.y + pos.h / 2 - 4}
                textAnchor="middle"
                fill={isTumor ? '#fca5a5' : '#cbd5e1'}
                fontSize="9"
                fontWeight={isTumor ? 700 : 400}
              >
                {pos.label}
              </text>
              <text
                x={pos.x + pos.w / 2}
                y={pos.y + pos.h / 2 + 8}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize="8"
              >
                {value > 0 ? value.toExponential(1) : '—'}
              </text>
            </g>
          )
        })}

        {/* Legend */}
        <text x="350" y="20" fill="#94a3b8" fontSize="9">Uptake</text>
        <rect x="350" y="28" width="40" height="8" rx="2"
              fill="linear-gradient(90deg, #1e293b, #38bdf8, #facc15, #ef4444)" />
        <defs>
          <linearGradient id="legend-grad" x1="0" x2="1">
            <stop offset="0%" stopColor="#1e293b" />
            <stop offset="33%" stopColor="#38bdf8" />
            <stop offset="66%" stopColor="#facc15" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>
        <rect x="350" y="28" width="40" height="8" rx="2" fill="url(#legend-grad)" />
        <text x="350" y="46" fill="#64748b" fontSize="7">Low</text>
        <text x="381" y="46" fill="#64748b" fontSize="7">High</text>
      </svg>
    </div>
  )
}

const styles = {
  container: {
    background: '#1e293b',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '20px',
  },
  title: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#94a3b8',
    marginBottom: '12px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  svg: {
    width: '100%',
    maxWidth: '500px',
    margin: '0 auto',
    display: 'block',
  },
}
