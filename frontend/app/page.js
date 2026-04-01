import Link from 'next/link'

export default function HomePage() {
  return (
    <div style={{ background: '#fafafa', color: '#111' }}>

      {/* NAV */}
      <nav style={S.nav}>
        <div style={S.navInner}>
          <span style={S.logo}>TheraPredict</span>
          <div style={S.navLinks}>
            <a href="#why" style={S.navLink}>Why it matters</a>
            <a href="#what" style={S.navLink}>What we do</a>
            <a href="#science" style={S.navLink}>Science</a>
            <Link href="/simulate" style={S.navCta}>Launch Platform</Link>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section style={S.hero}>
        <div style={S.heroInner}>
          <p style={S.eyebrow}>Mechanistic Simulation Platform</p>
          <h1 style={S.h1}>
            Predict biological outcomes<br />before real-world testing.
          </h1>
          <p style={S.heroP}>
            TheraPredict is a mechanistic simulation platform that models how
            therapeutic strategies behave in the human body — from biodistribution
            to target engagement and toxicity.
          </p>
          <p style={S.heroAccent}>
            We simulate consequence, not just interaction.
          </p>
          <div style={S.heroBtns}>
            <Link href="/simulate" style={S.btnPrimary}>Launch Simulation &rarr;</Link>
            <a href="#what" style={S.btnSecondary}>See how it works</a>
          </div>
        </div>
      </section>

      {/* SUBTEXT */}
      <section style={S.subtextSection}>
        <div style={S.container}>
          <p style={S.subtextLead}>
            Reduce experimental uncertainty before in vivo testing.
          </p>
          <p style={S.subtextBody}>
            TheraPredict helps research teams prioritize theranostic strategies
            by simulating whole-body behavior using explainable, auditable models.
          </p>
        </div>
      </section>

      {/* WHY IT MATTERS */}
      <section id="why" style={{ ...S.section, background: '#fff' }}>
        <div style={S.container}>
          <p style={S.eyebrow}>The Problem</p>
          <h2 style={S.h2}>Why it matters</h2>
          <p style={S.sectionLead}>
            Drug discovery still relies heavily on trial and error.
          </p>
          <div style={S.threeCol}>
            <div style={S.problemCard}>
              <p style={S.problemText}>Many candidates fail late due to poor distribution or unexpected toxicity.</p>
            </div>
            <div style={S.problemCard}>
              <p style={S.problemText}>Molecular binding does not guarantee biological success in the patient.</p>
            </div>
            <div style={S.problemCard}>
              <p style={S.problemText}>Experimental validation is slow, expensive, and often inconclusive.</p>
            </div>
          </div>
          <p style={S.sectionConclusion}>
            TheraPredict introduces a simulation layer between molecular design
            and real-world testing.
          </p>
        </div>
      </section>

      {/* WHAT WE DO */}
      <section id="what" style={S.section}>
        <div style={S.container}>
          <p style={S.eyebrow}>The Platform</p>
          <h2 style={S.h2}>What we do</h2>
          <p style={S.sectionLead}>
            We simulate how therapeutic agents behave in the human body
            using mechanistic models.
          </p>
          <div style={S.ioGrid}>
            <div style={S.ioCard}>
              <h3 style={S.ioTitle}>Input</h3>
              <ul style={S.ioList}>
                <li>Target (PSMA, SSTR2, HER2, FAP, CD20)</li>
                <li>Agent (antibody, peptide, small molecule, nanobody)</li>
                <li>Isotope and dose</li>
                <li>Patient parameters</li>
              </ul>
            </div>
            <div style={S.ioArrow}>&rarr;</div>
            <div style={S.ioCard}>
              <h3 style={S.ioTitle}>Output</h3>
              <ul style={S.ioList}>
                <li>Biodistribution across 15 organs</li>
                <li>Time-activity curves</li>
                <li>Radiation dosimetry</li>
                <li>Target engagement estimation</li>
                <li>Biological effect (directional)</li>
                <li>Strategy ranking with rationale</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* PIPELINE */}
      <section style={{ ...S.section, background: '#fff' }}>
        <div style={S.container}>
          <p style={S.eyebrow}>The Pipeline</p>
          <h2 style={S.h2}>Seven modules. Full traceability.</h2>
          <div style={S.pipelineRow}>
            {['Target', 'Agent', 'Parameters', 'PBPK', 'Dosimetry', 'Effect', 'Decision'].map((step, i) => (
              <div key={step} style={S.pipelineStep}>
                <span style={S.pipelineNum}>{String(i + 1).padStart(2, '0')}</span>
                <span style={S.pipelineLabel}>{step}</span>
              </div>
            ))}
          </div>
          <p style={S.pipelineNote}>
            Each step is explicit, traceable, and grounded in known biology.
          </p>
        </div>
      </section>

      {/* DIFFERENTIATOR */}
      <section style={S.diffSection}>
        <div style={S.container}>
          <p style={S.eyebrow}>Core Differentiator</p>
          <h2 style={S.h2}>From interaction to consequence.</h2>
          <p style={S.sectionLead}>
            Most computational tools focus on molecular interaction.
            TheraPredict focuses on what happens next.
          </p>
          <div style={S.diffGrid}>
            {[
              'Where does it go in the body?',
              'Does it reach the target?',
              'What organs are exposed?',
              'Is the biological effect plausible?',
            ].map((q) => (
              <div key={q} style={S.diffItem}>
                <span style={S.diffQ}>{q}</span>
              </div>
            ))}
          </div>
          <p style={S.sectionConclusion}>
            We model the full biological pathway from injection to outcome.
          </p>
        </div>
      </section>

      {/* VALIDATION */}
      <section style={{ ...S.section, background: '#fff' }}>
        <div style={S.container}>
          <p style={S.eyebrow}>Validation</p>
          <h2 style={S.h2}>Built on mechanistic modeling and validated scenarios.</h2>
          <div style={S.statsGrid}>
            {[
              ['15', 'Physiological compartments'],
              ['7', 'Radioisotopes supported'],
              ['5', 'Validated molecular targets'],
              ['128', 'Tests across known cases'],
            ].map(([val, label]) => (
              <div key={label} style={S.statCard}>
                <span style={S.statVal}>{val}</span>
                <span style={S.statLabel}>{label}</span>
              </div>
            ))}
          </div>
          <p style={S.validationNote}>
            The system reproduces expected biodistribution patterns and
            organ-specific uptake trends for established theranostic agents.
          </p>
        </div>
      </section>

      {/* USE CASES */}
      <section style={S.section}>
        <div style={S.container}>
          <p style={S.eyebrow}>Applications</p>
          <h2 style={S.h2}>Use cases</h2>
          <div style={S.useCaseGrid}>
            <UseCase title="Theranostic strategy comparison" desc="Compare agents targeting the same pathway and select optimal candidates." />
            <UseCase title="Preclinical prioritization" desc="Reduce the number of experimental candidates before animal studies." />
            <UseCase title="Dosimetry estimation" desc="Estimate tumor dose and identify dose-limiting organs before treatment." />
            <UseCase title="Hypothesis exploration" desc="Test biological strategies before committing to experimental validation." />
          </div>
        </div>
      </section>

      {/* SCIENCE */}
      <section id="science" style={{ ...S.section, background: '#fff' }}>
        <div style={S.container}>
          <p style={S.eyebrow}>Scientific Foundation</p>
          <h2 style={S.h2}>No black box. All assumptions explicit.</h2>
          <div style={S.sciList}>
            <SciItem text="Physiologically-Based Pharmacokinetic (PBPK) modeling — 15 compartments, ODE solver" />
            <SciItem text="Mass-action binding kinetics — Kd, kon, koff, target occupancy (Hill model)" />
            <SciItem text="Monte Carlo uncertainty propagation — confidence intervals on all predictions" />
            <SciItem text="MIRD/OLINDA dosimetry — S-values for Lu-177, Y-90, Ac-225, I-131" />
            <SciItem text="Literature-derived biology — Open Targets, Human Protein Atlas, UniProt" />
          </div>
          <p style={S.sciNote}>All results are traceable. All parameters are auditable.</p>
        </div>
      </section>

      {/* TARGETS */}
      <section style={S.section}>
        <div style={S.container}>
          <p style={S.eyebrow}>Validated Targets</p>
          <div style={S.targetRow}>
            {['PSMA', 'SSTR2', 'HER2', 'FAP', 'CD20'].map((t) => (
              <span key={t} style={S.targetBadge}>{t}</span>
            ))}
          </div>
          <p style={S.targetNote}>
            Each target includes expression profiles, tissue accessibility,
            and known biological behavior from peer-reviewed sources.
          </p>
        </div>
      </section>

      {/* TRUST */}
      <section style={{ ...S.section, background: '#fff' }}>
        <div style={S.container}>
          <p style={S.eyebrow}>Explainability by Design</p>
          <h2 style={S.h2}>Every simulation provides:</h2>
          <div style={S.trustGrid}>
            {[
              'Parameter traceability',
              'Activated rules',
              'Confidence scores per module',
              'Source data provenance',
              'Execution logs (JSONL)',
              'Hypotheses stated explicitly',
            ].map((item) => (
              <div key={item} style={S.trustItem}>
                <span style={S.trustCheck}>&#10003;</span>
                <span style={S.trustText}>{item}</span>
              </div>
            ))}
          </div>
          <p style={S.trustNote}>
            TheraPredict is designed for scientific auditability.
          </p>
        </div>
      </section>

      {/* POSITIONING */}
      <section style={S.posSection}>
        <div style={S.container}>
          <h2 style={S.posTitle}>
            Bridging molecular design<br />and biological reality.
          </h2>
          <p style={S.posText}>
            TheraPredict sits between drug design and experimental validation.
            We provide a decision layer that helps teams understand whether
            a strategy is biologically plausible before testing it in the real world.
          </p>
        </div>
      </section>

      {/* FINAL CTA */}
      <section style={S.ctaSection}>
        <div style={S.container}>
          <h2 style={S.ctaTitle}>Simulate before you test.</h2>
          <div style={S.heroBtns}>
            <Link href="/simulate" style={S.btnPrimary}>Launch Platform &rarr;</Link>
          </div>
          <p style={S.disclaimer}>For research use only. Not for clinical decision-making.</p>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={S.footer}>
        <div style={{ ...S.container, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <span style={S.logo}>TheraPredict</span>
            <p style={S.footerText}>Mechanistic Theranostic Simulation Platform</p>
          </div>
          <p style={S.footerText}>
            Built with SciPy, FastAPI, Next.js &middot; Data from Open Targets, HPA, UniProt
          </p>
        </div>
      </footer>
    </div>
  )
}

function UseCase({ title, desc }) {
  return (
    <div style={S.useCaseCard}>
      <h4 style={S.useCaseTitle}>{title}</h4>
      <p style={S.useCaseDesc}>{desc}</p>
    </div>
  )
}

function SciItem({ text }) {
  return (
    <div style={S.sciItem}>
      <span style={S.sciDot} />
      <span style={S.sciText}>{text}</span>
    </div>
  )
}

const S = {
  nav: {
    position: 'sticky', top: 0, zIndex: 100,
    background: 'rgba(250,250,250,0.9)', backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    borderBottom: '1px solid #e5e7eb', padding: '0 32px',
  },
  navInner: {
    maxWidth: '1080px', margin: '0 auto',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '56px',
  },
  logo: { fontSize: '17px', fontWeight: 700, letterSpacing: '-0.02em', color: '#111' },
  navLinks: { display: 'flex', alignItems: 'center', gap: '24px' },
  navLink: { color: '#6b7280', textDecoration: 'none', fontSize: '13px', fontWeight: 500 },
  navCta: {
    padding: '7px 18px', borderRadius: '7px', background: '#111', color: '#fff',
    fontSize: '13px', fontWeight: 600, textDecoration: 'none',
  },

  hero: { padding: '140px 32px 80px' },
  heroInner: { maxWidth: '1080px', margin: '0 auto' },
  eyebrow: {
    fontSize: '11px', fontWeight: 700, letterSpacing: '0.12em',
    textTransform: 'uppercase', color: '#059669', marginBottom: '20px',
  },
  h1: {
    fontSize: 'clamp(36px, 5.5vw, 64px)', fontWeight: 800, lineHeight: 1.08,
    letterSpacing: '-0.03em', color: '#111', marginBottom: '24px', maxWidth: '680px',
  },
  h2: {
    fontSize: 'clamp(28px, 3.5vw, 42px)', fontWeight: 800, lineHeight: 1.12,
    letterSpacing: '-0.02em', color: '#111', marginBottom: '20px',
  },
  heroP: { fontSize: '17px', lineHeight: 1.7, color: '#6b7280', maxWidth: '520px', marginBottom: '12px' },
  heroAccent: {
    fontSize: '17px', fontWeight: 600, color: '#111', marginBottom: '32px',
    fontStyle: 'italic',
  },
  heroBtns: { display: 'flex', gap: '12px', flexWrap: 'wrap' },
  btnPrimary: {
    display: 'inline-flex', alignItems: 'center', padding: '12px 28px',
    borderRadius: '8px', background: '#111', color: '#fff',
    fontSize: '14px', fontWeight: 600, textDecoration: 'none', border: 'none',
  },
  btnSecondary: {
    display: 'inline-flex', alignItems: 'center', padding: '12px 28px',
    borderRadius: '8px', border: '1px solid #d1d5db', background: 'transparent',
    color: '#374151', fontSize: '14px', fontWeight: 600, textDecoration: 'none',
  },

  subtextSection: {
    padding: '60px 32px', borderTop: '1px solid #e5e7eb', borderBottom: '1px solid #e5e7eb',
    background: '#fff',
  },
  container: { maxWidth: '1080px', margin: '0 auto' },
  subtextLead: { fontSize: '20px', fontWeight: 700, color: '#111', marginBottom: '8px' },
  subtextBody: { fontSize: '16px', lineHeight: 1.7, color: '#6b7280', maxWidth: '560px' },

  section: { padding: '80px 32px' },
  sectionLead: { fontSize: '17px', lineHeight: 1.7, color: '#6b7280', maxWidth: '520px', marginBottom: '40px' },
  sectionConclusion: { fontSize: '16px', fontWeight: 600, color: '#111', marginTop: '32px' },

  threeCol: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '8px' },
  problemCard: {
    padding: '24px', borderRadius: '10px', border: '1px solid #e5e7eb', background: '#fafafa',
  },
  problemText: { fontSize: '15px', lineHeight: 1.6, color: '#374151', margin: 0 },

  ioGrid: { display: 'flex', gap: '24px', alignItems: 'flex-start', flexWrap: 'wrap' },
  ioCard: { flex: '1 1 280px', padding: '28px', borderRadius: '10px', border: '1px solid #e5e7eb', background: '#fff' },
  ioTitle: { fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#059669', marginBottom: '16px' },
  ioList: { listStyle: 'none', padding: 0, margin: 0 },
  ioArrow: { fontSize: '24px', color: '#d1d5db', alignSelf: 'center', padding: '0 8px' },

  pipelineRow: { display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' },
  pipelineStep: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '10px 16px', borderRadius: '8px', border: '1px solid #e5e7eb', background: '#fafafa',
  },
  pipelineNum: { fontSize: '11px', fontWeight: 800, color: '#059669' },
  pipelineLabel: { fontSize: '14px', fontWeight: 600, color: '#111' },
  pipelineNote: { fontSize: '14px', color: '#6b7280', fontStyle: 'italic' },

  diffSection: { padding: '80px 32px', background: '#f8faf9' },
  diffGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', marginBottom: '8px' },
  diffItem: { padding: '20px 24px', borderRadius: '10px', borderLeft: '3px solid #059669', background: '#fff' },
  diffQ: { fontSize: '15px', fontWeight: 600, color: '#111' },

  statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' },
  statCard: { textAlign: 'center', padding: '24px 16px' },
  statVal: { display: 'block', fontSize: '36px', fontWeight: 800, color: '#111', letterSpacing: '-0.02em' },
  statLabel: { display: 'block', fontSize: '12px', color: '#6b7280', marginTop: '4px' },
  validationNote: { fontSize: '15px', color: '#6b7280', lineHeight: 1.6 },

  useCaseGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' },
  useCaseCard: { padding: '24px', borderRadius: '10px', border: '1px solid #e5e7eb', background: '#fff' },
  useCaseTitle: { fontSize: '15px', fontWeight: 700, color: '#111', marginBottom: '8px' },
  useCaseDesc: { fontSize: '14px', lineHeight: 1.6, color: '#6b7280', margin: 0 },

  sciList: { display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' },
  sciItem: { display: 'flex', alignItems: 'flex-start', gap: '12px' },
  sciDot: {
    width: '6px', height: '6px', borderRadius: '50%', background: '#059669',
    flexShrink: 0, marginTop: '7px',
  },
  sciText: { fontSize: '15px', lineHeight: 1.6, color: '#374151' },
  sciNote: { fontSize: '15px', fontWeight: 600, color: '#111' },

  targetRow: { display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' },
  targetBadge: {
    padding: '10px 24px', borderRadius: '8px', border: '1px solid #e5e7eb',
    background: '#fff', fontSize: '16px', fontWeight: 700, color: '#111',
    letterSpacing: '0.02em',
  },
  targetNote: { fontSize: '14px', color: '#6b7280', lineHeight: 1.6 },

  trustGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', marginBottom: '20px' },
  trustItem: { display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 16px' },
  trustCheck: { color: '#059669', fontSize: '16px', fontWeight: 700 },
  trustText: { fontSize: '14px', color: '#374151' },
  trustNote: { fontSize: '15px', fontWeight: 600, color: '#111' },

  posSection: {
    padding: '80px 32px', background: '#111', color: '#fff', textAlign: 'center',
  },
  posTitle: {
    fontSize: 'clamp(28px, 3.5vw, 42px)', fontWeight: 800, lineHeight: 1.15,
    letterSpacing: '-0.02em', color: '#fff', marginBottom: '20px',
  },
  posText: { fontSize: '17px', lineHeight: 1.7, color: '#9ca3af', maxWidth: '560px', margin: '0 auto' },

  ctaSection: { padding: '80px 32px', textAlign: 'center' },
  ctaTitle: {
    fontSize: '36px', fontWeight: 800, color: '#111',
    letterSpacing: '-0.02em', marginBottom: '24px',
  },
  disclaimer: { fontSize: '12px', color: '#9ca3af', marginTop: '20px' },

  footer: { padding: '32px', borderTop: '1px solid #e5e7eb' },
  footerText: { fontSize: '12px', color: '#9ca3af', marginTop: '4px' },
}

// Style list items
S.ioList = { ...S.ioList }
