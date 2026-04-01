# AI-Driven Digital Theranostic Simulation Platform
## Full Technical Architecture, Product Strategy & Roadmap

---

# 1. SYSTEM ARCHITECTURE

## 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Web UI   │  │ API Gateway  │  │ CLI Tools │  │ Notebook SDK │  │
│  └──────────┘  └──────────────┘  └───────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                      ORCHESTRATION LAYER                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Simulation Orchestrator (DAG-based)              │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────┐  │  │
│  │  │ Config  │ │ Scenario │ │ Pipeline │ │ Result Aggregator│  │  │
│  │  │ Manager │ │ Builder  │ │ Runner   │ │                  │  │  │
│  │  └─────────┘ └──────────┘ └──────────┘ └─────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                       SIMULATION ENGINES                           │
│                                                                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐  │
│  │  TARGET    │ │   AGENT    │ │   BODY     │ │    PK/PD       │  │
│  │  ENGINE    │ │ SIMULATION │ │ SIMULATION │ │    ENGINE       │  │
│  │            │ │  ENGINE    │ │  ENGINE    │ │                 │  │
│  │ - Scoring  │ │ - Affinity │ │ - Compart- │ │ - PBPK solver  │  │
│  │ - Access.  │ │ - Design   │ │   mental   │ │ - Time series  │  │
│  │ - Relevance│ │ - Clearance│ │ - Flow     │ │ - Dose-response│  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────────┘  │
│                                                                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────────────────────────┐  │
│  │  IMAGING   │ │  PATIENT   │ │       DECISION ENGINE          │  │
│  │ CALIBRATION│ │ SIMILARITY │ │                                 │  │
│  │  LAYER     │ │  ENGINE    │ │  - Candidate ranking            │  │
│  │            │ │            │ │  - Strategy optimization        │  │
│  │ - PET/CT   │ │ - Embedding│ │  - Explanation generation       │  │
│  │ - SUV map  │ │ - Clustering│ │  - Confidence intervals       │  │
│  │ - Calibrate│ │ - KNN      │ │                                 │  │
│  └────────────┘ └────────────┘ └────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                         DATA LAYER                                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Patient  │  │ Imaging Store│  │ Model     │  │ Simulation   │  │
│  │ Registry │  │ (DICOM/NIfTI)│  │ Registry  │  │ Results DB   │  │
│  └──────────┘  └──────────────┘  └───────────┘  └──────────────┘  │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │ Target   │  │ Agent        │  │ Calibration / Ground Truth   │  │
│  │ Knowledge│  │ Library      │  │ Store                        │  │
│  │ Graph    │  │              │  │                               │  │
│  └──────────┘  └──────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 1.2 Design Principles

1. **Modularity**: Each engine is independently deployable, testable, and replaceable
2. **Progressive fidelity**: Start with coarse models, refine with data
3. **Hybrid inference**: Every prediction combines mechanistic + statistical + learned components
4. **Calibration-first**: Every output includes uncertainty quantification
5. **Reproducibility**: Every simulation run is versioned and reproducible

## 1.3 Inter-Module Communication

Engines communicate via a **typed message bus** using structured simulation contexts:

```python
@dataclass
class SimulationContext:
    patient: PatientProfile          # demographics, clinical data
    target: TargetAssessment         # from Target Engine
    agent: AgentProperties           # from Agent Simulation Engine
    body_model: BodyModelState       # from Body Simulation Engine
    pk_profile: PKProfile            # from PK/PD Engine
    imaging_calibration: Optional[CalibrationResult]
    similar_patients: List[PatientMatch]
    metadata: SimulationMetadata     # run ID, version, params
```

---

# 2. DETAILED MODULE SPECIFICATIONS

## 2.1 Target Engine

### Purpose
Assess the theranostic relevance of a molecular target for a given patient or patient cohort.

### Architecture

```
┌─────────────────────────────────────────────┐
│               TARGET ENGINE                  │
│                                              │
│  INPUT                                       │
│  ├── Target ID (e.g., HER2, PSMA, CD20)     │
│  ├── Tumor type                              │
│  ├── Optional: mutation panel / RNA-seq      │
│  ├── Optional: IHC/FISH scores               │
│  │                                           │
│  PROCESSING                                  │
│  ├── 1. Knowledge Graph Lookup               │
│  │   ├── Expression frequency by tumor type  │
│  │   ├── Known theranostic agents            │
│  │   └── Clinical evidence level             │
│  │                                           │
│  ├── 2. Expression Score Model               │
│  │   ├── Population-level: literature prior   │
│  │   ├── Cohort-level: dataset statistics     │
│  │   └── Patient-level: if molecular data     │
│  │                                            │
│  ├── 3. Accessibility Model                   │
│  │   ├── Surface vs intracellular             │
│  │   ├── Shedding risk                        │
│  │   ├── Tumor microenvironment factors       │
│  │   └── Vascularization estimate             │
│  │                                            │
│  ├── 4. Theranostic Relevance Scorer          │
│  │   ├── Can it be imaged? (diagnostic)       │
│  │   ├── Can it be treated? (therapeutic)     │
│  │   └── Combined theranostic score           │
│  │                                            │
│  OUTPUT                                       │
│  ├── target_score: float [0, 1]               │
│  ├── accessibility_likelihood: float [0, 1]   │
│  ├── theranostic_relevance: {diag, ther, combined} │
│  ├── confidence_interval: (low, high)         │
│  ├── evidence_level: str (A/B/C/D)           │
│  └── similar_indications: List[Indication]    │
└───────────────────────────────────────────────┘
```

### Implementation Details

**Knowledge Graph**: Built from curated sources:
- UniProt (protein data)
- The Human Protein Atlas (expression data)
- ClinicalTrials.gov (theranostic evidence)
- DrugBank (approved agents)
- Custom curation of theranostic literature

**Expression Score Model** (Bayesian approach):
```python
class ExpressionScorer:
    """
    Hierarchical Bayesian model:
    - Prior: population-level expression frequency from literature
    - Likelihood: patient-specific molecular data if available
    - Posterior: calibrated expression probability
    """
    def score(self, target_id: str, tumor_type: str,
              patient_data: Optional[MolecularProfile] = None) -> ExpressionScore:
        prior = self.knowledge_graph.get_expression_prior(target_id, tumor_type)
        if patient_data:
            likelihood = self.molecular_model.compute_likelihood(
                target_id, patient_data
            )
            posterior = self.bayesian_update(prior, likelihood)
        else:
            posterior = prior
        return ExpressionScore(
            mean=posterior.mean,
            ci_low=posterior.quantile(0.05),
            ci_high=posterior.quantile(0.95),
            data_source="patient" if patient_data else "population"
        )
```

**Accessibility Model**: Rule-based + learned hybrid:
- Rule-based component: known membrane topology, glycosylation sites, steric factors
- ML component: random forest trained on structural features vs. binding success rates from published antibody data

### Data Requirements (MVP)
- Curated table of ~50 common theranostic targets with expression frequencies per tumor type
- Human Protein Atlas bulk downloads (free, publicly available)
- ~200 rows of target-agent-outcome data from literature

### Limitations (Scientific Honesty)
- Population-level priors are averages; individual patient expression can deviate significantly
- Accessibility modeling is approximate — actual tumor penetration depends on many unmeasured factors
- Without patient-specific molecular data, the engine provides population-level estimates only

---

## 2.2 Agent Simulation Engine

### Purpose
Model the pharmacological and physical properties of candidate theranostic agents and predict their in-vivo behavior characteristics.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│            AGENT SIMULATION ENGINE                    │
│                                                       │
│  INPUT                                                │
│  ├── Agent type: {antibody, Fab, scFv, nanobody,     │
│  │               small_molecule, peptide, mRNA_LNP}  │
│  ├── Target: from Target Engine                       │
│  ├── Optional: sequence / structure                   │
│  ├── Isotope (if radiotracer): 68Ga, 177Lu, 225Ac... │
│  │                                                    │
│  AGENT PROPERTY MODELS                                │
│  │                                                    │
│  ├── 1. Molecular Weight & Size Estimator             │
│  │   ├── IgG: ~150 kDa, ~10 nm                       │
│  │   ├── Fab: ~50 kDa, ~6 nm                         │
│  │   ├── Nanobody: ~15 kDa, ~3 nm                    │
│  │   └── Small molecule: <1 kDa, <1 nm               │
│  │                                                    │
│  ├── 2. Binding Affinity Predictor                    │
│  │   ├── If known Kd: use directly                    │
│  │   ├── If structure available: docking score → Kd   │
│  │   └── If class only: use class median + range      │
│  │                                                    │
│  ├── 3. Clearance Model                               │
│  │   ├── Renal (size-dependent, <60 kDa filtered)     │
│  │   ├── Hepatic (FcRn-mediated recycling for IgG)    │
│  │   ├── Target-mediated drug disposition (TMDD)       │
│  │   └── Radioactive decay (isotope-specific)          │
│  │                                                    │
│  ├── 4. Tumor Penetration Predictor                   │
│  │   ├── Size → extravasation rate                     │
│  │   ├── Affinity → binding site barrier               │
│  │   ├── Charge / hydrophobicity effects               │
│  │   └── Output: penetration depth estimate (mm)       │
│  │                                                    │
│  ├── 5. Off-Target Binding Model                      │
│  │   ├── Known cross-reactivity database               │
│  │   ├── Tissue expression of target in normal organs  │
│  │   └── Predicted off-target accumulation sites       │
│  │                                                    │
│  OUTPUT                                               │
│  ├── agent_profile: AgentProperties                    │
│  │   ├── molecular_weight: float (kDa)                │
│  │   ├── hydrodynamic_radius: float (nm)              │
│  │   ├── binding_affinity_Kd: float (nM)              │
│  │   ├── plasma_half_life: float (hours)              │
│  │   ├── clearance_route: str                         │
│  │   ├── tumor_penetration_score: float [0,1]         │
│  │   └── off_target_risk: Dict[str, float]            │
│  ├── uncertainty: AgentUncertainty                     │
│  └── data_sources: List[str]                          │
└───────────────────────────────────────────────────────┘
```

### Key Models

**Clearance Model** — Multi-compartment, semi-mechanistic:
```python
class ClearanceModel:
    """
    Combines allometric scaling with agent-specific modifiers.
    Uses the 2-compartment model as baseline with corrections.
    """
    def predict_half_life(self, agent: AgentProperties) -> HalfLifeEstimate:
        # Base: allometric scaling from MW
        base_t_half = self.allometric_scale(agent.molecular_weight)

        # Modifier: FcRn recycling (IgG-like agents have longer t½)
        if agent.has_fc_region:
            base_t_half *= self.fcrn_recycling_factor(agent.fc_affinity)

        # Modifier: TMDD (high-expression targets accelerate clearance)
        tmdd_factor = self.tmdd_correction(
            agent.binding_affinity,
            agent.target_expression_level,
            agent.target_internalization_rate
        )
        base_t_half *= tmdd_factor

        # Modifier: Anti-drug antibody risk (approximate)
        ada_risk = self.ada_risk_model(agent.humanization_score)

        return HalfLifeEstimate(
            central=base_t_half,
            range=(base_t_half * 0.5, base_t_half * 2.0),  # broad uncertainty
            ada_adjusted=base_t_half * (1 - ada_risk * 0.3),
            confidence="low" if not agent.has_clinical_data else "moderate"
        )
```

**Tumor Penetration Model** — Physics-informed:
```python
class TumorPenetrationModel:
    """
    Based on Thurber-Schmidt-Wittrup model of antibody penetration.
    Balances extravasation, diffusion, binding, and clearance.

    Key insight: higher affinity ≠ better penetration (binding site barrier).
    """
    def predict_penetration(self, agent: AgentProperties,
                            tumor: TumorProperties) -> PenetrationResult:
        # Krogh cylinder model parameters
        R_krogh = tumor.avg_intercapillary_distance / 2  # ~75-200 μm
        P = self.permeability(agent.hydrodynamic_radius)  # vascular permeability
        D = self.diffusivity(agent.hydrodynamic_radius)   # interstitial diffusion
        kon = agent.binding_on_rate
        Ag = tumor.antigen_density

        # Thiele modulus: reaction vs diffusion
        phi = R_krogh * np.sqrt(kon * Ag / D)

        # Penetration depth
        penetration_depth = R_krogh / phi if phi > 1 else R_krogh

        return PenetrationResult(
            depth_um=penetration_depth * 1e6,
            uniformity_score=1.0 / (1.0 + phi),
            binding_site_barrier_risk=phi > 3.0,
            recommendation=self._recommend(phi, agent.type)
        )
```

### Agent Library (Pre-built for MVP)
| Agent Class | Example | MW (kDa) | t½ (h) | Penetration |
|---|---|---|---|---|
| Full IgG | Trastuzumab | 148 | 480-600 | Low-moderate |
| Fab fragment | — | 50 | 12-20 | Moderate |
| Nanobody | — | 15 | 2-4 | High |
| Small molecule | PSMA-617 | 1.0 | 2-6 | Very high |
| Peptide | DOTATATE | 1.4 | 1-3 | Very high |

### Limitations
- Binding affinity prediction without structure is highly uncertain (order-of-magnitude estimates)
- Tumor penetration model assumes idealized geometry; real tumors are heterogeneous
- Off-target binding prediction is incomplete — only covers known expression patterns

---

## 2.3 Body Simulation Engine (CRITICAL MODULE)

### Purpose
Simulate the whole-body distribution, circulation, and accumulation of theranostic agents using a multi-agent, compartmental approach.

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   BODY SIMULATION ENGINE                          │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              COMPARTMENTAL BODY MODEL                       │  │
│  │                                                              │  │
│  │          ┌──────────┐                                        │  │
│  │          │  LUNGS   │←─────────────┐                        │  │
│  │          └────┬─────┘              │                        │  │
│  │               │ (cardiac output)   │                        │  │
│  │     ┌─────────┼─────────┐          │                        │  │
│  │     ▼         ▼         ▼          │                        │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐       │                        │  │
│  │  │LIVER │ │KIDNEY│ │SPLEEN│       │                        │  │
│  │  └──┬───┘ └──┬───┘ └──┬───┘       │                        │  │
│  │     │        │        │            │                        │  │
│  │     ▼        ▼        │      ┌─────┤                        │  │
│  │  ┌──────┐ ┌──────┐   │      │VENOUS│                       │  │
│  │  │ GUT  │ │BLADDER│   │      │BLOOD │                       │  │
│  │  └──────┘ └──────┘   │      └──┬───┘                       │  │
│  │                       │         │                            │  │
│  │     ┌─────────────────┘   ┌─────┘                           │  │
│  │     ▼                     ▼                                  │  │
│  │  ┌──────┐ ┌──────┐ ┌───────┐ ┌──────┐ ┌──────┐            │  │
│  │  │BONE  │ │MUSCLE│ │ TUMOR │ │HEART │ │BRAIN │            │  │
│  │  │MARROW│ │      │ │(1..N) │ │      │ │      │            │  │
│  │  └──────┘ └──────┘ └───────┘ └──────┘ └──────┘            │  │
│  │                                                              │  │
│  │  Each compartment has:                                       │  │
│  │  - Volume (L)                                                │  │
│  │  - Blood flow fraction (% cardiac output)                    │  │
│  │  - Vascular volume fraction                                  │  │
│  │  - Interstitial volume fraction                              │  │
│  │  - Cell surface target density (if applicable)               │  │
│  │  - Endosomal uptake rate                                     │  │
│  │  - Lymphatic drainage rate                                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              MULTI-AGENT SIMULATION LAYER                    │  │
│  │                                                              │  │
│  │  Agents (molecules) are tracked as populations per           │  │
│  │  compartment with stochastic transitions:                    │  │
│  │                                                              │  │
│  │  States per compartment:                                     │  │
│  │  ├── Free in vascular space                                  │  │
│  │  ├── Free in interstitial space (extravasated)               │  │
│  │  ├── Bound to target (specific)                              │  │
│  │  ├── Bound non-specifically (FcγR, etc.)                     │  │
│  │  ├── Internalized                                            │  │
│  │  └── Degraded / eliminated                                   │  │
│  │                                                              │  │
│  │  Transition rates:                                           │  │
│  │  ├── Extravasation: f(size, vascular permeability)           │  │
│  │  ├── Binding: f(kon, koff, target_density, free_agent)       │  │
│  │  ├── Internalization: f(receptor_turnover)                   │  │
│  │  ├── Degradation: f(lysosomal_rate, FcRn_rescue)            │  │
│  │  └── Elimination: renal_filtration + hepatic_metabolism      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  OUTPUT                                                           │
│  ├── concentration_time_curves: Dict[Organ, TimeSeries]          │
│  ├── tumor_uptake: float (%ID/g)                                 │
│  ├── tumor_to_background_ratio: float                            │
│  ├── organ_doses: Dict[Organ, float] (for dosimetry)             │
│  ├── time_to_optimal_imaging: float (hours)                      │
│  └── biodistribution_map: Dict[Organ, float] at each timepoint  │
└──────────────────────────────────────────────────────────────────┘
```

### Implementation: Hybrid ODE + Stochastic Approach

**Core ODE System** (deterministic backbone):
```python
class BodySimulationEngine:
    """
    Solves the compartmental ODE system:
    dC_i/dt = Q_i/V_i * (C_arterial - C_i/Kp_i) - k_bind_i * C_i * Ag_i + k_off_i * B_i - k_elim_i * C_i

    Where:
    - C_i = free agent concentration in compartment i
    - Q_i = blood flow to compartment i
    - V_i = volume of compartment i
    - Kp_i = tissue-to-plasma partition coefficient
    - k_bind_i = binding rate in compartment i
    - Ag_i = antigen density in compartment i
    - B_i = bound agent concentration
    - k_elim_i = elimination rate from compartment i
    """

    def __init__(self, body_model: BodyModel, agent: AgentProperties):
        self.body = body_model
        self.agent = agent
        self.compartments = body_model.compartments
        self.n_states = len(self.compartments) * 3  # free, bound, internalized per compartment

    def derivatives(self, t: float, y: np.ndarray) -> np.ndarray:
        dydt = np.zeros_like(y)
        free = y[:self.n_compartments]
        bound = y[self.n_compartments:2*self.n_compartments]
        internalized = y[2*self.n_compartments:]

        # Arterial concentration (mixed venous return)
        c_arterial = np.sum(
            self.body.blood_flow_fractions * free / self.body.partition_coefficients
        )

        for i, comp in enumerate(self.compartments):
            # Flow-mediated distribution
            flow_term = (comp.blood_flow / comp.volume) * (
                c_arterial - free[i] / comp.partition_coefficient
            )

            # Binding kinetics (if target present)
            binding_term = 0
            unbinding_term = 0
            if comp.target_density > 0:
                binding_term = self.agent.kon * free[i] * (
                    comp.target_density - bound[i]  # available targets
                )
                unbinding_term = self.agent.koff * bound[i]

            # Internalization
            internalization_term = comp.internalization_rate * bound[i]

            # Elimination (renal for kidney, hepatic for liver)
            elimination_term = comp.elimination_rate * free[i]

            # Free agent
            dydt[i] = flow_term - binding_term + unbinding_term - elimination_term

            # Bound agent
            dydt[self.n_compartments + i] = binding_term - unbinding_term - internalization_term

            # Internalized
            dydt[2*self.n_compartments + i] = internalization_term - comp.degradation_rate * internalized[i]

        return dydt

    def simulate(self, dose: float, duration_hours: float,
                 dt: float = 0.1) -> SimulationResult:
        y0 = np.zeros(self.n_states)
        y0[self.body.venous_blood_index] = dose / self.body.plasma_volume

        t_span = (0, duration_hours)
        t_eval = np.arange(0, duration_hours, dt)

        solution = solve_ivp(
            self.derivatives, t_span, y0,
            method='LSODA',  # stiff-aware solver
            t_eval=t_eval,
            rtol=1e-6, atol=1e-9
        )

        return self._package_results(solution)
```

**Stochastic Layer** (uncertainty quantification):
```python
class StochasticBodySimulation:
    """
    Wraps the ODE solver with Monte Carlo sampling to propagate
    parameter uncertainty through the simulation.

    Key uncertain parameters:
    - Blood flow fractions (±20-30%)
    - Vascular permeability (±50%)
    - Binding affinity (±0.5 log)
    - Target density (±2-fold)
    """
    def simulate_ensemble(self, base_params: SimulationParams,
                          n_samples: int = 200) -> EnsembleResult:
        results = []
        for _ in range(n_samples):
            perturbed = self._sample_parameters(base_params)
            engine = BodySimulationEngine(perturbed.body, perturbed.agent)
            result = engine.simulate(perturbed.dose, perturbed.duration)
            results.append(result)

        return EnsembleResult(
            median=np.median([r.tumor_uptake for r in results]),
            ci_5=np.percentile([r.tumor_uptake for r in results], 5),
            ci_95=np.percentile([r.tumor_uptake for r in results], 95),
            all_runs=results
        )
```

### Compartment Parameters (Default Adult)

| Compartment | Volume (L) | Blood Flow (% CO) | Target Expression (varies) |
|---|---|---|---|
| Arterial blood | 1.5 | — | Low |
| Venous blood | 3.5 | — | Low |
| Lungs | 0.5 | 100% | Variable |
| Liver | 1.8 | 25% | Moderate |
| Kidneys | 0.3 | 19% | PSMA+ in proximal tubule |
| Spleen | 0.15 | 3% | High (FcγR) |
| Heart | 0.3 | 4% | Low |
| Muscle | 28.0 | 17% | Low |
| Bone marrow | 1.5 | 5% | Variable |
| Tumor (user-defined) | 0.001-1.0 | 1-5% | High (target) |
| Rest of body | ~15 | 22% | Variable |

### Limitations
- Compartmental models assume well-mixed compartments — no spatial gradients within organs
- Blood flow fractions are population averages; individual variation is significant
- Tumor vasculature is highly heterogeneous; model uses effective average parameters
- Lymphatic drainage modeling is simplified
- Does not model immune cell interactions (ADCC, CDC) — purely pharmacokinetic

---

## 2.4 PK/PD Engine

### Purpose
Integrate pharmacokinetic and pharmacodynamic modeling for time-resolved predictions of agent behavior, efficacy, and toxicity.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PK/PD ENGINE                          │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │           PBPK MODEL CORE                          │  │
│  │                                                     │  │
│  │  ┌─────────────┐  ┌──────────────┐                 │  │
│  │  │ 2-Compartment│  │ Full PBPK    │                 │  │
│  │  │ (fast, less  │  │ (Body Engine │                 │  │
│  │  │  accurate)   │  │  integration)│                 │  │
│  │  └─────────────┘  └──────────────┘                 │  │
│  │         ↕               ↕                           │  │
│  │  Model selection based on data availability         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │         PHARMACODYNAMIC MODELS                      │  │
│  │                                                     │  │
│  │  Diagnostic PD (imaging):                           │  │
│  │  ├── SUV prediction = f(uptake, body_weight, dose)  │  │
│  │  ├── Tumor-to-background ratio over time            │  │
│  │  └── Optimal imaging window                         │  │
│  │                                                     │  │
│  │  Therapeutic PD (treatment):                        │  │
│  │  ├── Absorbed dose = f(uptake, residence_time, E)   │  │
│  │  ├── Tumor control probability (TCP)                │  │
│  │  └── Normal tissue complication probability (NTCP)  │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │           SCENARIO COMPARISON                       │  │
│  │                                                     │  │
│  │  Compare N scenarios across:                        │  │
│  │  ├── Different agents                               │  │
│  │  ├── Different doses                                │  │
│  │  ├── Different isotopes (68Ga vs 177Lu vs 225Ac)    │  │
│  │  ├── Different timing protocols                     │  │
│  │  └── Different patient subgroups                    │  │
│  │                                                     │  │
│  │  Output: ranked comparison with confidence           │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  OUTPUT                                                  │
│  ├── pk_curves: Dict[Compartment, TimeSeries]           │
│  ├── auc_values: Dict[Compartment, float]               │
│  ├── suv_prediction: float (for imaging agents)         │
│  ├── absorbed_dose_gy: Dict[Organ, float] (therapeutic) │
│  ├── tcp: float (tumor control probability)             │
│  ├── ntcp: Dict[Organ, float]                           │
│  └── optimal_timing: float (hours post-injection)       │
└─────────────────────────────────────────────────────────┘
```

### Dosimetry Model (for therapeutic agents)
```python
class DosimetryEngine:
    """
    MIRD formalism for internal dosimetry:
    D(target) = Σ_source Ã_source × S(target ← source)

    Where:
    - Ã = time-integrated activity (from PK curves)
    - S = dose factor (from OLINDA/EXM or precomputed)
    """
    def compute_absorbed_dose(self, pk_result: PKResult,
                              isotope: Isotope) -> DosimetryResult:
        doses = {}
        for organ in pk_result.organs:
            # Time-integrated activity (area under activity-time curve)
            residence_time = np.trapz(
                pk_result.activity_curves[organ],
                pk_result.time_points
            )
            # S-values from lookup table (OLINDA)
            s_value = self.s_value_table.get(isotope, organ)
            doses[organ] = residence_time * s_value

        # Tumor control probability (simplified linear-quadratic)
        tumor_dose = doses.get('tumor', 0)
        tcp = 1 - np.exp(-self.alpha * tumor_dose - self.beta * tumor_dose**2)

        return DosimetryResult(
            organ_doses=doses,
            tumor_dose=tumor_dose,
            tcp=tcp,
            dose_limiting_organ=max(
                [(k, v) for k, v in doses.items() if k != 'tumor'],
                key=lambda x: x[1] / self.organ_tolerance[x[0]]
            )
        )
```

### Limitations
- Dosimetry S-values assume standard organ geometries (ICRP reference phantoms)
- TCP/NTCP models use simplified radiobiological parameters (α/β ratios from external beam, not perfectly applicable to targeted radionuclide therapy)
- Does not model dose-rate effects (protracted vs. acute irradiation)

---

## 2.5 Imaging Calibration Layer

### Purpose
Use real PET/CT imaging data as ground truth to calibrate and validate simulation predictions.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│               IMAGING CALIBRATION LAYER                       │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            IMAGE PROCESSING PIPELINE                   │    │
│  │                                                        │    │
│  │  1. DICOM Ingestion                                    │    │
│  │     ├── PET series (SUV-calibrated)                    │    │
│  │     ├── CT series (for anatomy / attenuation)          │    │
│  │     └── Headers: dose, weight, scan time, isotope      │    │
│  │                                                        │    │
│  │  2. Segmentation                                       │    │
│  │     ├── Organ segmentation (TotalSegmentator / MONAAI) │    │
│  │     ├── Tumor segmentation (threshold + manual / AI)   │    │
│  │     └── VOI extraction                                 │    │
│  │                                                        │    │
│  │  3. Quantification                                     │    │
│  │     ├── SUVmean, SUVmax, SUVpeak per ROI               │    │
│  │     ├── Metabolic tumor volume (MTV)                   │    │
│  │     ├── Total lesion activity (TLA)                    │    │
│  │     └── Organ uptake (%ID/g equivalent)                │    │
│  │                                                        │    │
│  │  4. Radiomics Feature Extraction                       │    │
│  │     ├── First-order statistics                         │    │
│  │     ├── Shape features                                 │    │
│  │     ├── Texture features (GLCM, GLRLM, GLSZM)         │    │
│  │     └── Standardized per IBSI                          │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            CALIBRATION ENGINE                          │    │
│  │                                                        │    │
│  │  Compare: predicted_uptake vs measured_uptake          │    │
│  │                                                        │    │
│  │  Methods:                                              │    │
│  │  ├── Direct comparison (predicted %ID/g vs measured)   │    │
│  │  ├── Bayesian parameter estimation:                    │    │
│  │  │   Update simulation parameters to fit observed data │    │
│  │  ├── Transfer learning:                                │    │
│  │  │   Fine-tune ML components on institution's data     │    │
│  │  └── Ensemble weighting:                               │    │
│  │      Adjust model weights based on prediction error    │    │
│  │                                                        │    │
│  │  Output:                                               │    │
│  │  ├── calibration_score: float (goodness of fit)        │    │
│  │  ├── updated_parameters: Dict (calibrated params)      │    │
│  │  ├── bias_map: Dict[Organ, float] (systematic errors)  │    │
│  │  └── calibration_report: CalibrationReport             │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            SYNTHETIC IMAGE GENERATION                  │    │
│  │                                                        │    │
│  │  From simulation output → synthetic PET-like image     │    │
│  │  ├── Map compartment uptake → voxel intensities        │    │
│  │  ├── Apply PSF blurring (scanner resolution)           │    │
│  │  ├── Add Poisson noise (count statistics)              │    │
│  │  └── Output: 3D volume comparable to real PET          │    │
│  │                                                        │    │
│  │  Purpose: visual comparison + radiomics comparison     │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Calibration Process
```python
class CalibrationEngine:
    """
    Bayesian calibration: use imaging data to update simulation parameters.

    Prior: simulation parameter distributions
    Likelihood: P(observed_image | parameters)
    Posterior: calibrated parameter distributions
    """
    def calibrate(self, simulation_result: SimulationResult,
                  imaging_data: ImagingQuantification) -> CalibrationResult:

        # Extract comparable quantities
        predicted = {
            organ: simulation_result.uptake_at_time(
                organ, imaging_data.scan_time_post_injection
            )
            for organ in imaging_data.organs
        }
        measured = imaging_data.organ_uptake_values

        # Compute organ-level bias
        bias = {
            organ: measured[organ] / predicted[organ]
            for organ in predicted if predicted[organ] > 0
        }

        # Bayesian parameter update using ABC or MCMC
        posterior_params = self._abc_calibration(
            prior_params=simulation_result.parameters,
            observed=measured,
            simulator=self.run_simulation,
            n_iterations=1000,
            tolerance=0.1
        )

        return CalibrationResult(
            bias_map=bias,
            calibrated_params=posterior_params,
            goodness_of_fit=self._compute_r_squared(predicted, measured),
            n_calibration_points=len(measured)
        )
```

### Limitations
- PET quantification has intrinsic variability (partial volume effects, reconstruction artifacts)
- Organ segmentation accuracy directly affects calibration quality
- Requires scan-time-matched comparison (PET captures a snapshot; simulation is continuous)
- Scanner-specific calibration may not transfer across institutions

---

## 2.6 Patient Similarity Engine

### Purpose
Find clinically similar patients to leverage historical outcomes and imaging data for better predictions on new patients.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              PATIENT SIMILARITY ENGINE                         │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           FEATURE EXTRACTION                           │    │
│  │                                                        │    │
│  │  Clinical features:                                    │    │
│  │  ├── Demographics (age, sex, weight, BSA)              │    │
│  │  ├── Tumor type, stage, grade                          │    │
│  │  ├── Molecular markers (HER2, PSMA, Ki-67, etc.)      │    │
│  │  ├── Prior treatments                                  │    │
│  │  └── Lab values (eGFR, liver function)                 │    │
│  │                                                        │    │
│  │  Imaging features:                                     │    │
│  │  ├── Radiomics: 100+ features per lesion               │    │
│  │  ├── Organ volumes                                     │    │
│  │  ├── Tumor burden (number, size, location)             │    │
│  │  └── SUV statistics (if available)                     │    │
│  │                                                        │    │
│  │  Derived features:                                     │    │
│  │  ├── Body composition (from CT)                        │    │
│  │  ├── Estimated organ function                          │    │
│  │  └── Target expression estimate                        │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           EMBEDDING & SIMILARITY                       │    │
│  │                                                        │    │
│  │  Approach 1: Structured embedding                      │    │
│  │  ├── Normalize clinical features                       │    │
│  │  ├── PCA or UMAP on radiomics                          │    │
│  │  ├── Concatenate → patient vector                      │    │
│  │  └── Cosine similarity / Mahalanobis distance          │    │
│  │                                                        │    │
│  │  Approach 2: Learned embedding (later stage)           │    │
│  │  ├── Contrastive learning on patient pairs             │    │
│  │  ├── Outcome-supervised: similar patients should       │    │
│  │  │   have similar treatment responses                  │    │
│  │  └── Multi-modal: combine imaging + clinical           │    │
│  │                                                        │    │
│  │  Approach 3: Imaging-only embedding                    │    │
│  │  ├── 3D CNN (pretrained on TotalSegmentator)           │    │
│  │  ├── Extract features from penultimate layer           │    │
│  │  └── kNN in feature space                              │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  OUTPUT                                                       │
│  ├── similar_patients: List[PatientMatch]                     │
│  │   each with: patient_id, similarity_score, key_differences │
│  ├── cohort_statistics: CohortStats                           │
│  │   (mean uptake, response rate, toxicity rate in cohort)    │
│  └── confidence: float (based on cohort size and similarity)  │
└──────────────────────────────────────────────────────────────┘
```

### MVP Implementation
```python
class PatientSimilarityEngine:
    """
    MVP: structured feature matching with clinical + basic imaging features.
    No deep learning required initially.
    """
    def __init__(self):
        self.feature_weights = {
            'tumor_type': 3.0,      # most important
            'target_expression': 2.5,
            'stage': 1.5,
            'age': 0.5,
            'weight': 0.5,
            'eGFR': 1.0,           # kidney function affects PK
            'tumor_volume': 1.5,
            'n_metastases': 1.0,
        }
        self.scaler = StandardScaler()
        self.index = None  # FAISS or scikit-learn NearestNeighbors

    def build_index(self, patient_db: PatientDatabase):
        features = []
        for patient in patient_db:
            vec = self._extract_features(patient)
            features.append(vec)
        features = np.array(features)
        features = self.scaler.fit_transform(features)
        # Weight features
        features *= np.array(list(self.feature_weights.values()))
        self.index = NearestNeighbors(n_neighbors=10, metric='cosine')
        self.index.fit(features)

    def find_similar(self, query_patient: Patient,
                     k: int = 5) -> List[PatientMatch]:
        vec = self._extract_features(query_patient)
        vec = self.scaler.transform(vec.reshape(1, -1))
        vec *= np.array(list(self.feature_weights.values()))
        distances, indices = self.index.kneighbors(vec, n_neighbors=k)
        return [
            PatientMatch(
                patient_id=self.patient_db[idx].id,
                similarity=1 - dist,
                key_differences=self._explain_differences(query_patient, self.patient_db[idx])
            )
            for dist, idx in zip(distances[0], indices[0])
        ]
```

### Limitations
- With <100 patients, similarity matches may be sparse or misleading
- Feature weighting is heuristic initially — requires outcome data to optimize
- Imaging-based similarity requires standardized acquisition protocols
- Patient similarity does not imply identical biology — use as prior, not as ground truth

---

## 2.7 Decision Engine

### Purpose
Integrate all engine outputs to rank candidate strategies and provide actionable recommendations with explainability.

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     DECISION ENGINE                               │
│                                                                    │
│  INPUT: Results from all engines for N candidate strategies       │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │           MULTI-CRITERIA SCORING                          │    │
│  │                                                            │    │
│  │  For each candidate strategy (agent + isotope + dose):     │    │
│  │                                                            │    │
│  │  Efficacy Score:                                           │    │
│  │  ├── Tumor uptake (%ID/g)                    weight: 0.25  │    │
│  │  ├── Tumor-to-background ratio               weight: 0.20  │    │
│  │  ├── Target binding probability               weight: 0.15  │    │
│  │  ├── Tumor penetration depth                  weight: 0.10  │    │
│  │  └── Similar patient outcomes (if available)  weight: 0.30  │    │
│  │                                                            │    │
│  │  Safety Score:                                             │    │
│  │  ├── Kidney dose (fraction of tolerance)      weight: 0.30  │    │
│  │  ├── Bone marrow dose                         weight: 0.25  │    │
│  │  ├── Liver dose                               weight: 0.20  │    │
│  │  ├── Off-target accumulation                  weight: 0.15  │    │
│  │  └── Similar patient toxicity (if available)  weight: 0.10  │    │
│  │                                                            │    │
│  │  Practical Score:                                          │    │
│  │  ├── Isotope availability                     weight: 0.30  │    │
│  │  ├── Preparation complexity                   weight: 0.20  │    │
│  │  ├── Imaging window feasibility               weight: 0.25  │    │
│  │  └── Cost estimate                            weight: 0.25  │    │
│  │                                                            │    │
│  │  Combined: w_eff * Efficacy + w_safe * Safety + w_prac * P │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │           EXPLANATION LAYER                                │    │
│  │                                                            │    │
│  │  For each recommendation:                                  │    │
│  │  ├── Key drivers (SHAP-like feature importance)            │    │
│  │  ├── Risk factors                                          │    │
│  │  ├── Comparison to alternatives                            │    │
│  │  ├── Confidence level (high/medium/low)                    │    │
│  │  ├── Data support level (clinical/preclinical/simulated)   │    │
│  │  └── Natural language summary                              │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                    │
│  OUTPUT                                                           │
│  ├── ranked_strategies: List[StrategyRanking]                    │
│  │   each with: strategy, combined_score, subscores, explanation │
│  ├── best_strategy: StrategyRanking                              │
│  ├── confidence: ConfidenceAssessment                            │
│  └── report: StructuredReport (PDF/JSON/HTML)                    │
└──────────────────────────────────────────────────────────────────┘
```

### Example Output
```json
{
  "recommendation": {
    "rank": 1,
    "strategy": {
      "agent": "Trastuzumab-derived nanobody",
      "isotope": "68Ga (diagnostic) / 177Lu (therapeutic)",
      "dose": "150 MBq diagnostic, 7.4 GBq therapeutic"
    },
    "scores": {
      "efficacy": 0.78,
      "safety": 0.82,
      "practical": 0.65,
      "combined": 0.76
    },
    "explanation": {
      "key_drivers": [
        "High HER2 expression (IHC 3+) → strong target availability",
        "Nanobody format → rapid tumor penetration, fast blood clearance",
        "68Ga PET at 1-2h post-injection → high tumor-to-background"
      ],
      "risks": [
        "Kidney uptake moderate (estimated 3.2 Gy/GBq) — monitor renal function",
        "Limited clinical data for nanobody-177Lu in this indication"
      ],
      "confidence": "moderate",
      "data_support": "preclinical + simulation + 3 similar patients"
    }
  }
}
```

---

# 3. TECH STACK

## 3.1 Core Language & Framework

| Layer | Technology | Rationale |
|---|---|---|
| **Primary language** | Python 3.11+ | Ecosystem depth for scientific computing, ML, imaging |
| **Type checking** | Pydantic v2 + mypy | Runtime validation of simulation parameters; catch errors early |
| **Async orchestration** | asyncio + Celery | Pipeline orchestration; long simulations run async |
| **API framework** | FastAPI | Type-safe REST API, auto-generated OpenAPI docs |
| **Package management** | uv (astral) | Fast, reproducible dependency resolution |

## 3.2 Simulation & Scientific Computing

| Component | Technology | Rationale |
|---|---|---|
| **ODE solver** | `scipy.integrate.solve_ivp` (LSODA) | Stiff-aware, battle-tested; sufficient for compartmental ODEs |
| **Stochastic simulation** | NumPy + custom Monte Carlo | Lightweight; no need for heavy frameworks for parameter sampling |
| **Advanced PBPK (later)** | `Tellurium` / `libRoadRunner` (SBML) | SBML-compatible; allows importing PK-Sim models |
| **Multi-agent simulation** | Custom lightweight engine | Mesa is overkill for molecule-as-agent; custom is faster and more targeted |
| **Bayesian inference** | `PyMC` (v5) or `NumPyro` (JAX-based) | Parameter calibration, uncertainty quantification |
| **Numerical arrays** | NumPy, SciPy | Foundation |

**Why not PK-Sim / mrgsolve directly?**
- PK-Sim is GUI-heavy and .NET-based — poor Python integration
- mrgsolve is R-native — adds R dependency
- Better: implement core PBPK equations in Python, import PK-Sim SBML exports when needed via Tellurium

## 3.3 Machine Learning

| Component | Technology | Rationale |
|---|---|---|
| **Tabular ML** | XGBoost, LightGBM | Best for structured clinical + radiomics data; interpretable |
| **Deep learning** | PyTorch 2.x | Imaging models, embeddings, future GNN |
| **Medical imaging DL** | MONAI | PET/CT segmentation, pretrained models |
| **Radiomics** | PyRadiomics | IBSI-compliant feature extraction |
| **Embeddings / similarity** | FAISS (Facebook) | Fast nearest-neighbor search |
| **Explainability** | SHAP | Feature importance for Decision Engine |
| **Experiment tracking** | MLflow | Model versioning, parameter logging |

## 3.4 Medical Imaging

| Component | Technology | Rationale |
|---|---|---|
| **DICOM handling** | pydicom + highdicom | Read/write DICOM, structured reports |
| **NIfTI / volume ops** | nibabel, SimpleITK | Format conversion, registration, resampling |
| **Organ segmentation** | TotalSegmentator (via MONAI) | 104 structures from CT; pretrained, validated |
| **Tumor segmentation** | MONAI + custom fine-tuned | PET-guided segmentation |
| **Visualization** | ITK-SNAP (desktop), Niivue (web) | 3D volume rendering for UI |

## 3.5 Data Storage

| Component | Technology | Rationale |
|---|---|---|
| **Structured data** | PostgreSQL | Patient records, simulation configs, results |
| **Imaging data** | MinIO (S3-compatible) | DICOM/NIfTI object storage; self-hosted or cloud |
| **Time series** | TimescaleDB (PostgreSQL extension) | PK curves, simulation time series |
| **Knowledge graph** | Neo4j or NetworkX (MVP) | Target-disease-agent relationships |
| **Model registry** | MLflow | ML model versioning |
| **Caching** | Redis | Simulation result caching |

## 3.6 Infrastructure

| Component | Technology | Rationale |
|---|---|---|
| **Containerization** | Docker + Docker Compose | Reproducible environments |
| **Orchestration (later)** | Kubernetes | Scale simulation workers |
| **CI/CD** | GitHub Actions | Automated testing, deployment |
| **Monitoring** | Prometheus + Grafana | Simulation job monitoring |
| **Frontend** | React + TypeScript + Plotly/D3 | Interactive dashboards; Plotly for PK curves |
| **Notebooks** | JupyterHub | For researchers/power users |

## 3.7 Key Library Versions (Pinned)

```toml
# pyproject.toml (core dependencies)
[project]
dependencies = [
    "numpy>=1.26,<2.0",
    "scipy>=1.12",
    "pandas>=2.2",
    "pydantic>=2.6",
    "fastapi>=0.110",
    "uvicorn>=0.27",
    "torch>=2.2",
    "monai>=1.3",
    "pydicom>=2.4",
    "nibabel>=5.2",
    "pyradiomics>=3.1",
    "xgboost>=2.0",
    "scikit-learn>=1.4",
    "pymc>=5.10",
    "shap>=0.45",
    "mlflow>=2.10",
    "celery>=5.3",
    "redis>=5.0",
    "sqlalchemy>=2.0",
    "plotly>=5.18",
]
```

---

# 4. MVP PLAN

## 4.1 MVP Scope: "HER2 Antibody Biodistribution Simulator"

### What it does
Simulates the biodistribution of a HER2-targeting agent (trastuzumab or derivative) in a virtual patient and predicts:
1. Organ-level uptake over time (concentration-time curves)
2. Tumor uptake (%ID/g)
3. Tumor-to-background ratio
4. Optimal imaging time window

### What it does NOT do (yet)
- No real patient data integration
- No imaging calibration
- No patient similarity
- No deep learning
- No multi-agent comparison (single agent only)

### User Flow

```
1. User selects:
   ├── Target: HER2
   ├── Agent: Trastuzumab (full IgG) | Pertuzumab | Nanobody
   ├── Isotope: 89Zr (PET) | 177Lu (therapy)
   ├── Dose: slider (10-400 MBq)
   └── Patient: default adult | adjust weight/eGFR

2. System runs:
   ├── Target Engine: HER2 score for selected tumor type
   ├── Agent Engine: properties for selected agent
   ├── Body Engine: ODE simulation (10-15 compartments)
   └── PK/PD Engine: dosimetry if therapeutic isotope

3. User sees:
   ├── Animated body diagram with organ uptake coloring
   ├── Time-activity curves per organ (interactive Plotly)
   ├── Tumor uptake value with confidence interval
   ├── Tumor-to-background ratio
   ├── Optimal imaging window (for diagnostic)
   ├── Organ dose estimates (for therapeutic)
   └── Summary recommendation text
```

### MVP Architecture

```
┌───────────────────────────────────────────────┐
│              MVP ARCHITECTURE                  │
│                                                │
│  Frontend (React)                              │
│  ├── Input form (target, agent, isotope, dose)│
│  ├── Body diagram (SVG, colored by uptake)    │
│  ├── Time-activity curve plot (Plotly)         │
│  └── Summary card with key metrics            │
│                                                │
│  Backend (FastAPI)                             │
│  ├── /api/simulate  (POST → run simulation)   │
│  ├── /api/agents    (GET → agent library)     │
│  ├── /api/targets   (GET → target info)       │
│  └── /api/scenarios (GET → saved runs)        │
│                                                │
│  Simulation Core (Python)                     │
│  ├── target_engine.py     (lookup + scoring)  │
│  ├── agent_engine.py      (property models)   │
│  ├── body_engine.py       (ODE solver)        │
│  ├── pk_engine.py         (dosimetry)         │
│  └── models/              (parameter tables)  │
│                                                │
│  Data (JSON/SQLite)                           │
│  ├── targets.json         (curated targets)   │
│  ├── agents.json          (agent library)     │
│  ├── compartments.json    (body model params) │
│  └── simulations.db       (saved results)     │
└───────────────────────────────────────────────┘
```

### MVP Timeline: 8-10 weeks

| Week | Milestone |
|---|---|
| 1-2 | Core ODE body model (12 compartments), verified against published trastuzumab PK data |
| 3 | Agent property models (IgG, Fab, nanobody), target scoring for HER2 |
| 4 | Basic dosimetry engine (89Zr, 177Lu), Monte Carlo uncertainty |
| 5-6 | FastAPI backend, API contracts, simulation endpoint |
| 7-8 | React frontend: input form, body diagram, time-activity curves |
| 9 | Integration testing, comparison against published clinical data |
| 10 | Demo polish, documentation, deployment (Docker) |

### MVP Validation Strategy

Compare model predictions against published clinical data:

| Agent | Isotope | Published Data Source | Validation Metric |
|---|---|---|---|
| Trastuzumab | 89Zr | Dijkers et al., Clin Pharmacol Ther 2010 | Blood PK curve, liver/spleen uptake |
| Trastuzumab | 89Zr | Bensch et al., Nat Med 2018 | Tumor uptake range |
| PSMA-617 | 177Lu | Violet et al., Lancet Oncol 2019 | Kidney/salivary gland dose |
| DOTATATE | 68Ga | Sandström et al., JNM 2013 | Organ biodistribution |

**Success criterion**: Predicted organ uptake values within 2-fold of published means for ≥80% of compartments.

---

## 4.2 MVP Code Structure

```
theranostics/
├── pyproject.toml
├── README.md
├── docker-compose.yml
├── Dockerfile
│
├── src/
│   ├── theranostics/
│   │   ├── __init__.py
│   │   ├── config.py                 # Global config, constants
│   │   │
│   │   ├── engines/
│   │   │   ├── __init__.py
│   │   │   ├── target.py             # Target Engine
│   │   │   ├── agent.py              # Agent Simulation Engine
│   │   │   ├── body.py               # Body Simulation Engine (ODE)
│   │   │   ├── pkpd.py               # PK/PD Engine
│   │   │   ├── imaging.py            # Imaging Calibration (stub)
│   │   │   ├── similarity.py         # Patient Similarity (stub)
│   │   │   └── decision.py           # Decision Engine (simplified)
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── patient.py            # Patient data model
│   │   │   ├── agent_properties.py   # Agent property models
│   │   │   ├── compartment.py        # Organ compartment model
│   │   │   ├── simulation.py         # Simulation context & results
│   │   │   └── isotopes.py           # Isotope decay data
│   │   │
│   │   ├── data/
│   │   │   ├── targets.json          # Curated target database
│   │   │   ├── agents.json           # Agent library
│   │   │   ├── compartments.json     # Default body model parameters
│   │   │   ├── isotopes.json         # Isotope properties
│   │   │   └── s_values.json         # OLINDA S-values (subset)
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI app
│   │   │   ├── routes/
│   │   │   │   ├── simulate.py
│   │   │   │   ├── agents.py
│   │   │   │   └── targets.py
│   │   │   └── schemas.py            # API request/response models
│   │   │
│   │   └── orchestrator.py           # Pipeline orchestrator
│   │
│   └── frontend/                     # React app
│       ├── package.json
│       ├── src/
│       │   ├── App.tsx
│       │   ├── components/
│       │   │   ├── SimulationForm.tsx
│       │   │   ├── BodyDiagram.tsx
│       │   │   ├── TimeActivityChart.tsx
│       │   │   ├── ResultsSummary.tsx
│       │   │   └── DoseCard.tsx
│       │   ├── api/
│       │   │   └── client.ts
│       │   └── types/
│       │       └── simulation.ts
│       └── public/
│           └── body_outline.svg
│
├── tests/
│   ├── test_target_engine.py
│   ├── test_agent_engine.py
│   ├── test_body_engine.py
│   ├── test_pkpd_engine.py
│   ├── test_integration.py
│   └── validation/
│       ├── test_trastuzumab_pk.py    # Compare vs published data
│       └── test_psma617_pk.py
│
├── notebooks/
│   ├── 01_body_model_development.ipynb
│   ├── 02_agent_validation.ipynb
│   └── 03_clinical_data_comparison.ipynb
│
└── docs/
    ├── architecture.md
    └── model_documentation.md
```

---

# 5. DATA STRATEGY

## 5.1 Data Sources by Phase

### Phase 1: MVP (0-3 months) — Zero patient data required

| Data Type | Source | Size | Access |
|---|---|---|---|
| Target expression frequencies | Human Protein Atlas (proteinatlas.org) | ~20,000 genes × 44 tissues | Free, CC BY-SA 3.0 |
| Agent PK parameters | Published literature (curated) | ~50-100 agent-parameter sets | Manual curation |
| Body model parameters | ICRP Publication 89 (reference values) | Standard adult male/female | Published reference |
| Isotope properties | ICRP/NNDC nuclear data | All therapeutic isotopes | Public |
| Validation PK curves | Published clinical trial data (digitized) | ~10-20 studies | Literature |
| S-values for dosimetry | OLINDA/EXM published tables | Standard organs | Published |

### Phase 2: Early Validation (3-6 months) — Small clinical dataset

| Data Type | Source | Size | Access |
|---|---|---|---|
| PET/CT imaging | Clinical partner hospital | 30-100 patients | Data sharing agreement |
| Clinical outcomes | Clinical partner | Matched to imaging | IRB approval required |
| Public PET datasets | TCIA (The Cancer Imaging Archive) | Variable | Free, with DUA |
| PSMA PET datasets | TCIA: PSMA-MRI-CT collection | ~200 patients | Free |

### Phase 3: Scale (6-12 months)

| Data Type | Source | Size | Access |
|---|---|---|---|
| Multi-center imaging | Federated learning partners | 500-2000 patients | Federated (data stays local) |
| Real-world outcomes | EHR integration partners | 1000+ | Commercial partnership |
| Molecular profiling | TCGA, cBioPortal | 10,000+ tumors | Free |

## 5.2 Synthetic Data Strategy

Critical for early development when real patient data is scarce.

```python
class SyntheticPatientGenerator:
    """
    Generate realistic synthetic patients for:
    1. Model development and testing
    2. UI development
    3. Demonstration to stakeholders
    4. Training data augmentation

    NOT for: clinical validation (always use real data for that)
    """
    def generate_patient(self, tumor_type: str,
                         target: str) -> SyntheticPatient:
        # Sample demographics from population distributions
        age = self._sample_age(tumor_type)
        sex = self._sample_sex(tumor_type)
        weight = self._sample_weight(age, sex)
        height = self._sample_height(age, sex)
        bsa = self._dubois_bsa(weight, height)

        # Sample tumor characteristics
        stage = self._sample_stage(tumor_type)
        tumor_volume = self._sample_tumor_volume(stage)
        n_metastases = self._sample_metastases(stage)

        # Sample target expression (conditional on tumor type)
        expression_level = self._sample_expression(target, tumor_type)

        # Sample organ function
        egfr = self._sample_egfr(age, sex)
        liver_function = self._sample_liver_function(age, has_liver_mets=n_metastases > 0)

        # Scale body model parameters to this patient
        body_model = self._scale_body_model(weight, height, sex, age)

        return SyntheticPatient(
            demographics=Demographics(age=age, sex=sex, weight=weight, height=height, bsa=bsa),
            tumor=TumorProfile(type=tumor_type, stage=stage, volume=tumor_volume,
                              n_metastases=n_metastases),
            target=TargetProfile(name=target, expression=expression_level),
            organ_function=OrganFunction(egfr=egfr, liver=liver_function),
            body_model=body_model,
            is_synthetic=True  # Always flag synthetic data
        )
```

### Synthetic PET Generation (for UI development)
```python
class SyntheticPETGenerator:
    """
    Generate synthetic PET-like volumes from simulation output.
    Used for visualization, NOT for model training or validation.
    """
    def generate(self, simulation_result: SimulationResult,
                 ct_template: np.ndarray,
                 organ_segmentation: np.ndarray) -> np.ndarray:
        pet_volume = np.zeros_like(ct_template, dtype=np.float32)

        for organ_id, organ_name in ORGAN_MAP.items():
            mask = organ_segmentation == organ_id
            uptake = simulation_result.uptake_at_time(
                organ_name, self.scan_time
            )
            # Fill with uptake value + realistic noise
            pet_volume[mask] = uptake * (1 + np.random.normal(0, 0.15, mask.sum()))

        # Apply Gaussian blur (PET resolution ~4-5mm FWHM)
        pet_volume = gaussian_filter(pet_volume, sigma=2.0)

        # Add Poisson noise (count statistics)
        pet_volume = np.random.poisson(pet_volume * self.count_scale) / self.count_scale

        return pet_volume
```

## 5.3 Avoiding Overfitting with Small Datasets

| Strategy | Implementation |
|---|---|
| **Strong priors** | Use mechanistic models as backbone; ML only corrects residuals |
| **Cross-validation** | Leave-one-out CV for datasets <50; 5-fold for larger |
| **Regularization** | L2 regularization on all ML models; Bayesian priors on parameters |
| **Feature selection** | Max 5-10 features for ML models with <100 samples |
| **Ensemble** | Combine mechanistic + ML predictions; weight by data availability |
| **Domain constraints** | Enforce physical bounds (concentrations ≥ 0, mass conservation) |
| **Synthetic augmentation** | Supplement real data with simulation-based synthetic samples |
| **Uncertainty calibration** | Always report prediction intervals; widen with less data |

## 5.4 Data Quality Requirements

```python
class DataQualityChecker:
    """Run on every patient record before it enters the pipeline."""

    REQUIRED_FIELDS = ['age', 'sex', 'weight', 'tumor_type', 'target']
    VALID_RANGES = {
        'age': (18, 100),
        'weight': (30, 200),  # kg
        'egfr': (5, 150),     # mL/min/1.73m²
        'tumor_volume': (0.001, 5000),  # mL
    }

    def validate(self, patient: PatientRecord) -> ValidationResult:
        errors = []
        warnings = []

        for field in self.REQUIRED_FIELDS:
            if getattr(patient, field, None) is None:
                errors.append(f"Missing required field: {field}")

        for field, (low, high) in self.VALID_RANGES.items():
            val = getattr(patient, field, None)
            if val is not None and not (low <= val <= high):
                warnings.append(f"{field}={val} outside expected range [{low}, {high}]")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            completeness=self._compute_completeness(patient)
        )
```

---

# 6. SIMULATION STRATEGY

## 6.1 What Is Simulated Deterministically

These components use physics-based equations with known parameters:

| Component | Model | Equations |
|---|---|---|
| Blood circulation | Compartmental flow | Mass balance ODEs: dC/dt = Q/V × (C_in - C_out/Kp) |
| Radioactive decay | Exponential decay | A(t) = A₀ × e^(-λt), λ = ln(2)/t½ |
| Renal filtration | Size-based cutoff | GFR × sieving coefficient (size-dependent) |
| Mass conservation | Algebraic constraint | Σ(all compartments) = total injected dose (minus eliminated) |
| Binding kinetics | Law of mass action | dB/dt = kon × C × (Ag - B) - koff × B |
| Diffusion | Fick's law | J = -D × dC/dx |

**Confidence**: High for the mathematical framework; parameter values carry uncertainty.

## 6.2 What Is Simulated Probabilistically

These components use distributions rather than point estimates:

| Component | Uncertain Parameters | Distribution | Source |
|---|---|---|---|
| Vascular permeability | Per organ, per agent size | Log-normal | Literature ranges |
| Target expression | Per patient | Beta(α, β) from population data | HPA + literature |
| Binding affinity | Kd measurement | Log-normal (±0.5 log) | Assay variability |
| Blood flow distribution | Per organ | Normal, ±20% | ICRP reference ± variability |
| Tumor vascularity | Per patient | Log-normal | Imaging-derived when available |
| Body composition | Per patient (if unknown) | Conditioned on age/sex/weight | Population statistics |

**Implementation**: Monte Carlo simulation with N=200-1000 parameter samples per prediction. Report median + 90% credible interval.

## 6.3 What Is Learned from Data

These components use ML models trained on available data:

| Component | Model Type | Training Data | When Available |
|---|---|---|---|
| Expression score correction | Bayesian update | Patient molecular data | Phase 2 |
| PK parameter personalization | XGBoost regression | Clinical + imaging features → PK params | Phase 2 (30+ patients) |
| Tumor uptake prediction correction | Random forest | Predicted vs. actual uptake (imaging) | Phase 2 (30+ patients) |
| Patient similarity weights | Metric learning | Outcome data from similar patients | Phase 3 (100+ patients) |
| Imaging-based biomarkers | 3D CNN | Radiomics → treatment response | Phase 3 (200+ patients) |
| Dose-response model | Neural ODE | Dose + PK → outcome | Phase 4 (500+ patients) |

## 6.4 Hybrid Inference Framework

```python
class HybridPredictor:
    """
    Combines mechanistic model, statistical model, and ML correction.

    Final prediction = w1 * mechanistic + w2 * statistical + w3 * ML_correction

    Weights are data-dependent:
    - With no data: w1=0.7, w2=0.3, w3=0.0 (pure mechanistic + priors)
    - With 30 patients: w1=0.5, w2=0.2, w3=0.3
    - With 200+ patients: w1=0.3, w2=0.1, w3=0.6
    """
    def predict(self, context: SimulationContext) -> PredictionResult:
        # Mechanistic prediction (always available)
        mech_pred = self.mechanistic_model.predict(context)

        # Statistical prediction (population priors)
        stat_pred = self.statistical_model.predict(context)

        # ML correction (if trained)
        ml_correction = 0.0
        if self.ml_model is not None and self.ml_model.is_trained:
            ml_correction = self.ml_model.predict_correction(
                context, mech_pred
            )

        # Adaptive weighting
        weights = self._compute_weights(context.data_availability)

        combined = (
            weights.mechanistic * mech_pred.value +
            weights.statistical * stat_pred.value +
            weights.ml * (mech_pred.value + ml_correction)
        )

        # Uncertainty: propagate from all sources
        uncertainty = self._propagate_uncertainty(
            mech_pred, stat_pred, ml_correction, weights
        )

        return PredictionResult(
            value=combined,
            uncertainty=uncertainty,
            components={
                'mechanistic': mech_pred,
                'statistical': stat_pred,
                'ml_correction': ml_correction,
            },
            weights=weights
        )
```

## 6.5 Simulation Fidelity Levels

The platform supports multiple fidelity levels, automatically selected based on context:

| Level | Name | Speed | When Used |
|---|---|---|---|
| L1 | Quick estimate | <1 sec | UI sliders, real-time parameter exploration |
| L2 | Standard simulation | 5-30 sec | Default simulation run |
| L3 | Full Monte Carlo | 1-5 min | Detailed report with uncertainty quantification |
| L4 | High-fidelity | 10-30 min | Calibration against patient imaging data |

```
L1: 2-compartment analytical solution, point estimates only
L2: 12-compartment ODE, 50 Monte Carlo samples
L3: 12-compartment ODE, 500 Monte Carlo samples, full dosimetry
L4: 15+ compartment ODE, 1000 MC samples, Bayesian calibration, patient-specific parameters
```

---

# 7. PRODUCT STRATEGY

## 7.1 Short-Term Product (0-6 months): "TheraPredict Simulator"

**What it is**: A web-based tool for theranostic researchers and nuclear medicine physicians to simulate agent biodistribution and compare strategies.

**Target users**:
- Nuclear medicine researchers exploring new theranostic agents
- Pharmaceutical companies in preclinical theranostic development
- Academic groups designing clinical trials

**Value proposition**: "Simulate your theranostic agent's behavior before the first injection."

**Revenue model**:
- Freemium: basic simulations (HER2, PSMA, SSTR) free
- Pro: $500/month — custom agents, scenario comparison, export reports
- Enterprise: $2,000/month — API access, custom models, priority support

**Key features**:
- Pre-built models for top 10 theranostic targets
- Agent comparison tool (IgG vs Fab vs nanobody vs small molecule)
- Interactive biodistribution visualizer
- Dosimetry estimates for common isotopes
- PDF/JSON report generation
- Saved scenarios and sharing

**Go-to-market**:
- Launch at SNMMI (Society of Nuclear Medicine) or EANM conferences
- Publish validation paper (predicted vs. published clinical data)
- Free tier for academic researchers (viral adoption)
- Direct sales to top 20 radiopharmaceutical companies

**Risks**: Users may not trust simulation accuracy without clinical validation data. **Mitigation**: Lead with transparency — publish all model assumptions and validation results.

## 7.2 Mid-Term Platform (6-18 months): "TheraPredict Clinical"

**What it is**: A clinical decision support platform that integrates patient-specific data (imaging, molecular, clinical) to provide personalized theranostic predictions.

**Target users**:
- Hospital nuclear medicine departments
- Theranostic clinical trial sponsors
- Radiopharmaceutical companies (companion diagnostic optimization)

**Value proposition**: "Personalize theranostic treatment selection using your patient's data."

**New capabilities** (on top of Simulator):
- DICOM import: upload PET/CT, automatic segmentation and quantification
- Model calibration against real imaging data
- Patient similarity engine: "show me similar patients and their outcomes"
- Multi-cycle treatment planning (e.g., 4 cycles of 177Lu-PSMA)
- Dosimetry-based dose optimization
- Regulatory-grade audit trails

**Revenue model**:
- SaaS: $5,000-15,000/month per institution
- Per-patient pricing option: $200-500/simulation
- Clinical trial platform license: $50,000-200,000/trial

**Regulatory pathway**:
- CE marking (EU MDR Class IIa — clinical decision support software)
- FDA 510(k) — predicate: dosimetry software (e.g., HERMES, MIM)
- Start regulatory process at month 9; target clearance by month 18-24

**Key partnerships needed**:
- 2-3 academic medical centers for validation data
- 1 radiopharmaceutical company for co-development
- 1 PACS/RIS vendor for clinical workflow integration

## 7.3 Long-Term Vision (18-36+ months): "TheraPredict Digital Twin"

**What it is**: A full digital twin platform for in-silico theranostic drug development, capable of virtual clinical trials and personalized treatment optimization.

**Target users**:
- Pharma/biotech (drug development: virtual trials, patient selection)
- Regulatory agencies (in-silico evidence packages)
- Payers/health systems (cost-effectiveness modeling)
- Precision medicine networks

**Value proposition**: "Run virtual theranostic clinical trials. Optimize drug candidates in silico. Personalize treatment at the individual level."

**Breakthrough capabilities**:
- Virtual clinical trial simulation (N=1000 synthetic + real patients)
- Drug candidate optimization (optimize agent design parameters)
- Treatment response prediction (longitudinal modeling)
- Multi-modal data integration (genomics + imaging + clinical + wearables)
- Federated learning across institutions (data never leaves the hospital)
- LLM-powered natural language interface ("show me the best strategy for a 65yo male with PSMA+ mCRPC and borderline kidney function")
- Real-time imaging biomarker extraction during treatment

**Revenue model**:
- Platform license: $500K-2M/year for pharma
- Virtual trial service: $1-5M per indication
- Clinical decision support: per-institution SaaS
- Data network effects: each new institution improves models for all

**Competitive moat**:
- Calibrated models validated against real patient data (hard to replicate)
- Growing patient similarity database (network effect)
- Regulatory clearance (12-18 month barrier)
- Clinical workflow integration (switching costs)

---

# 8. FULL ROADMAP

## Phase 1: Foundation (Months 0-3)

### Technical Milestones
| Week | Deliverable | Details |
|---|---|---|
| 1-2 | Project setup | Repository, CI/CD, Docker, dependency management |
| 2-3 | Body Simulation Engine v1 | 12-compartment ODE model, LSODA solver, default parameters |
| 3-4 | Body model validation | Compare trastuzumab PK curves against Dijkers et al. 2010 |
| 4-5 | Target Engine v1 | Knowledge graph for 10 targets, expression scoring |
| 5-6 | Agent Engine v1 | Property models for IgG, Fab, nanobody, small molecule |
| 6-7 | PK/PD Engine v1 | Basic dosimetry (89Zr, 177Lu, 225Ac, 68Ga) |
| 7-8 | Monte Carlo layer | Stochastic simulation with 200 samples, CI output |
| 8-9 | FastAPI backend | REST API for all engines |
| 9-10 | React frontend v1 | Input form, body diagram, time-activity curves |
| 10-12 | Integration & validation | End-to-end testing, validation against 5 published datasets |

### Product Milestones
- Working demo: simulate HER2 antibody, see biodistribution
- Validation report: model vs. published data comparison
- Landing page and waitlist

### Validation Strategy
- Compare against ≥5 published PK datasets (different agents/isotopes)
- Target: predicted values within 2-fold of published means for ≥80% of organs
- Document all model assumptions and their sources

### Team Needed
- 1 computational biologist / pharmacokineticist (lead modeler)
- 1 full-stack developer (FastAPI + React)
- 1 ML engineer (part-time, infrastructure setup)

---

## Phase 2: Clinical Data Integration (Months 3-6)

### Technical Milestones
| Week | Deliverable | Details |
|---|---|---|
| 13-14 | DICOM pipeline | pydicom ingestion, SUV calculation, metadata extraction |
| 14-16 | Organ segmentation | TotalSegmentator integration, automated CT segmentation |
| 16-18 | Imaging quantification | Per-organ SUV extraction, tumor segmentation (semi-auto) |
| 18-20 | Calibration engine v1 | Compare predicted vs. measured uptake, compute bias |
| 20-22 | Patient similarity v1 | Structured feature matching, kNN on clinical features |
| 22-24 | Decision engine v1 | Multi-criteria scoring, basic ranking |
| 24-26 | Expanded agent library | Add PSMA-617, DOTATATE, anti-CD20, total 15 agents |

### Product Milestones
- Beta launch with 3 clinical partner institutions
- First real patient data calibration (30+ patients)
- Scenario comparison feature (compare 3 strategies side by side)
- Conference presentation at SNMMI/EANM

### Validation Strategy
- Retrospective study: predict uptake for 30 patients, compare with actual PET
- Compute per-organ prediction error (MAE, correlation)
- Calibration: show that model improves after seeing 10, 20, 30 patients
- IRB-approved protocol with clinical partner

### Team Growth
- Add: 1 medical imaging scientist
- Add: 1 clinical advisor (nuclear medicine physician, part-time)

---

## Phase 3: ML Enhancement (Months 6-12)

### Technical Milestones
| Week | Deliverable | Details |
|---|---|---|
| 27-30 | ML correction models | XGBoost residual correction trained on 50+ calibration pairs |
| 30-33 | Radiomics pipeline | PyRadiomics extraction, feature selection, predictive models |
| 33-36 | Advanced body model | Patient-specific parameter scaling (weight, age, organ function) |
| 36-38 | Treatment response model | Multi-cycle dosimetry, cumulative dose tracking |
| 38-40 | Learned patient similarity | Outcome-weighted embeddings (if outcome data available) |
| 40-44 | Synthetic PET generation | Simulation → synthetic PET for visual comparison |
| 44-48 | API v2 | Batch simulation, webhooks, Python SDK for researchers |
| 48-52 | Federated learning prototype | Model training without sharing patient data |

### Product Milestones
- Public launch of TheraPredict Simulator (freemium)
- 10+ paying institutions on Clinical platform
- Published validation study (peer-reviewed journal)
- Regulatory pre-submission meeting (FDA/CE)
- Expanded to 30+ targets, 25+ agents

### Validation Strategy
- Prospective validation: predict before scan, compare after (50+ patients)
- Multi-center: validate across 2-3 institutions with different scanners
- Ablation study: mechanistic-only vs. hybrid vs. ML-corrected
- Publish: "AI-augmented pharmacokinetic prediction for theranostics"

### Team Growth
- Add: 1 ML scientist (deep learning / medical imaging)
- Add: 1 product manager
- Add: 1 regulatory affairs consultant
- Total team: 6-7 people

---

## Phase 4: Platform & Scale (Months 12-24)

### Technical Milestones
| Month | Deliverable | Details |
|---|---|---|
| 12-14 | Virtual patient cohort | Generate 1000+ realistic virtual patients for each indication |
| 14-16 | Virtual trial simulator | Simulate trial arms, compute statistical power |
| 16-18 | Drug design optimization | Bayesian optimization of agent properties (size, affinity) |
| 18-20 | LLM interface | Natural language queries over simulation results |
| 20-22 | Longitudinal modeling | Multi-timepoint prediction, treatment adaptation |
| 22-24 | Federated learning production | Multi-center model improvement without data sharing |

### Product Milestones
| Month | Milestone |
|---|---|
| 12-14 | First pharma partnership (virtual trial service) |
| 14-16 | CE marking submission |
| 16-18 | FDA 510(k) submission |
| 18-20 | 50+ institutions on platform |
| 20-22 | Launch virtual trial service |
| 22-24 | Series A fundraising (if not done earlier) |

### Validation Strategy
- Virtual trial retrospective: simulate a completed trial, compare outcomes
- Regulatory validation package (analytical + clinical validation)
- Real-world evidence: track prediction accuracy across all platform users
- External validation by independent academic group

### Team Growth
- Add: 2 engineers (backend/infrastructure)
- Add: 1 clinical operations lead
- Add: 1 business development lead
- Total team: 10-12 people

---

# 9. SCIENTIFIC HONESTY: LIMITATIONS & APPROXIMATIONS

## 9.1 What This Platform IS

- A **probabilistic simulation tool** that combines mechanistic models with data-driven corrections
- A **decision support system** that helps rank and compare theranostic strategies
- A **research platform** that accelerates hypothesis generation and experimental design
- A **calibratable system** that improves with each patient's data

## 9.2 What This Platform IS NOT

- **NOT a replacement for clinical trials** — simulations cannot substitute for real efficacy/safety data
- **NOT a diagnostic device** (in its early form) — outputs are predictions, not measurements
- **NOT perfectly accurate** — all predictions carry uncertainty, and that uncertainty should be communicated
- **NOT a guarantee of treatment outcome** — biological complexity exceeds any model

## 9.3 Key Approximations

| Approximation | Impact | Mitigation |
|---|---|---|
| **Well-mixed compartments** | Ignores spatial heterogeneity within organs | Report this as a known limitation; future: spatially-resolved models |
| **Population-average parameters** | Individual variation can be 2-5× | Monte Carlo sampling; patient-specific calibration when data available |
| **Simplified tumor model** | Real tumors have heterogeneous vasculature, necrosis, immune infiltrate | Use tumor-specific parameters where measurable; acknowledge limitation |
| **No immune interactions** | ADCC/CDC can significantly affect antibody-based therapy | Out of scope for v1; plan for v2 immune module |
| **Static target expression** | Expression can change with treatment, hypoxia, etc. | Note as limitation; future: dynamic expression models |
| **Standard organ geometries for dosimetry** | Patient-specific anatomy varies | CT-based personalization in Phase 2 |
| **Limited drug-drug interactions** | Concurrent medications can affect PK | Accept limitation; flag known interactions from database |

## 9.4 Confidence Communication

Every output must include:

```python
class ConfidenceAssessment:
    level: Literal["high", "moderate", "low", "very_low"]
    factors: List[str]  # What drives this confidence level
    data_support: Literal[
        "clinical_validated",      # Compared against clinical data
        "preclinical_supported",   # Supported by preclinical data
        "literature_informed",     # Based on published parameters
        "simulation_only",         # Pure simulation, no validation
        "extrapolated"             # Outside training/validation domain
    ]
    recommendation: str  # What the user should do with this information

# Example:
ConfidenceAssessment(
    level="moderate",
    factors=[
        "Trastuzumab PK model validated against 3 clinical datasets",
        "Patient-specific body model (weight-scaled)",
        "Target expression from population average (no patient-specific data)"
    ],
    data_support="literature_informed",
    recommendation="Use as hypothesis-generating. Confirm tumor uptake with diagnostic PET before therapeutic dosing."
)
```

## 9.5 What We Are Honest About

1. **Small sample sizes**: With 30-100 patients, ML models have limited generalizability. We weight mechanistic models more heavily and communicate wide confidence intervals.

2. **Biological complexity**: The human body is not a set of well-mixed compartments. Our model is a useful approximation, not a faithful reproduction.

3. **Extrapolation risk**: Predictions for novel agent types, rare tumor types, or unusual patient populations are less reliable.

4. **Garbage in, garbage out**: Model quality depends on input data quality. Missing or inaccurate inputs produce unreliable outputs.

5. **Validation gaps**: Until validated against diverse, multi-center clinical data, predictions should be treated as hypothesis-generating, not decision-making.

---

# 10. RISK ANALYSIS & MITIGATION

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Model predictions too inaccurate for clinical use | Medium | High | Lead with simulation/research use case; build trust with validation data |
| Insufficient clinical data for calibration | Medium | High | Synthetic data + federated learning + strong mechanistic backbone |
| Regulatory pathway unclear for in-silico tools | Medium | Medium | Early pre-submission meeting with FDA; follow ASME V&V 40 framework |
| Competition from pharma internal tools | Medium | Medium | Focus on academic adoption (moat via network effects) + publication |
| Clinical partners slow to share data | High | Medium | Start with public datasets; offer free platform access for data partners |
| Overpromising / loss of scientific credibility | Low | Very High | Rigorous validation framework; always communicate uncertainty |
| Key person risk (small team) | Medium | High | Document everything; modular architecture; hire early |

---

# 11. COMPETITIVE LANDSCAPE

| Competitor | What They Do | Our Differentiation |
|---|---|---|
| **Certara (Simcyp)** | PBPK modeling for drug development | We focus specifically on theranostics + imaging calibration |
| **Open Systems Pharmacology (PK-Sim)** | Open-source PBPK | We add AI, imaging, patient similarity; theranostic-specific |
| **GE/Siemens dosimetry software** | Post-imaging dosimetry calculation | We predict BEFORE imaging; combine PK + dosimetry |
| **Flywheel / Gradient Health** | Medical imaging data platforms | We add simulation engines; not just data management |
| **In-house pharma tools** | Custom PBPK for specific agents | We offer a general platform across agents and targets |

**Our unique combination**: PBPK + AI + imaging calibration + patient similarity + theranostic-specific, in a single integrated platform.

---

# 12. KEY METRICS TO TRACK

## Technical Metrics
- Mean absolute error: predicted vs. measured organ uptake (%ID/g)
- Correlation coefficient: predicted vs. measured tumor SUV
- Calibration score: % of predictions where true value falls within 90% CI
- Simulation speed: time to complete L2 simulation

## Product Metrics
- Monthly active users (MAU)
- Simulations run per month
- Conversion: free → paid
- Customer retention (monthly)
- Net Promoter Score

## Scientific Metrics
- Number of published validation studies
- Number of clinical sites using the platform
- Size of calibration dataset (number of patients)
- Number of agent/target combinations validated

---

# 13. IMMEDIATE NEXT STEPS (This Week)

1. **Set up repository**: Initialize Python project with `uv`, create module structure
2. **Implement body model**: 12-compartment ODE with default parameters
3. **Digitize validation data**: Extract PK curves from Dijkers et al. 2010 (trastuzumab-89Zr)
4. **First simulation**: Run trastuzumab simulation, plot PK curves, compare to published data
5. **Define data models**: Pydantic models for Patient, Agent, Compartment, SimulationResult

This gets a working simulation core in place within the first 2 weeks.
