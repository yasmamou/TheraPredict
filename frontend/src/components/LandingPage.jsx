import React, { useEffect, useRef, useState, useCallback } from 'react'

// ─── Scroll-reveal hook ────────────────────────────────────────────────
function useReveal(threshold = 0.15) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect() } },
      { threshold }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return [ref, visible]
}

function Reveal({ children, delay = 0, y = 40, style = {} }) {
  const [ref, visible] = useReveal()
  return (
    <div ref={ref} style={{
      ...style,
      opacity: visible ? 1 : 0,
      transform: visible ? 'translateY(0)' : `translateY(${y}px)`,
      transition: `opacity 0.8s cubic-bezier(0.16,1,0.3,1) ${delay}s, transform 0.8s cubic-bezier(0.16,1,0.3,1) ${delay}s`,
    }}>
      {children}
    </div>
  )
}

// ─── Subtle animated gradient orb (background decoration) ──────────────
function GradientOrb({ color1, color2, size, top, left, right, delay = '0s' }) {
  return (
    <div style={{
      position: 'absolute', top, left, right,
      width: size, height: size, borderRadius: '50%',
      background: `radial-gradient(circle, ${color1} 0%, ${color2} 40%, transparent 70%)`,
      opacity: 0.07, filter: 'blur(60px)', pointerEvents: 'none',
      animation: `float ${8 + Math.random() * 4}s ease-in-out infinite`,
      animationDelay: delay,
    }} />
  )
}

// ─── Main Landing Page ─────────────────────────────────────────────────
export default function LandingPage({ onEnter }) {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', h, { passive: true })
    return () => window.removeEventListener('scroll', h)
  }, [])

  return (
    <div style={{ background: '#fafafa', color: '#0a0a0a', overflowX: 'hidden' }}>

      {/* ── NAV ── */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        background: scrolled ? 'rgba(250,250,250,0.85)' : 'transparent',
        backdropFilter: scrolled ? 'blur(24px) saturate(180%)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(24px) saturate(180%)' : 'none',
        borderBottom: scrolled ? '1px solid rgba(0,0,0,0.06)' : '1px solid transparent',
        transition: 'all 0.4s ease',
      }}>
        <div style={S.navInner}>
          <span style={S.logo}>TheraPredict</span>
          <div style={S.navLinks}>
            <a href="#about" style={S.navLink}>About</a>
            <a href="#pipeline" style={S.navLink}>Pipeline</a>
            <a href="#targets" style={S.navLink}>Targets</a>
            <a href="#science" style={S.navLink}>Science</a>
            <button onClick={onEnter} style={S.navCta}>Launch Platform</button>
          </div>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={S.hero}>
        {/* Subtle orbs */}
        <GradientOrb color1="#059669" color2="#06b6d4" size="600px" top="-200px" right="-100px" />
        <GradientOrb color1="#0284c7" color2="#7c3aed" size="500px" top="200px" left="-150px" delay="2s" />

        <div style={S.heroInner}>
          <Reveal>
            <p style={S.heroLabel}>Mechanistic Theranostic Simulation</p>
          </Reveal>
          <Reveal delay={0.1}>
            <h1 style={S.heroH1}>
              Predicting where<br />medicine meets<br />the molecule.
            </h1>
          </Reveal>
          <Reveal delay={0.2}>
            <p style={S.heroP}>
              TheraPredict simulates the full journey of theranostic agents through
              the human body — from injection to tumor uptake, organ dosimetry, and
              biological effect — with complete traceability at every step.
            </p>
          </Reveal>
          <Reveal delay={0.3}>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <button onClick={onEnter} style={S.btnPrimary}>
                Launch Platform <span style={{ marginLeft: '8px' }}>&rarr;</span>
              </button>
              <a href="#about" style={S.btnSecondary}>Learn more</a>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── MARQUEE STATS ── */}
      <section style={S.statsBar}>
        <div style={S.statsInner}>
          {[
            ['15', 'Body compartments'],
            ['7', 'Radioisotopes'],
            ['5', 'Molecular targets'],
            ['7', 'Pipeline modules'],
            ['128', 'Validated tests'],
          ].map(([val, label], i) => (
            <div key={i} style={S.statItem}>
              <span style={S.statVal}>{val}</span>
              <span style={S.statLabel}>{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── ABOUT ── */}
      <section id="about" style={S.section}>
        <div style={S.container}>
          <div style={S.twoCol}>
            <div style={S.colText}>
              <Reveal>
                <p style={S.eyebrow}>The Platform</p>
              </Reveal>
              <Reveal delay={0.05}>
                <h2 style={S.h2}>
                  From molecular target<br />to clinical insight.
                </h2>
              </Reveal>
              <Reveal delay={0.1}>
                <p style={S.body}>
                  TheraPredict bridges nuclear medicine and computational biology.
                  Input a target, an agent, and a patient profile — get a complete
                  simulation with biodistribution, radiation dosimetry, biological
                  effects, and actionable recommendations.
                </p>
              </Reveal>
              <Reveal delay={0.15}>
                <p style={S.body}>
                  Every prediction is mechanistic, not a black box. Every parameter
                  is traceable. Every hypothesis is stated. Every confidence interval
                  is computed. The full audit trail is available for every simulation.
                </p>
              </Reveal>
            </div>
            <div style={S.colCards}>
              {[
                { title: 'Mechanistic PBPK', text: '15-compartment physiologically-based model with ODE solver and Monte Carlo uncertainty quantification.' },
                { title: 'Radiation dosimetry', text: 'MIRD/OLINDA-based internal dosimetry for Lu-177, Y-90, Ac-225, I-131. Organ doses, therapeutic index.' },
                { title: 'Biological effects', text: 'Target occupancy, causal pharmacodynamic rules, dose-effect relationships. Directional, never speculative.' },
                { title: 'Decision support', text: 'Transparent weighted scoring: efficacy, safety, practicality, confidence. Every sub-score visible.' },
              ].map((c, i) => (
                <Reveal key={i} delay={0.05 * i}>
                  <div style={S.miniCard}>
                    <h4 style={S.miniCardTitle}>{c.title}</h4>
                    <p style={S.miniCardText}>{c.text}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── DIVIDER QUOTE ── */}
      <section style={S.quoteSection}>
        <div style={S.container}>
          <Reveal>
            <blockquote style={S.quote}>
              "The goal of theranostics is simple: see what you treat, treat what you
              see. The challenge is predicting it before the patient is in the scanner."
            </blockquote>
          </Reveal>
        </div>
      </section>

      {/* ── PIPELINE ── */}
      <section id="pipeline" style={{ ...S.section, background: '#fff' }}>
        <div style={S.container}>
          <Reveal><p style={S.eyebrow}>The Pipeline</p></Reveal>
          <Reveal delay={0.05}>
            <h2 style={S.h2}>Seven modules.<br />Complete traceability.</h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p style={{ ...S.body, maxWidth: '540px', marginBottom: '56px' }}>
              Each module receives structured input, produces structured output,
              logs its work, exposes its hypotheses, and reports its confidence.
            </p>
          </Reveal>

          <div style={S.pipelineGrid}>
            {[
              { n: '01', name: 'Input Normalizer', desc: 'Validates input, fills defaults, logs every assumption.' },
              { n: '02', name: 'Knowledge Layer', desc: 'Queries Open Targets, Human Protein Atlas, UniProt. Curated fallback.' },
              { n: '03', name: 'Parameter Builder', desc: 'Explicit rules for clearance, penetration, BBB, binding kinetics.' },
              { n: '04', name: 'PBPK Engine', desc: '15-compartment ODE solver (BDF). Monte Carlo uncertainty on all parameters.' },
              { n: '05', name: 'Dosimetry Engine', desc: 'MIRD S-values. Organ doses, dose-limiting organ, therapeutic index.' },
              { n: '06', name: 'PD / Effect Engine', desc: 'Target occupancy, causal rules, radiotheranostic dose-response.' },
              { n: '07', name: 'Decision Engine', desc: 'Weighted scoring. Ranking. Why and why not for each recommendation.' },
            ].map((m, i) => (
              <Reveal key={i} delay={0.06 * i}>
                <div style={S.pipelineCard}>
                  <span style={S.pipelineNum}>{m.n}</span>
                  <div>
                    <h4 style={S.pipelineName}>{m.name}</h4>
                    <p style={S.pipelineDesc}>{m.desc}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── TARGETS ── */}
      <section id="targets" style={S.section}>
        <div style={S.container}>
          <Reveal><p style={S.eyebrow}>Validated Targets</p></Reveal>
          <Reveal delay={0.05}>
            <h2 style={S.h2}>Built on landmark theranostics.</h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p style={{ ...S.body, maxWidth: '540px', marginBottom: '56px' }}>
              V1 is validated on the most established theranostic targets,
              each backed by phase III trials or FDA-approved therapies.
            </p>
          </Reveal>

          <div style={S.targetGrid}>
            {[
              { sym: 'PSMA', gene: 'FOLH1', cancer: 'Prostate cancer', pair: '⁶⁸Ga-PSMA-11 → ¹⁷⁷Lu-PSMA-617', trial: 'VISION — Sartor et al., NEJM 2021' },
              { sym: 'SSTR2', gene: 'SSTR2', cancer: 'Neuroendocrine tumors', pair: '⁶⁸Ga-DOTATATE → ¹⁷⁷Lu-DOTATATE', trial: 'NETTER-1 — Strosberg et al., NEJM 2017' },
              { sym: 'HER2', gene: 'ERBB2', cancer: 'Breast & gastric cancer', pair: '⁸⁹Zr-Trastuzumab → ¹⁷⁷Lu-Trastuzumab', trial: 'Dijkers et al., Clin Pharmacol Ther 2010' },
              { sym: 'FAP', gene: 'FAP', cancer: 'Pan-tumor stroma', pair: '⁶⁸Ga-FAPI-46 → ¹⁷⁷Lu-FAP-2286', trial: 'Ballal et al., Scientific Reports 2021' },
              { sym: 'CD20', gene: 'MS4A1', cancer: 'Lymphoma & CLL', pair: '⁸⁹Zr-Rituximab → ⁹⁰Y-Ibritumomab', trial: 'FDA-approved radioimmunotherapy' },
            ].map((t, i) => (
              <Reveal key={i} delay={0.06 * i}>
                <div style={S.tCard}>
                  <div style={S.tCardHeader}>
                    <span style={S.tSym}>{t.sym}</span>
                    <span style={S.tGene}>{t.gene}</span>
                  </div>
                  <p style={S.tCancer}>{t.cancer}</p>
                  <div style={S.tDivider} />
                  <p style={S.tPairLabel}>Theranostic pair</p>
                  <p style={S.tPair}>{t.pair}</p>
                  <p style={S.tTrial}>{t.trial}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── SCIENCE ── */}
      <section id="science" style={{ ...S.section, background: '#fff' }}>
        <div style={S.container}>
          <Reveal><p style={S.eyebrow}>Scientific Foundation</p></Reveal>
          <Reveal delay={0.05}>
            <h2 style={S.h2}>Grounded in peer-reviewed research.</h2>
          </Reveal>

          <div style={S.sciGrid}>
            {[
              { area: 'Pharmacokinetics', refs: ['Nestorov I. (2003) Clinical Pharmacokinetics', 'Shah DK, Betts AM. (2012) J Pharmacokinet Pharmacodyn', 'ICRP Publication 89 (2002) — Reference body parameters'] },
              { area: 'Tumor penetration', refs: ['Thurber GM, Schmidt MM, Wittrup KD. (2008) Adv Drug Deliv Rev', 'Thurber GM, Wittrup KD. (2012) Cancer Research'] },
              { area: 'Internal dosimetry', refs: ['Stabin MG et al. (2005) OLINDA/EXM — J Nucl Med', 'Bolch WE et al. (2009) MIRD Pamphlet No. 21', 'Bodei L et al. (2008) Eur J Nucl Med Mol Imaging'] },
              { area: 'Biological data', refs: ['Open Targets — Ochoa et al. (2023) Nucleic Acids Res', 'Human Protein Atlas — Uhlén et al. (2015) Science', 'UniProt Consortium (2023) Nucleic Acids Res'] },
            ].map((s, i) => (
              <Reveal key={i} delay={0.06 * i}>
                <div style={S.sciCard}>
                  <h4 style={S.sciTitle}>{s.area}</h4>
                  {s.refs.map((r, j) => <p key={j} style={S.sciRef}>{r}</p>)}
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={S.cta}>
        <GradientOrb color1="#059669" color2="#06b6d4" size="700px" top="-300px" left="30%" delay="1s" />
        <div style={S.container}>
          <Reveal>
            <h2 style={{ ...S.h2, fontSize: '42px', marginBottom: '16px' }}>Ready to simulate?</h2>
          </Reveal>
          <Reveal delay={0.05}>
            <p style={{ ...S.body, maxWidth: '480px', marginBottom: '32px' }}>
              Explore biodistribution, dosimetry, and biological effects
              for your theranostic strategy.
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <button onClick={onEnter} style={S.btnPrimary}>
              Launch Platform <span style={{ marginLeft: '8px' }}>&rarr;</span>
            </button>
          </Reveal>
          <Reveal delay={0.15}>
            <p style={S.disclaimer}>For research use only. Not for clinical decision-making.</p>
          </Reveal>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer style={S.footer}>
        <div style={{ ...S.container, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <span style={{ ...S.logo, fontSize: '16px' }}>TheraPredict</span>
            <p style={S.footerText}>Mechanistic Theranostic Simulation Platform — V1</p>
          </div>
          <p style={S.footerText}>
            SciPy &middot; FastAPI &middot; React &middot; Open Targets &middot; Human Protein Atlas &middot; UniProt
          </p>
        </div>
      </footer>
    </div>
  )
}

// ─── Styles ────────────────────────────────────────────────────────────

const S = {
  // Nav
  navInner: {
    maxWidth: '1140px', margin: '0 auto', padding: '0 32px',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    height: '60px',
  },
  logo: {
    fontSize: '18px', fontWeight: 700, letterSpacing: '-0.02em', color: '#0a0a0a',
  },
  navLinks: { display: 'flex', alignItems: 'center', gap: '28px' },
  navLink: {
    color: '#64748b', textDecoration: 'none', fontSize: '14px', fontWeight: 500,
    transition: 'color 0.2s',
  },
  navCta: {
    padding: '8px 20px', borderRadius: '8px', border: 'none',
    background: '#0a0a0a', color: '#fff', fontSize: '13px', fontWeight: 600,
    cursor: 'pointer', transition: 'opacity 0.2s',
  },

  // Hero
  hero: {
    minHeight: '100vh', display: 'flex', alignItems: 'center',
    padding: '140px 32px 100px', position: 'relative', overflow: 'hidden',
  },
  heroInner: { maxWidth: '1140px', margin: '0 auto', position: 'relative', zIndex: 1 },
  heroLabel: {
    fontSize: '13px', fontWeight: 600, letterSpacing: '0.08em',
    textTransform: 'uppercase', color: '#059669', marginBottom: '24px',
  },
  heroH1: {
    fontSize: 'clamp(40px, 6vw, 72px)', fontWeight: 800, lineHeight: 1.05,
    letterSpacing: '-0.03em', color: '#0a0a0a', marginBottom: '28px',
  },
  heroP: {
    fontSize: '18px', lineHeight: 1.7, color: '#64748b',
    maxWidth: '540px', marginBottom: '36px',
  },
  btnPrimary: {
    display: 'inline-flex', alignItems: 'center',
    padding: '14px 32px', borderRadius: '10px', border: 'none',
    background: '#0a0a0a', color: '#fff', fontSize: '15px', fontWeight: 600,
    cursor: 'pointer', transition: 'opacity 0.2s',
  },
  btnSecondary: {
    display: 'inline-flex', alignItems: 'center',
    padding: '14px 32px', borderRadius: '10px',
    border: '1px solid #d1d5db', background: 'transparent',
    color: '#374151', fontSize: '15px', fontWeight: 600,
    cursor: 'pointer', textDecoration: 'none', transition: 'border-color 0.2s',
  },

  // Stats bar
  statsBar: {
    borderTop: '1px solid #e5e7eb', borderBottom: '1px solid #e5e7eb',
    padding: '32px', background: '#fff',
  },
  statsInner: {
    maxWidth: '1140px', margin: '0 auto',
    display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '24px',
  },
  statItem: { display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minWidth: '120px' },
  statVal: { fontSize: '32px', fontWeight: 800, color: '#0a0a0a', letterSpacing: '-0.02em' },
  statLabel: { fontSize: '12px', color: '#94a3b8', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' },

  // Sections
  section: { padding: '100px 32px' },
  container: { maxWidth: '1140px', margin: '0 auto' },
  eyebrow: {
    fontSize: '12px', fontWeight: 700, letterSpacing: '0.1em',
    textTransform: 'uppercase', color: '#059669', marginBottom: '16px',
  },
  h2: {
    fontSize: 'clamp(30px, 4vw, 48px)', fontWeight: 800, lineHeight: 1.1,
    letterSpacing: '-0.02em', color: '#0a0a0a', marginBottom: '20px',
  },
  body: { fontSize: '16px', lineHeight: 1.75, color: '#64748b' },

  // Two-col about
  twoCol: { display: 'flex', gap: '64px', flexWrap: 'wrap' },
  colText: { flex: '1 1 400px' },
  colCards: { flex: '1 1 360px', display: 'flex', flexDirection: 'column', gap: '12px' },
  miniCard: {
    padding: '20px 24px', borderRadius: '12px', border: '1px solid #e5e7eb',
    background: '#fff', transition: 'border-color 0.3s',
  },
  miniCardTitle: { fontSize: '15px', fontWeight: 700, color: '#0a0a0a', marginBottom: '6px' },
  miniCardText: { fontSize: '14px', lineHeight: 1.6, color: '#64748b' },

  // Quote
  quoteSection: {
    padding: '80px 32px', background: '#fff',
    borderTop: '1px solid #e5e7eb', borderBottom: '1px solid #e5e7eb',
  },
  quote: {
    fontSize: 'clamp(20px, 2.5vw, 28px)', fontWeight: 500, lineHeight: 1.5,
    color: '#374151', fontStyle: 'italic', maxWidth: '700px',
    borderLeft: '3px solid #059669', paddingLeft: '24px',
  },

  // Pipeline
  pipelineGrid: { display: 'flex', flexDirection: 'column', gap: '10px' },
  pipelineCard: {
    display: 'flex', alignItems: 'flex-start', gap: '20px',
    padding: '20px 24px', borderRadius: '12px', border: '1px solid #e5e7eb',
    transition: 'border-color 0.3s, box-shadow 0.3s',
  },
  pipelineNum: {
    fontSize: '13px', fontWeight: 800, color: '#059669',
    width: '36px', height: '36px', borderRadius: '10px',
    border: '1.5px solid #d1fae5', background: '#ecfdf5',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  pipelineName: { fontSize: '15px', fontWeight: 700, color: '#0a0a0a', marginBottom: '2px' },
  pipelineDesc: { fontSize: '14px', color: '#64748b', lineHeight: 1.5 },

  // Targets
  targetGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))',
    gap: '14px',
  },
  tCard: {
    padding: '24px', borderRadius: '14px', border: '1px solid #e5e7eb',
    background: '#fff', transition: 'box-shadow 0.3s, border-color 0.3s',
  },
  tCardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' },
  tSym: { fontSize: '20px', fontWeight: 800, letterSpacing: '-0.01em', color: '#0a0a0a' },
  tGene: { fontSize: '12px', color: '#94a3b8', fontFamily: 'monospace' },
  tCancer: { fontSize: '14px', color: '#64748b', marginBottom: '12px' },
  tDivider: { height: '1px', background: '#e5e7eb', margin: '12px 0' },
  tPairLabel: { fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#059669', marginBottom: '4px' },
  tPair: { fontSize: '13px', color: '#374151', marginBottom: '12px', lineHeight: 1.4 },
  tTrial: { fontSize: '12px', color: '#94a3b8', lineHeight: 1.4 },

  // Science
  sciGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
    gap: '14px', marginTop: '40px',
  },
  sciCard: {
    padding: '24px', borderRadius: '12px', border: '1px solid #e5e7eb',
  },
  sciTitle: { fontSize: '15px', fontWeight: 700, color: '#0a0a0a', marginBottom: '12px' },
  sciRef: { fontSize: '13px', color: '#64748b', lineHeight: 1.5, marginBottom: '6px', paddingLeft: '12px', borderLeft: '2px solid #e5e7eb' },

  // CTA
  cta: {
    padding: '100px 32px', textAlign: 'center', position: 'relative', overflow: 'hidden',
  },
  disclaimer: { fontSize: '12px', color: '#94a3b8', marginTop: '20px' },

  // Footer
  footer: {
    padding: '32px', borderTop: '1px solid #e5e7eb',
  },
  footerText: { fontSize: '12px', color: '#94a3b8', marginTop: '4px' },
}
