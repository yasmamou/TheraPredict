import Link from 'next/link'

// ─── This page is 100% server-rendered (SSG). ──────────────────────────
// All text is in the HTML. No JavaScript needed to read it.
// "View Page Source" shows full content.

export default function HomePage() {
  return (
    <div style={{ background: '#fafafa', color: '#0a0a0a' }}>

      {/* ── NAV ── */}
      <nav style={S.nav}>
        <div style={S.navInner}>
          <span style={S.logo}>TheraPredict</span>
          <div style={S.navLinks}>
            <a href="#about" style={S.navLink}>About</a>
            <a href="#pipeline" style={S.navLink}>Pipeline</a>
            <a href="#targets" style={S.navLink}>Targets</a>
            <a href="#science" style={S.navLink}>Science</a>
            <Link href="/simulate" style={S.navCta}>Launch Platform</Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={S.hero}>
        <div style={S.heroInner}>
          <p style={S.eyebrow}>Mechanistic Theranostic Simulation</p>
          <h1 style={S.h1}>
            Predicting where medicine meets the molecule.
          </h1>
          <p style={S.heroP}>
            TheraPredict simulates the full journey of theranostic agents through
            the human body — from injection to tumor uptake, organ dosimetry, and
            biological effect — with complete traceability at every step.
          </p>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <Link href="/simulate" style={S.btnPrimary}>
              Launch Platform &rarr;
            </Link>
            <a href="#about" style={S.btnSecondary}>Learn more</a>
          </div>
        </div>
      </section>

      {/* ── STATS ── */}
      <section style={S.statsBar}>
        <div style={S.statsInner}>
          {[
            ['15', 'Body compartments'],
            ['7', 'Radioisotopes'],
            ['5', 'Molecular targets'],
            ['7', 'Pipeline modules'],
            ['128', 'Validated tests'],
          ].map(([val, label]) => (
            <div key={label} style={S.statItem}>
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
              <p style={S.eyebrow}>The Platform</p>
              <h2 style={S.h2}>From molecular target to clinical insight.</h2>
              <p style={S.body}>
                TheraPredict bridges nuclear medicine and computational biology.
                Input a target, an agent, and a patient profile — get a complete
                simulation with biodistribution, radiation dosimetry, biological
                effects, and actionable recommendations.
              </p>
              <p style={S.body}>
                Every prediction is mechanistic, not a black box. Every parameter
                is traceable. Every hypothesis is stated. Every confidence interval
                is computed.
              </p>
            </div>
            <div style={S.colCards}>
              <Card title="Mechanistic PBPK" text="15-compartment physiologically-based model with ODE solver and Monte Carlo uncertainty quantification." />
              <Card title="Radiation dosimetry" text="MIRD/OLINDA-based internal dosimetry for Lu-177, Y-90, Ac-225, I-131. Organ doses and therapeutic index." />
              <Card title="Biological effects" text="Target occupancy, causal pharmacodynamic rules, dose-effect relationships. Directional, never speculative." />
              <Card title="Decision support" text="Transparent weighted scoring: efficacy, safety, practicality, confidence. Every sub-score visible." />
            </div>
          </div>
        </div>
      </section>

      {/* ── QUOTE ── */}
      <section style={S.quoteSection}>
        <div style={S.container}>
          <blockquote style={S.quote}>
            &ldquo;The goal of theranostics is simple: see what you treat, treat what you
            see. The challenge is predicting it before the patient is in the scanner.&rdquo;
          </blockquote>
        </div>
      </section>

      {/* ── PIPELINE ── */}
      <section id="pipeline" style={{ ...S.section, background: '#fff' }}>
        <div style={S.container}>
          <p style={S.eyebrow}>The Pipeline</p>
          <h2 style={S.h2}>Seven modules. Complete traceability.</h2>
          <p style={{ ...S.body, maxWidth: '540px', marginBottom: '48px' }}>
            Each module receives structured input, produces structured output,
            logs its work, exposes its hypotheses, and reports its confidence.
          </p>

          <div style={S.pipelineGrid}>
            <PipelineStep n="01" name="Input Normalizer" desc="Validates input, fills defaults, logs every assumption made." />
            <PipelineStep n="02" name="Knowledge Layer" desc="Queries Open Targets, Human Protein Atlas, UniProt. Curated fallback when offline." />
            <PipelineStep n="03" name="Parameter Builder" desc="Explicit rules for clearance, tumor penetration, blood-brain barrier, binding kinetics." />
            <PipelineStep n="04" name="PBPK Engine" desc="15-compartment ODE solver (BDF method). Monte Carlo uncertainty on all parameters." />
            <PipelineStep n="05" name="Dosimetry Engine" desc="MIRD formalism with OLINDA S-values. Organ doses, dose-limiting organ, therapeutic index." />
            <PipelineStep n="06" name="PD / Effect Engine" desc="Target occupancy (Hill model), causal rules, radiotheranostic dose-response." />
            <PipelineStep n="07" name="Decision Engine" desc="Weighted scoring with visible weights. Ranking with why and why not for each strategy." />
          </div>
        </div>
      </section>

      {/* ── TARGETS ── */}
      <section id="targets" style={S.section}>
        <div style={S.container}>
          <p style={S.eyebrow}>Validated Targets</p>
          <h2 style={S.h2}>Built on landmark theranostics.</h2>
          <p style={{ ...S.body, maxWidth: '540px', marginBottom: '48px' }}>
            V1 is validated on the most established theranostic targets,
            each backed by phase III trials or FDA-approved therapies.
          </p>

          <div style={S.targetGrid}>
            <TargetCard sym="PSMA" gene="FOLH1" cancer="Prostate cancer"
              pair="68Ga-PSMA-11 → 177Lu-PSMA-617"
              trial="VISION — Sartor et al., NEJM 2021" />
            <TargetCard sym="SSTR2" gene="SSTR2" cancer="Neuroendocrine tumors"
              pair="68Ga-DOTATATE → 177Lu-DOTATATE"
              trial="NETTER-1 — Strosberg et al., NEJM 2017" />
            <TargetCard sym="HER2" gene="ERBB2" cancer="Breast & gastric cancer"
              pair="89Zr-Trastuzumab → 177Lu-Trastuzumab"
              trial="Dijkers et al., Clin Pharmacol Ther 2010" />
            <TargetCard sym="FAP" gene="FAP" cancer="Pan-tumor stroma"
              pair="68Ga-FAPI-46 → 177Lu-FAP-2286"
              trial="Ballal et al., Scientific Reports 2021" />
            <TargetCard sym="CD20" gene="MS4A1" cancer="Lymphoma & CLL"
              pair="89Zr-Rituximab → 90Y-Ibritumomab"
              trial="FDA-approved radioimmunotherapy" />
          </div>
        </div>
      </section>

      {/* ── SCIENCE ── */}
      <section id="science" style={{ ...S.section, background: '#fff' }}>
        <div style={S.container}>
          <p style={S.eyebrow}>Scientific Foundation</p>
          <h2 style={S.h2}>Grounded in peer-reviewed research.</h2>

          <div style={S.sciGrid}>
            <SciCard area="Pharmacokinetics" refs={[
              'Nestorov I. (2003) Clinical Pharmacokinetics',
              'Shah DK, Betts AM. (2012) J Pharmacokinet Pharmacodyn',
              'ICRP Publication 89 (2002) — Reference body parameters',
            ]} />
            <SciCard area="Tumor penetration" refs={[
              'Thurber GM, Schmidt MM, Wittrup KD. (2008) Adv Drug Deliv Rev',
              'Thurber GM, Wittrup KD. (2012) Cancer Research',
            ]} />
            <SciCard area="Internal dosimetry" refs={[
              'Stabin MG et al. (2005) OLINDA/EXM — J Nucl Med',
              'Bolch WE et al. (2009) MIRD Pamphlet No. 21',
              'Bodei L et al. (2008) Eur J Nucl Med Mol Imaging',
            ]} />
            <SciCard area="Biological data" refs={[
              'Open Targets — Ochoa et al. (2023) Nucleic Acids Res',
              'Human Protein Atlas — Uhlén et al. (2015) Science',
              'UniProt Consortium (2023) Nucleic Acids Res',
            ]} />
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={S.cta}>
        <div style={S.container}>
          <h2 style={{ ...S.h2, fontSize: '42px', marginBottom: '16px' }}>Ready to simulate?</h2>
          <p style={{ ...S.body, maxWidth: '480px', marginBottom: '32px' }}>
            Explore biodistribution, dosimetry, and biological effects
            for your theranostic strategy.
          </p>
          <Link href="/simulate" style={S.btnPrimary}>
            Launch Platform &rarr;
          </Link>
          <p style={S.disclaimer}>For research use only. Not for clinical decision-making.</p>
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

// ─── Server components (no "use client" needed) ────────────────────────

function Card({ title, text }) {
  return (
    <div style={S.miniCard}>
      <h4 style={S.miniCardTitle}>{title}</h4>
      <p style={S.miniCardText}>{text}</p>
    </div>
  )
}

function PipelineStep({ n, name, desc }) {
  return (
    <div style={S.pipelineCard}>
      <span style={S.pipelineNum}>{n}</span>
      <div>
        <h4 style={S.pipelineName}>{name}</h4>
        <p style={S.pipelineDesc}>{desc}</p>
      </div>
    </div>
  )
}

function TargetCard({ sym, gene, cancer, pair, trial }) {
  return (
    <div style={S.tCard}>
      <div style={S.tCardHeader}>
        <span style={S.tSym}>{sym}</span>
        <span style={S.tGene}>{gene}</span>
      </div>
      <p style={S.tCancer}>{cancer}</p>
      <div style={S.tDivider} />
      <p style={S.tPairLabel}>Theranostic pair</p>
      <p style={S.tPair}>{pair}</p>
      <p style={S.tTrial}>{trial}</p>
    </div>
  )
}

function SciCard({ area, refs }) {
  return (
    <div style={S.sciCard}>
      <h4 style={S.sciTitle}>{area}</h4>
      {refs.map((r, i) => <p key={i} style={S.sciRef}>{r}</p>)}
    </div>
  )
}

// ─── Styles ────────────────────────────────────────────────────────────

const S = {
  nav: {
    position: 'sticky', top: 0, zIndex: 100,
    background: 'rgba(250,250,250,0.85)', backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
    borderBottom: '1px solid rgba(0,0,0,0.06)', padding: '0 32px',
  },
  navInner: {
    maxWidth: '1140px', margin: '0 auto',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    height: '60px',
  },
  logo: { fontSize: '18px', fontWeight: 700, letterSpacing: '-0.02em', color: '#0a0a0a' },
  navLinks: { display: 'flex', alignItems: 'center', gap: '28px' },
  navLink: { color: '#64748b', textDecoration: 'none', fontSize: '14px', fontWeight: 500 },
  navCta: {
    padding: '8px 20px', borderRadius: '8px', border: 'none',
    background: '#0a0a0a', color: '#fff', fontSize: '13px', fontWeight: 600,
    textDecoration: 'none',
  },
  hero: {
    minHeight: '90vh', display: 'flex', alignItems: 'center',
    padding: '120px 32px 100px',
  },
  heroInner: { maxWidth: '1140px', margin: '0 auto' },
  eyebrow: {
    fontSize: '12px', fontWeight: 700, letterSpacing: '0.1em',
    textTransform: 'uppercase', color: '#059669', marginBottom: '16px',
  },
  h1: {
    fontSize: 'clamp(40px, 6vw, 72px)', fontWeight: 800, lineHeight: 1.05,
    letterSpacing: '-0.03em', color: '#0a0a0a', marginBottom: '28px',
    maxWidth: '700px',
  },
  h2: {
    fontSize: 'clamp(30px, 4vw, 48px)', fontWeight: 800, lineHeight: 1.1,
    letterSpacing: '-0.02em', color: '#0a0a0a', marginBottom: '20px',
  },
  heroP: {
    fontSize: '18px', lineHeight: 1.7, color: '#64748b',
    maxWidth: '540px', marginBottom: '36px',
  },
  body: { fontSize: '16px', lineHeight: 1.75, color: '#64748b', marginBottom: '16px' },
  btnPrimary: {
    display: 'inline-flex', alignItems: 'center',
    padding: '14px 32px', borderRadius: '10px', border: 'none',
    background: '#0a0a0a', color: '#fff', fontSize: '15px', fontWeight: 600,
    textDecoration: 'none',
  },
  btnSecondary: {
    display: 'inline-flex', alignItems: 'center',
    padding: '14px 32px', borderRadius: '10px',
    border: '1px solid #d1d5db', background: 'transparent',
    color: '#374151', fontSize: '15px', fontWeight: 600, textDecoration: 'none',
  },
  statsBar: {
    borderTop: '1px solid #e5e7eb', borderBottom: '1px solid #e5e7eb',
    padding: '32px', background: '#fff',
  },
  statsInner: {
    maxWidth: '1140px', margin: '0 auto',
    display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '24px',
  },
  statItem: { display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minWidth: '100px' },
  statVal: { fontSize: '32px', fontWeight: 800, color: '#0a0a0a', letterSpacing: '-0.02em' },
  statLabel: { fontSize: '11px', color: '#94a3b8', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '0.05em', textAlign: 'center' },
  section: { padding: '100px 32px' },
  container: { maxWidth: '1140px', margin: '0 auto' },
  twoCol: { display: 'flex', gap: '64px', flexWrap: 'wrap' },
  colText: { flex: '1 1 400px' },
  colCards: { flex: '1 1 360px', display: 'flex', flexDirection: 'column', gap: '12px' },
  miniCard: { padding: '20px 24px', borderRadius: '12px', border: '1px solid #e5e7eb', background: '#fff' },
  miniCardTitle: { fontSize: '15px', fontWeight: 700, color: '#0a0a0a', marginBottom: '6px' },
  miniCardText: { fontSize: '14px', lineHeight: 1.6, color: '#64748b', margin: 0 },
  quoteSection: {
    padding: '80px 32px', background: '#fff',
    borderTop: '1px solid #e5e7eb', borderBottom: '1px solid #e5e7eb',
  },
  quote: {
    fontSize: 'clamp(20px, 2.5vw, 28px)', fontWeight: 500, lineHeight: 1.5,
    color: '#374151', fontStyle: 'italic', maxWidth: '700px',
    borderLeft: '3px solid #059669', paddingLeft: '24px', margin: 0,
  },
  pipelineGrid: { display: 'flex', flexDirection: 'column', gap: '10px' },
  pipelineCard: {
    display: 'flex', alignItems: 'flex-start', gap: '20px',
    padding: '20px 24px', borderRadius: '12px', border: '1px solid #e5e7eb',
  },
  pipelineNum: {
    fontSize: '13px', fontWeight: 800, color: '#059669',
    width: '36px', height: '36px', borderRadius: '10px',
    border: '1.5px solid #d1fae5', background: '#ecfdf5',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  pipelineName: { fontSize: '15px', fontWeight: 700, color: '#0a0a0a', marginBottom: '2px' },
  pipelineDesc: { fontSize: '14px', color: '#64748b', lineHeight: 1.5, margin: 0 },
  targetGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: '14px',
  },
  tCard: { padding: '24px', borderRadius: '14px', border: '1px solid #e5e7eb', background: '#fff' },
  tCardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' },
  tSym: { fontSize: '20px', fontWeight: 800, letterSpacing: '-0.01em', color: '#0a0a0a' },
  tGene: { fontSize: '12px', color: '#94a3b8', fontFamily: 'monospace' },
  tCancer: { fontSize: '14px', color: '#64748b', margin: 0 },
  tDivider: { height: '1px', background: '#e5e7eb', margin: '12px 0' },
  tPairLabel: { fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#059669', marginBottom: '4px' },
  tPair: { fontSize: '13px', color: '#374151', marginBottom: '12px', lineHeight: 1.4 },
  tTrial: { fontSize: '12px', color: '#94a3b8', lineHeight: 1.4, margin: 0 },
  sciGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
    gap: '14px', marginTop: '40px',
  },
  sciCard: { padding: '24px', borderRadius: '12px', border: '1px solid #e5e7eb' },
  sciTitle: { fontSize: '15px', fontWeight: 700, color: '#0a0a0a', marginBottom: '12px' },
  sciRef: { fontSize: '13px', color: '#64748b', lineHeight: 1.5, marginBottom: '6px', paddingLeft: '12px', borderLeft: '2px solid #e5e7eb' },
  cta: { padding: '100px 32px', textAlign: 'center' },
  disclaimer: { fontSize: '12px', color: '#94a3b8', marginTop: '20px' },
  footer: { padding: '32px', borderTop: '1px solid #e5e7eb' },
  footerText: { fontSize: '12px', color: '#94a3b8', marginTop: '4px' },
}
