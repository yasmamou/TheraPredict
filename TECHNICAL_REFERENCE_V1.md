# TheraPredict V1 — Technical Reference

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Pipeline Modules](#3-pipeline-modules)
4. [Mathematical Models](#4-mathematical-models)
5. [External Data Sources](#5-external-data-sources)
6. [Curated Knowledge Base](#6-curated-knowledge-base)
7. [Isotope & Dosimetry Data](#7-isotope--dosimetry-data)
8. [Confidence & Uncertainty](#8-confidence--uncertainty)
9. [File Structure](#9-file-structure)
10. [Running the Platform](#10-running-the-platform)
11. [Testing & Benchmarks](#11-testing--benchmarks)
12. [Scientific References](#12-scientific-references)

---

## 1. Overview

TheraPredict V1 is a **mechanistic theranostic simulation platform** that predicts the biodistribution, dosimetry, and biological effects of radiolabeled and targeted agents in oncology.

The platform is built on a **7-module pipeline**, each module being:
- deterministic when possible, probabilistic only when necessary,
- fully logged (structured JSON lines),
- traceable (every parameter, rule, and hypothesis is recorded),
- testable (unit tests + integration benchmarks on known agents).

### What V1 does

- Simulates whole-body pharmacokinetics (PBPK) for theranostic agents
- Computes internal radiation dosimetry (MIRD formalism)
- Estimates biological effects (target occupancy, directional PD)
- Ranks strategies with transparent, weighted scoring
- Provides a full audit trail for every prediction

### What V1 does NOT do

- Predict exact clinical outcomes
- Generate new protein sequences or perform docking
- Simulate full intracellular signaling cascades
- Replace clinical judgment

### Scope

| Category | V1 Scope |
|----------|----------|
| Targets | PSMA, SSTR2, HER2, FAP, CD20 |
| Agent classes | small molecule, peptide, nanobody, Fab, IgG |
| Isotopes | Ga-68, F-18, Lu-177, Y-90, Ac-225, Zr-89, I-131 |
| Body model | 15 compartments (plasma + 14 tissues including tumor) |

---

## 2. Architecture

### 2.1 Pipeline Flow

```
User Input (JSON, potentially incomplete)
    │
    ▼
┌──────────────────────┐
│  Module 1             │   Validates, normalizes, fills defaults (all logged)
│  Input Normalizer     │   → NormalizedRequest
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Module 2             │   Queries Open Targets, HPA, UniProt + curated fallback
│  Knowledge Layer      │   → TargetKnowledge (expression, accessibility, evidence)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Module 3             │   Explicit rules: clearance, penetration, BBB, binding
│  Parameter Builder    │   → BuiltParameters (PK, binding, tumor, risk)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Module 4             │   ODE-based PBPK solver + Monte Carlo uncertainty
│  PBPK Engine          │   → PBPKResult (time-activity curves, biodistribution)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Module 5             │   MIRD/OLINDA S-values, organ doses, therapeutic index
│  Dosimetry Engine     │   → DosimetryResultV1 (only for therapeutic isotopes)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Module 6             │   Target occupancy, causal rules, radiotheranostic PD
│  PD / Effect Engine   │   → PDResult (effect direction, plausibility, toxicity)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Module 7             │   Transparent weighted scoring, why / why not
│  Decision Engine      │   → DecisionResultV1 (scores, rank, recommendation)
└──────────┬───────────┘
           ▼
Output: Full result + logs + confidence per module + audit trail
```

### 2.2 Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.9+, FastAPI, Pydantic |
| ODE Solver | SciPy `solve_ivp` (BDF primary, Radau fallback) |
| Monte Carlo | NumPy random sampling, lognormal perturbations |
| Frontend | React 18, Vite, Plotly.js |
| API integrations | httpx (async HTTP client) |
| Testing | pytest |
| Containerization | Docker, Docker Compose |

---

## 3. Pipeline Modules

### 3.1 Module 1 — Input Normalizer

**File:** `src/theranostics/services/input_normalizer.py`

**Purpose:** Convert potentially incomplete user input into a fully populated `NormalizedRequest`.

**Key behaviors:**
- Validates target against V1 allowed list (PSMA, SSTR2, HER2, FAP, CD20)
- Normalizes isotope aliases (e.g., `68Ga` → `Ga-68`, `177Lu` → `Lu-177`)
- Fills missing agent parameters from class defaults (size, Kd, half-life, clearance fractions)
- Derives `koff` from `Kd × kon` when only Kd and kon are provided
- Assigns default dose based on isotope type (therapeutic: 7.4 GBq, diagnostic: 185 MBq)
- Converts renal/hepatic function descriptors to eGFR and liver scores

**Logging:** Every default applied is recorded in `defaults_applied[]`. Input and output hashes are stored for audit.

### 3.2 Module 2 — Knowledge Layer

**File:** `src/theranostics/services/knowledge_layer.py`

**Purpose:** Retrieve biological facts about the target from external APIs and curated internal data.

**This module provides FACTS, not predictions.**
- Correct: "PSMA expression: high in tumor, 0.62 in kidney, 0.58 in salivary glands"
- Incorrect: "the molecule will go to the kidney"

**Data retrieval order:**
1. Internal curated tables (always loaded as baseline)
2. Open Targets API — target-disease association score, evidence level
3. Human Protein Atlas API — tissue-level protein expression
4. UniProt API — protein structure, subcellular location, transmembrane domains

**Conflict resolution:** When HPA and curated data disagree by > 0.3, the average is used and the conflict is logged.

**Output:** `TargetKnowledge` object containing:
- `normal_tissue_expression`: dict of tissue → expression score [0, 1]
- `tumor_expression_score`: float [0, 1]
- `accessibility_score`, `internalization_score`, `shedding_risk`
- `evidence_level`: A (strong clinical), B (clinical), C (preclinical), D (limited)
- `sources_used`: list of data sources actually queried
- `conflicts`: list of data disagreements

### 3.3 Module 3 — Parameter Builder

**File:** `src/theranostics/services/parameter_builder.py`

**Purpose:** Transform biological knowledge + agent properties into numerical parameters for the PBPK/PD engines.

This is the core business logic module. Every rule is explicit and logged.

#### 3.3.1 Clearance Rules

| Condition | Clearance Route | Confidence |
|-----------|----------------|------------|
| MW < 60 kDa | Renal | 0.85 |
| MW ≥ 60 kDa, IgG with Fc | Hepatic + FcRn recycling (70% rescue) | 0.80 |
| MW ≥ 60 kDa, no Fc | Hepatic / RES | 0.70 |

**Rationale:** The glomerular filtration cutoff of ~60 kDa is well established (Thurber et al., 2008). FcRn-mediated recycling extends IgG half-life by rescuing ~70% of internalized antibody from lysosomal degradation (Roopenian & Akilesh, 2007).

#### 3.3.2 Tumor Penetration Rules

Based on a Thurber-inspired heuristic (Thurber et al., 2008):

| Agent Class | Base Penetration | Binding Site Barrier Penalty (Kd < 1 nM) |
|-------------|-----------------|------------------------------------------|
| small molecule | 0.85 | 0.00 |
| peptide | 0.85 | 0.00 |
| nanobody | 0.70 | 0.05 |
| Fab | 0.55 | 0.10 |
| IgG | 0.35 | 0.20 |

The **Thiele modulus** (φ) is computed as:

```
φ² = R²_Krogh × kon × [Ag] / D

where:
  R_Krogh = Krogh cylinder radius (~50 µm)
  kon     = association rate (M⁻¹s⁻¹)
  [Ag]    = antigen density (M)
  D       = interstitial diffusivity (cm²/s)
```

A high Thiele modulus (φ > 3) indicates binding site barrier: the agent binds too quickly at the tumor periphery to penetrate uniformly.

#### 3.3.3 Blood-Brain Barrier (BBB)

| Agent Class | BBB Permeability Score | Note |
|-------------|----------------------|------|
| IgG | 0.001 | Effectively excluded |
| Fab | 0.002 | Effectively excluded |
| nanobody | 0.005 | Very low |
| peptide | 0.02 | Low to moderate |
| small molecule | 0.05 | Variable (lipophilicity-dependent) |

#### 3.3.4 Binding Kinetics (Kon / Koff)

- If Kd and kon are provided: `koff = Kd × 10⁻⁹ × kon`
- If Kd is unknown: class defaults are applied with explicit warning
- No parameter is ever silently invented

#### 3.3.5 Tissue Target Densities

Expression scores from the Knowledge Layer are converted to approximate nM densities:

```
density_nM = expression_score × 200
```

The 200 nM reference corresponds to high receptor density (e.g., PSMA in prostate tumor ~100-200 nM, HER2 3+ in breast ~150-200 nM).

#### 3.3.6 Off-Target Scoring

```
off_target_score(tissue) = expression(tissue) × exposure_probability(tissue)
```

Exposure probability depends on:
- Vascularization and capillary fenestration
- Agent class (small molecules have higher renal exposure, IgG has higher liver/spleen)

### 3.4 Module 4 — PBPK Engine

**File:** `src/theranostics/services/pbpk_engine_v1.py`

**Purpose:** Simulate whole-body pharmacokinetics using a physiologically-based pharmacokinetic (PBPK) model.

#### Compartments (15 total)

| # | Compartment | Volume (L) | Blood Flow (% CO) | Notes |
|---|------------|-----------|-------------------|-------|
| 1 | Plasma | 3.0 | — | Central compartment |
| 2 | Lungs | 0.5 | 100% (series) | First-pass organ |
| 3 | Liver | 1.8 | 25% | Fenestrated capillaries, elimination |
| 4 | Kidney | 0.3 | 19% | Fenestrated, elimination |
| 5 | Spleen | 0.15 | 3% | Open sinusoids |
| 6 | Heart | 0.3 | 4% | HER2 expression site |
| 7 | Muscle | 28.0 | 17% | Background reference for TBR |
| 8 | Bone marrow | 1.5 | 5% | Sinusoidal, CD20 expression |
| 9 | Skin | 3.0 | 5% | — |
| 10 | Gut | 1.2 | 15% | Portal circulation |
| 11 | Brain | 1.4 | 12% | BBB-limited |
| 12 | Salivary glands | 0.04 | 0.5% | PSMA expression site |
| 13 | Bone | 4.0 | 2% | Cortical + trabecular |
| 14 | Rest of body | 10.0 | remainder | Catch-all |
| 15 | Tumor | variable | 2% | EPR effect, target-rich |

Reference body: ICRP Publication 89, adult male, 73 kg (ICRP, 2002).

#### ODE System

For each tissue compartment *t*:

```
V_t × dC_t/dt = Q_t × (C_p - C_t/Kp_t) - kon × C_t × (Ag_t - B_t) + koff × B_t
```

Bound agent:
```
dB_t/dt = kon × C_t × (Ag_t - B_t) - koff × B_t - k_int × B_t
```

Internalized agent:
```
dI_t/dt = k_int × B_t - k_deg × I_t
```

Plasma:
```
V_p × dC_p/dt = Σ_t Q_t × (C_t/Kp_t - C_p) - CL × C_p
```

Radioactive decay (applied to all states):
```
dy/dt -= λ × y    where λ = ln(2) / t½_physical
```

**Variables:**
- C_t: free tissue concentration (nM)
- C_p: plasma concentration (nM)
- B_t: bound agent concentration (nM)
- I_t: internalized agent (nM)
- Q_t: blood flow to tissue (L/h)
- V_t: tissue volume (L)
- Kp_t: tissue:plasma partition coefficient
- Ag_t: target density (nM)
- kon: association rate (nM⁻¹ h⁻¹, capped at 5.0 for numerical stability)
- koff: dissociation rate (h⁻¹)
- k_int: internalization rate (h⁻¹)
- k_deg: intracellular degradation rate (h⁻¹, default 0.1)
- CL: total systemic clearance (L/h)
- λ: radioactive decay constant (h⁻¹)

#### Solver

- **Primary:** SciPy `solve_ivp` with BDF method (for stiff systems)
  - Relative tolerance: 10⁻⁴
  - Absolute tolerance: 10⁻⁶
  - Max step: 5.0 h
- **Fallback:** Radau method (if BDF fails)
- Both are implicit methods suitable for stiff ODE systems common in PBPK

#### Monte Carlo Uncertainty Quantification

Parameters are perturbed with lognormal distributions:

| Parameter | CV (σ of lognormal) | Rationale |
|-----------|-------------------|-----------|
| Blood flows Q | 10% | Inter-individual variability (ICRP 89) |
| Volumes V | 7% | Anatomical variability |
| Partition coefficients Kp | 10% | Tissue composition uncertainty |
| Target densities Ag | 20% | Expression heterogeneity |
| Clearance CL | 15% | PK variability |
| Initial concentration | 5% | Dosing uncertainty |

Default: 100 MC samples (configurable). Results reported as median + 90% CI (5th-95th percentile).

#### Key Outputs

- Time-activity curves per compartment (free, bound, total)
- Tumor peak concentration (nM), tumor AUC
- Tumor-to-background ratio (TBR) using muscle as background
- Optimal imaging time (peak TBR)
- Plasma terminal half-life (log-linear regression on terminal phase)
- Biodistribution at optimal imaging time

### 3.5 Module 5 — Dosimetry Engine

**File:** `src/theranostics/services/dosimetry_engine_v1.py`

**Purpose:** Convert time-activity curves to absorbed radiation doses.

**Only computed for therapeutic isotopes** (Lu-177, Y-90, Ac-225, I-131). Returns `None` for diagnostic isotopes.

#### MIRD Formalism

```
D(organ) = Ã(organ) × S(organ ← organ)

where:
  Ã = ∫₀^∞ A(t) dt    (cumulated activity, time-integrated concentration)
  S = absorbed dose per unit cumulated activity (Gy/GBq·h)
```

The time integral is computed via trapezoidal integration of the PBPK time-activity curves.

#### S-values

Simplified from **OLINDA/EXM** (Stabin et al., 2005), assuming standard adult organ geometries.

| Organ | Lu-177 | Y-90 | Ac-225 | I-131 |
|-------|--------|------|--------|-------|
| Kidney | 1.10 | 2.20 | 8.50 | 0.85 |
| Liver | 0.14 | 0.28 | 1.10 | 0.11 |
| Salivary glands | 0.90 | 1.80 | 7.00 | 0.70 |
| Bone marrow | 0.11 | 0.22 | 0.85 | 0.09 |
| Tumor (~10 cm³) | 0.60 | 1.20 | 4.80 | 0.46 |
| Spleen | 0.78 | 1.55 | 6.00 | 0.60 |

Units: Gy/GBq·h. Full tables in source code.

#### Organ Dose Tolerances

From clinical guidelines and EBRT equivalences:

| Organ | Tolerance (Gy) | Source |
|-------|---------------|--------|
| Kidney | 23 | Bodei et al., 2008 (BED for PRRT) |
| Bone marrow | 2 | Sandström et al., 2013 |
| Liver | 30 | EBRT equivalent |
| Salivary glands | 25 | Estimated from xerostomia data |
| Lungs | 20 | EBRT equivalent |

#### Key Outputs

- Organ doses (Gy/GBq and total Gy)
- Dose-limiting organ (highest fraction of tolerance)
- Therapeutic index = tumor dose / dose-limiting organ dose
- Tumor-to-kidney dose ratio
- Residence times per organ

### 3.6 Module 6 — PD / Effect Engine

**File:** `src/theranostics/services/pd_engine.py`

**Purpose:** Estimate biological effect. V1 produces **directional, plausible** effects, not quantitative clinical predictions.

#### 3.6.1 Target Occupancy

Simple Emax model:

```
Occupancy = C_tumor / (C_tumor + Kd)
```

Where C_tumor is the peak tumor concentration from PBPK and Kd is the equilibrium dissociation constant. This is a standard receptor occupancy model (Clark, 1933; Hill, 1910).

#### 3.6.2 Radiotheranostic PD

For therapeutic isotopes, effect is dose-dependent:

| Isotope | Minimum Tumor Dose (Gy) | Strong Effect Dose (Gy) |
|---------|------------------------|------------------------|
| Lu-177 | 20 | 60 |
| Y-90 | 30 | 80 |
| Ac-225 | 5 | 15 |
| I-131 | 25 | 70 |

Ac-225 thresholds are lower because alpha particles have much higher linear energy transfer (LET ~100 keV/µm vs ~0.2 keV/µm for beta).

#### 3.6.3 Causal Rules

Target-specific biological effect rules:

| Target | Effect When Targeted | Mechanism |
|--------|---------------------|-----------|
| PSMA | Cytotoxic to PSMA+ cells | Receptor-mediated internalization delivers payload |
| SSTR2 | Cytotoxic to NET cells | SSTR2-mediated internalization of somatostatin analogs |
| HER2 | Antiproliferative + ADCC | Blocks dimerization → inhibits MAPK/PI3K signaling |
| FAP | Tumor stroma disruption | Targets CAFs, may enhance immune infiltration |
| CD20 | B-cell depletion | CDC + ADCC + direct apoptosis |

#### 3.6.4 Off-Target Toxicity Rules

| Target | Organ | Toxicity |
|--------|-------|----------|
| PSMA | Kidney | Nephrotoxicity (PSMA in proximal tubule) |
| PSMA | Salivary glands | Xerostomia |
| HER2 | Heart | Cardiotoxicity (HER2 in cardiomyocytes) |
| CD20 | Bone marrow | Myelosuppression (normal B-cell depletion) |
| CD20 | Spleen | B-cell depletion |

### 3.7 Module 7 — Decision Engine

**File:** `src/theranostics/services/decision_engine_v1.py`

**Purpose:** Score, rank, and explain strategy recommendations.

#### Scoring Formula

```
Combined = w_eff × Efficacy + w_saf × Safety + w_prac × Practicality + w_conf × Confidence
```

Default weights:

| Component | Weight | Sub-components |
|-----------|--------|---------------|
| Efficacy | 0.40 | Tumor uptake (0.30) + TBR (0.25) + Target engagement (0.25) + Penetration (0.20) |
| Safety | 0.30 | Organ safety (off-target penalty) + Dosimetry safety |
| Practicality | 0.15 | Isotope availability + Imaging feasibility |
| Confidence | 0.15 | Evidence level (0.40) + Data quality (0.30) + MC stability (0.30) |

All sub-scores are [0, 1]. Weights are configurable and always logged.

#### Isotope Availability Scores

| Isotope | Score | Rationale |
|---------|-------|-----------|
| Ga-68 | 0.9 | Generator-produced, widely available |
| F-18 | 0.9 | Cyclotron, widespread PET infrastructure |
| Lu-177 | 0.8 | Reactor-produced, good supply chain |
| I-131 | 0.8 | Well-established production |
| Y-90 | 0.7 | Available but declining use |
| Zr-89 | 0.5 | Cyclotron, limited sites |
| Ac-225 | 0.3 | Very limited global supply |

---

## 4. Mathematical Models

### 4.1 PBPK Model

The model follows standard well-stirred compartmental PBPK theory as described in:
- **Nestorov (2003)** — Whole-body PBPK models. *Clinical Pharmacokinetics*, 42(10), 883-908.
- **Shah & Betts (2012)** — Towards a platform PBPK model for monoclonal antibodies. *J Pharmacokinet Pharmacodyn*, 39(5), 443-459.

Key assumptions:
- Each tissue is well-stirred (instant mixing within compartment)
- Blood flow-limited distribution (no membrane barrier except BBB)
- Linear clearance (no saturation in V1)
- Target-mediated binding follows mass-action kinetics

### 4.2 Binding Kinetics

Standard bimolecular binding:
```
Agent + Target ⇌ Agent:Target → Internalized → Degraded
         kon/koff      k_int          k_deg
```

Equilibrium: Kd = koff / kon (in consistent units)

### 4.3 Thurber Tumor Penetration Model

Adapted from **Thurber, Schmidt & Wittrup (2008)** — Antibody tumor penetration: Transport opposed by binding and clearance. *Advanced Drug Delivery Reviews*, 60(12), 1421-1434.

The Thiele modulus quantifies the ratio of binding rate to diffusion rate:
```
φ = R_Krogh × √(kon × [Ag] / D)
```

When φ >> 1: binding site barrier — agent is consumed at the tumor periphery before reaching the center.

### 4.4 Dosimetry (MIRD)

Based on the **MIRD** (Medical Internal Radiation Dose) formalism:
- **Bolch et al. (2009)** — MIRD Pamphlet No. 21. *J Nucl Med*, 50(3), 477-484.
- **Stabin, Sparks & Crowe (2005)** — OLINDA/EXM: the second-generation personal computer software for internal dose assessment. *J Nucl Med*, 46(6), 1023-1027.

### 4.5 Target Occupancy

Simple Hill equation (n=1):
```
Occupancy = [L] / ([L] + Kd)
```

This is a standard pharmacological model (Clark, 1933). In V1, only receptor occupancy is modeled (no downstream signaling).

---

## 5. External Data Sources

### 5.1 Open Targets Platform

**File:** `src/theranostics/integrations/open_targets.py`

**API:** GraphQL endpoint at `https://api.platform.opentargets.org/api/v4/graphql`

**Data retrieved:**
- Target-disease association scores (overall + per datatype)
- Disease metadata (name, EFO ID)
- Target tractability information

**Gene ID mapping:**
| Target | Ensembl ID | Gene |
|--------|-----------|------|
| PSMA | ENSG00000086205 | FOLH1 |
| SSTR2 | ENSG00000180616 | SSTR2 |
| HER2 | ENSG00000141736 | ERBB2 |
| FAP | ENSG00000078098 | FAP |
| CD20 | ENSG00000156738 | MS4A1 |

**Reference:** Ochoa et al. (2023). The next-generation Open Targets Platform. *Nucleic Acids Research*, 51(D1), D1353-D1359.

### 5.2 Human Protein Atlas (HPA)

**File:** `src/theranostics/integrations/human_protein_atlas.py`

**API:** REST endpoint at `https://www.proteinatlas.org/{GENE}.json`

**Data retrieved:**
- Tissue-level protein expression (immunohistochemistry-based)
- Expression levels: Not detected (0.0), Low (0.15), Medium (0.45), High (0.85)

**Tissue mapping:** HPA tissue names (e.g., "kidney", "heart muscle", "salivary gland") are mapped to our compartment names.

**Reference:** Uhlén et al. (2015). Tissue-based map of the human proteome. *Science*, 347(6220), 1260419.

### 5.3 UniProt

**File:** `src/theranostics/integrations/uniprot.py`

**API:** REST endpoint at `https://rest.uniprot.org/uniprotkb/{ACCESSION}.json`

**Data retrieved:**
- Protein name and function
- Subcellular localization (cell surface, transmembrane)
- Presence of extracellular domain (relevant for accessibility)
- Molecular weight

**UniProt accessions:**
| Target | Accession | Entry Name |
|--------|----------|-----------|
| PSMA | Q04609 | FOLH1_HUMAN |
| SSTR2 | P30874 | SSR2_HUMAN |
| HER2 | P04626 | ERBB2_HUMAN |
| FAP | Q12884 | SEPC_HUMAN |
| CD20 | P11836 | CD20_HUMAN |

**Reference:** The UniProt Consortium (2023). UniProt: the Universal Protein Knowledgebase. *Nucleic Acids Research*, 51(D1), D523-D531.

### 5.4 Caching Strategy

All API responses are cached locally as JSON files in `data/cache/{source}/{key}.json`. Cache is:
- File-based (no database required)
- Per-query granularity
- Never auto-expired in V1 (manual invalidation)
- Logged on read (cache hit) and write

---

## 6. Curated Knowledge Base

When APIs are unavailable or for baseline data, the platform uses internal curated tables.

### 6.1 Normal Tissue Expression (score [0, 1])

| Tissue | PSMA | SSTR2 | HER2 | FAP | CD20 |
|--------|------|-------|------|-----|------|
| Kidney | 0.62 | 0.25 | 0.15 | 0.05 | 0.03 |
| Salivary glands | 0.58 | 0.05 | 0.05 | 0.02 | 0.02 |
| Liver | 0.10 | 0.12 | 0.20 | 0.05 | 0.10 |
| Spleen | 0.08 | 0.55 | 0.08 | 0.03 | 0.80 |
| Bone marrow | 0.05 | 0.05 | 0.08 | 0.03 | 0.60 |
| Heart | 0.03 | 0.03 | 0.35 | 0.03 | 0.01 |
| Gut | 0.20 | 0.20 | 0.30 | 0.05 | 0.10 |
| Brain | 0.02 | 0.15 | 0.05 | 0.01 | 0.01 |
| Muscle | 0.03 | 0.03 | 0.05 | 0.03 | 0.01 |

Sources: Human Protein Atlas, published literature (see references section).

### 6.2 Target Properties

| Property | PSMA | SSTR2 | HER2 | FAP | CD20 |
|----------|------|-------|------|-----|------|
| Location | Cell surface | Cell surface | Cell surface | Cell surface | Cell surface |
| Internalization | Yes (high) | Yes (high) | Yes (moderate) | Yes (moderate) | No (very low) |
| Shedding risk | 0.05 | 0.00 | 0.20 | 0.10 | 0.00 |
| Typical tumor expression | 0.90 | 0.85 | 0.85 | 0.70 | 0.90 |

### 6.3 Agent Class Defaults

| Parameter | Small mol. | Peptide | Nanobody | Fab | IgG |
|-----------|-----------|---------|----------|-----|-----|
| Size (kDa) | 0.8 | 1.5 | 15 | 50 | 150 |
| Kd (nM) | 5.0 | 2.0 | 5.0 | 1.0 | 1.0 |
| kon (M⁻¹s⁻¹) | 10⁶ | 8×10⁵ | 5×10⁵ | 2×10⁵ | 1.5×10⁵ |
| Half-life (h) | 4 | 2 | 3 | 15 | 450 |
| Renal fraction | 0.60 | 0.65 | 0.80 | 0.40 | 0.00 |
| Hepatic fraction | 0.20 | 0.15 | 0.10 | 0.20 | 0.30 |
| Fc region | No | No | No | No | Yes |
| Vasc. perm. (cm/s) | 10⁻⁵ | 10⁻⁵ | 5×10⁻⁷ | 10⁻⁷ | 3×10⁻⁸ |

---

## 7. Isotope & Dosimetry Data

### 7.1 Isotope Library

| Isotope | Half-life | Type | Emission | Energy (keV) |
|---------|-----------|------|----------|-------------|
| Ga-68 | 1.13 h | Diagnostic | β⁺ | 1899 |
| F-18 | 1.83 h | Diagnostic | β⁺ | 634 |
| Zr-89 | 78.4 h | Diagnostic | β⁺ | 909 |
| Lu-177 | 159.5 h | Therapeutic | β⁻ | 497 |
| Y-90 | 64.1 h | Therapeutic | β⁻ | 2280 |
| I-131 | 192.5 h | Therapeutic | β⁻ | 606 |
| Ac-225 | 240 h | Therapeutic | α | 5830 |

### 7.2 Common Theranostic Pairs

| Diagnostic | Therapeutic | Target | Reference |
|-----------|-------------|--------|-----------|
| ⁶⁸Ga-PSMA-11 | ¹⁷⁷Lu-PSMA-617 | PSMA | Sartor et al., 2021 (VISION trial) |
| ⁶⁸Ga-DOTATATE | ¹⁷⁷Lu-DOTATATE | SSTR2 | Strosberg et al., 2017 (NETTER-1) |
| ⁸⁹Zr-Trastuzumab | ¹⁷⁷Lu-Trastuzumab | HER2 | Dijkers et al., 2010 |
| ⁶⁸Ga-FAPI-46 | ¹⁷⁷Lu-FAP-2286 | FAP | Ballal et al., 2021 |

---

## 8. Confidence & Uncertainty

### 8.1 Per-Module Confidence Scores

Each module produces its own confidence score [0, 1]:

| Module | Score Basis |
|--------|-----------|
| Knowledge | Number of sources queried, data conflicts, evidence level |
| Parameters | Fraction of parameters from data vs defaults |
| PBPK | MC success rate × 0.8 |
| Dosimetry | Fixed 0.65 (S-value uncertainty) |
| PD | Causal rule availability + binding confidence |
| Decision | Evidence level (0.4) + data quality (0.3) + MC stability (0.3) |

### 8.2 No Opaque Global Score

The platform never produces a single opaque confidence number. The per-module breakdown is always visible in the output and in the frontend "Confidence per Module" panel.

---

## 9. File Structure

```
therapredict/
├── src/theranostics/
│   ├── api/
│   │   ├── main.py                    # FastAPI app (V1 + legacy routes)
│   │   └── routes/
│   │       ├── simulate.py            # Legacy simulation endpoints
│   │       ├── simulate_v1.py         # V1 pipeline endpoints
│   │       └── agents.py              # Agent/target catalog
│   ├── services/                      # V1 pipeline modules
│   │   ├── logging_service.py         # Module 0: Structured JSONL logging
│   │   ├── input_normalizer.py        # Module 1: Input validation & defaults
│   │   ├── knowledge_layer.py         # Module 2: External + curated knowledge
│   │   ├── parameter_builder.py       # Module 3: Rules → parameters
│   │   ├── pbpk_engine_v1.py          # Module 4: ODE-based PBPK solver
│   │   ├── dosimetry_engine_v1.py     # Module 5: MIRD dosimetry
│   │   ├── pd_engine.py              # Module 6: PD / biological effect
│   │   └── decision_engine_v1.py      # Module 7: Transparent scoring
│   ├── integrations/                  # External API clients
│   │   ├── open_targets.py            # Open Targets GraphQL
│   │   ├── human_protein_atlas.py     # HPA REST API
│   │   └── uniprot.py                 # UniProt REST API
│   ├── engines/                       # Legacy engines (still functional)
│   ├── models/                        # Pydantic data models
│   ├── orchestrator.py                # Legacy orchestrator
│   ├── orchestrator_v1.py             # V1 pipeline orchestrator
│   └── config.py                      # Global configuration
├── frontend/
│   └── src/
│       ├── App.jsx                    # Main app (V1 interface)
│       └── components/
│           ├── V1SimulationForm.jsx    # V1 input form with presets
│           ├── V1ResultsDashboard.jsx  # 6-tab results (Results/PK/Dosimetry/Effect/Logs/Sources)
│           └── BodyDiagram.jsx         # SVG anatomical heatmap
├── tests/
│   ├── test_v1_pipeline.py            # 64 unit tests (all 7 modules)
│   ├── benchmark/
│   │   └── test_v1_benchmark.py       # 33 benchmark tests (PSMA, SSTR2, HER2)
│   └── validation/
│       └── test_trastuzumab_pk.py     # Clinical validation
├── data/
│   ├── cache/                         # API response cache (auto-populated)
│   ├── curated/                       # Curated reference data
│   ├── benchmarks/                    # Benchmark reference values
│   └── defaults/                      # Default parameter tables
├── logs/                              # JSONL pipeline logs (per request_id)
├── TECHNICAL_REFERENCE_V1.md          # This file
└── PLATFORM_ARCHITECTURE.md           # Original architecture vision
```

---

## 10. Running the Platform

### Prerequisites

```bash
pip install numpy scipy pandas pydantic fastapi uvicorn httpx
cd frontend && npm install
```

### Start Backend

```bash
PYTHONPATH=src python3 -m uvicorn theranostics.api.main:app --reload --port 8000
```

### Start Frontend

```bash
cd frontend && npm run dev
```

### Access

- **Frontend:** http://localhost:5173
- **API docs (Swagger):** http://localhost:8000/docs
- **API V1 endpoints:**
  - `POST /api/v1/simulate` — Run simulation (with external APIs)
  - `POST /api/v1/simulate/offline` — Run simulation (curated data only)
  - `POST /api/v1/compare` — Compare 2-10 strategies
  - `GET /api/v1/targets` — List supported targets
  - `GET /api/v1/isotopes` — List supported isotopes
  - `GET /api/v1/agent-classes` — List agent class defaults

### Example API Call

```bash
curl -X POST http://localhost:8000/api/v1/simulate/offline \
  -H "Content-Type: application/json" \
  -d '{
    "target": "PSMA",
    "agent": {
      "name": "PSMA-617",
      "class": "small_molecule",
      "size_kDa": 1.0,
      "kd_nM": 2.3,
      "isotope": "Lu-177",
      "internalization": true
    },
    "dose": { "activity_GBq": 7.4 },
    "tumor": { "type": "prostate", "volume_ml": 50 }
  }'
```

---

## 11. Testing & Benchmarks

### Run All Tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

**128 tests total:**
- 64 unit tests (`test_v1_pipeline.py`)
- 33 benchmark tests (`benchmark/test_v1_benchmark.py`)
- 31 legacy tests

### Benchmark Cases

#### PSMA Benchmark (prostate cancer, PSMA-617, Lu-177)

| Check | Expected | Status |
|-------|----------|--------|
| Clearance route | Renal (MW < 60 kDa) | Validated |
| Off-target organs | Kidney, salivary glands | Validated |
| Dosimetry | Present (therapeutic isotope) | Validated |
| Effect direction | Cytotoxic | Validated |
| Effect type | Radiotheranostic | Validated |

#### SSTR2 Benchmark (NET, DOTATATE, Lu-177)

| Check | Expected | Status |
|-------|----------|--------|
| Clearance route | Renal (peptide) | Validated |
| Off-target organs | Spleen (SSTR2), kidney | Validated |
| Dosimetry | Present | Validated |
| Dose-limiting organ | Identified | Validated |
| Effect direction | Cytotoxic | Validated |

#### HER2 Benchmark (breast cancer, Trastuzumab, Zr-89)

| Check | Expected | Status |
|-------|----------|--------|
| Clearance route | Hepatic (IgG > 60 kDa) | Validated |
| Off-target organs | Liver (Fc region) | Validated |
| Dosimetry | Absent (diagnostic isotope) | Validated |
| BBB permeability | Very low (0.001) | Validated |
| Binding site barrier | Present (IgG + high Kd) | Validated |
| Penetration | Lower than small molecule | Validated |

### Anti-leakage Policy

The pipeline never injects expected outcomes into input data:
- Expression scores come from the Knowledge Layer, not from expected biodistribution
- Off-target organs are derived from expression × exposure, not from ground truth
- Dosimetry is computed from PBPK curves, not from reference doses

---

## 12. Scientific References

### PBPK Modeling

1. **Nestorov I.** (2003). Whole body pharmacokinetic models. *Clinical Pharmacokinetics*, 42(10), 883-908.

2. **Shah DK, Betts AM.** (2012). Towards a platform PBPK model to characterize the plasma and tissue disposition of monoclonal antibodies in preclinical species and human. *J Pharmacokinet Pharmacodyn*, 39(5), 443-459.

3. **ICRP Publication 89.** (2002). Basic anatomical and physiological data for use in radiological protection: reference values. *Annals of the ICRP*, 32(3-4).

### Tumor Penetration & Binding Site Barrier

4. **Thurber GM, Schmidt MM, Wittrup KD.** (2008). Antibody tumor penetration: Transport opposed by binding and clearance. *Advanced Drug Delivery Reviews*, 60(12), 1421-1434.

5. **Thurber GM, Wittrup KD.** (2012). Quantitative spatiotemporal analysis of antibody fragment diffusion and endocytic consumption in tumor spheroids. *Cancer Research*, 72(13), 3448-3458.

### FcRn & Antibody PK

6. **Roopenian DC, Akilesh S.** (2007). FcRn: the neonatal Fc receptor comes of age. *Nature Reviews Immunology*, 7(9), 715-725.

### Dosimetry

7. **Stabin MG, Sparks RB, Crowe E.** (2005). OLINDA/EXM: the second-generation personal computer software for internal dose assessment in nuclear medicine. *J Nucl Med*, 46(6), 1023-1027.

8. **Bolch WE, Eckerman KF, Sgouros G, Thomas SR.** (2009). MIRD Pamphlet No. 21: A generalized schema for radiopharmaceutical dosimetry. *J Nucl Med*, 50(3), 477-484.

9. **Bodei L, Cremonesi M, Ferrari M, et al.** (2008). Long-term evaluation of renal toxicity after peptide receptor radionuclide therapy with ⁹⁰Y-DOTATOC and ¹⁷⁷Lu-DOTATATE. *Eur J Nucl Med Mol Imaging*, 35(10), 1847-1856.

10. **Sandström M, Freedman N, Fröss-Baron K, et al.** (2013). Kidney dosimetry in 777 patients during ¹⁷⁷Lu-DOTATATE therapy. *Eur J Nucl Med Mol Imaging*, 40(Suppl 1), 146.

### Theranostic Clinical Trials

11. **Sartor O, de Bono J, Chi KN, et al.** (2021). Lutetium-177–PSMA-617 for metastatic castration-resistant prostate cancer. *New England Journal of Medicine*, 385(12), 1091-1103. (VISION trial)

12. **Strosberg J, El-Haddad G, Wolin E, et al.** (2017). Phase 3 trial of ¹⁷⁷Lu-DOTATATE for midgut neuroendocrine tumors. *New England Journal of Medicine*, 376(2), 125-135. (NETTER-1 trial)

13. **Dijkers EC, Oude Munnink TH, Kosterink JG, et al.** (2010). Biodistribution of ⁸⁹Zr-trastuzumab and PET imaging of HER2-positive lesions in patients with metastatic breast cancer. *Clin Pharmacol Ther*, 87(5), 586-592.

14. **Ballal S, Yadav MP, Moon ES, et al.** (2021). Biodistribution, pharmacokinetics, dosimetry of [⁶⁸Ga]Ga-DOTA.SA.FAPi, and the manufacturing feasibility of intense therapeutic doses of [¹⁷⁷Lu]Lu-DOTA.SA.FAPi for various cancers. *Sci Rep*, 11, 3809.

### Data Sources

15. **Ochoa D, Hercules A, Mouber BM, et al.** (2023). The next-generation Open Targets Platform: reimagined, redesigned, rebuilt. *Nucleic Acids Research*, 51(D1), D1353-D1359.

16. **Uhlén M, Fagerberg L, Hallström BM, et al.** (2015). Tissue-based map of the human proteome. *Science*, 347(6220), 1260419.

17. **The UniProt Consortium.** (2023). UniProt: the Universal Protein Knowledgebase in 2023. *Nucleic Acids Research*, 51(D1), D523-D531.

### Pharmacology Fundamentals

18. **Clark AJ.** (1933). *The Mode of Action of Drugs on Cells*. Edward Arnold, London.

19. **Hill AV.** (1910). The possible effects of the aggregation of the molecules of haemoglobin on its dissociation curves. *J Physiol*, 40, iv-vii.

---

*Document version: 1.0.0 — Generated alongside TheraPredict V1 implementation.*
*For the original platform vision and roadmap, see `PLATFORM_ARCHITECTURE.md`.*
