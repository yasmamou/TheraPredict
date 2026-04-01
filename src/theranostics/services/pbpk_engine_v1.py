"""PBPK Engine V1 — Module 4 of TheraPredict V1 pipeline.

Enhanced multi-compartment PBPK solver with:
- 14 compartments (added salivary_glands, bone)
- Full logging (solver params, convergence, MC stats)
- BDF solver primary, Radau fallback
- Complete traceability
- Uses parameters from Parameter Builder
"""

from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np
from scipy.integrate import solve_ivp

from theranostics.services.input_normalizer import NormalizedRequest
from theranostics.services.parameter_builder import BuiltParameters
from theranostics.services.logging_service import PipelineLogger, ModuleTimer

MODULE = "pbpk_engine"

# ---------------------------------------------------------------------------
# Reference body model (ICRP 89, adult male 73 kg)
# ---------------------------------------------------------------------------

_COMPARTMENT_DEFS: list[dict[str, Any]] = [
    {"name": "plasma", "volume_l": 3.0, "blood_flow_frac": 0.0, "vasc_frac": 1.0, "is_tumor": False},
    {"name": "lungs", "volume_l": 0.5, "blood_flow_frac": 1.0, "vasc_frac": 0.30, "is_tumor": False},
    {"name": "liver", "volume_l": 1.8, "blood_flow_frac": 0.25, "vasc_frac": 0.15, "is_elimination": True, "is_tumor": False},
    {"name": "kidney", "volume_l": 0.3, "blood_flow_frac": 0.19, "vasc_frac": 0.15, "is_elimination": True, "is_tumor": False},
    {"name": "spleen", "volume_l": 0.15, "blood_flow_frac": 0.03, "vasc_frac": 0.20, "is_tumor": False},
    {"name": "heart", "volume_l": 0.3, "blood_flow_frac": 0.04, "vasc_frac": 0.10, "is_tumor": False},
    {"name": "muscle", "volume_l": 28.0, "blood_flow_frac": 0.17, "vasc_frac": 0.03, "is_tumor": False},
    {"name": "bone_marrow", "volume_l": 1.5, "blood_flow_frac": 0.05, "vasc_frac": 0.10, "is_tumor": False},
    {"name": "skin", "volume_l": 3.0, "blood_flow_frac": 0.05, "vasc_frac": 0.03, "is_tumor": False},
    {"name": "gut", "volume_l": 1.2, "blood_flow_frac": 0.15, "vasc_frac": 0.05, "is_tumor": False},
    {"name": "brain", "volume_l": 1.4, "blood_flow_frac": 0.12, "vasc_frac": 0.04, "is_tumor": False},
    {"name": "salivary_glands", "volume_l": 0.04, "blood_flow_frac": 0.005, "vasc_frac": 0.10, "is_tumor": False},
    {"name": "bone", "volume_l": 4.0, "blood_flow_frac": 0.02, "vasc_frac": 0.04, "is_tumor": False},
    # rest_of_body gets remaining blood flow
    {"name": "rest_of_body", "volume_l": 10.0, "blood_flow_frac": 0.0, "vasc_frac": 0.04, "is_tumor": False},
]


# ---------------------------------------------------------------------------
# PBPK result
# ---------------------------------------------------------------------------

class PBPKResult:
    """Output of the PBPK Engine."""

    def __init__(self) -> None:
        self.time_points: list[float] = []
        self.organ_timeseries: dict[str, dict[str, list[float]]] = {}
        self.tumor_peak_concentration_nM: float = 0.0
        self.tumor_auc: float = 0.0
        self.tbr_peak: float = 0.0
        self.optimal_imaging_time_h: float = 24.0
        self.plasma_half_life_h: float = 0.0
        self.biodistribution_at_optimal: dict[str, float] = {}
        self.mc_tumor_peaks: list[float] = []
        self.mc_tbr_peaks: list[float] = []
        self.mc_success_count: int = 0
        self.mc_fail_count: int = 0
        self.solver_method: str = "BDF"
        self.solver_nfev: int = 0
        self.computation_time_s: float = 0.0

    def to_metrics_dict(self) -> dict[str, Any]:
        """Return key metrics for PD/Decision engines."""
        return {
            "tumor_peak_concentration_nM": self.tumor_peak_concentration_nM,
            "tumor_auc": self.tumor_auc,
            "tbr_value": self.tbr_peak,
            "optimal_imaging_time": self.optimal_imaging_time_h,
            "plasma_half_life_h": self.plasma_half_life_h,
            "tumor_uptake_value": self.tumor_peak_concentration_nM,
            "n_monte_carlo": self.mc_success_count,
            "mc_ci_tumor": [
                float(np.percentile(self.mc_tumor_peaks, 5)) if self.mc_tumor_peaks else 0,
                float(np.percentile(self.mc_tumor_peaks, 95)) if self.mc_tumor_peaks else 0,
            ],
            "mc_ci_tbr": [
                float(np.percentile(self.mc_tbr_peaks, 5)) if self.mc_tbr_peaks else 0,
                float(np.percentile(self.mc_tbr_peaks, 95)) if self.mc_tbr_peaks else 0,
            ],
        }


# ---------------------------------------------------------------------------
# PBPK Engine V1
# ---------------------------------------------------------------------------

class PBPKEngineV1:
    """Module 4: Simulate whole-body pharmacokinetics."""

    def simulate(
        self,
        request: NormalizedRequest,
        params: BuiltParameters,
        logger: PipelineLogger,
    ) -> PBPKResult:
        with ModuleTimer(logger, MODULE, "simulation"):
            return self._do_simulate(request, params, logger)

    def _do_simulate(
        self,
        req: NormalizedRequest,
        params: BuiltParameters,
        logger: PipelineLogger,
    ) -> PBPKResult:
        t_start = time.perf_counter()
        result = PBPKResult()

        # Build compartment arrays
        patient_scale = req.patient.weight_kg / 73.0
        renal_factor = {"normal": 1.0, "mild_impairment": 0.7, "moderate_impairment": 0.45, "severe_impairment": 0.2}.get(req.patient.renal_function, 1.0) / 1.0
        hepatic_factor = {"normal": 1.0, "mild_impairment": 0.7, "moderate_impairment": 0.4}.get(req.patient.hepatic_function, 1.0)

        # Add tumor compartment
        tumor_def = {
            "name": "tumor", "volume_l": req.tumor.volume_ml / 1000.0,
            "blood_flow_frac": 0.02, "vasc_frac": 0.08, "is_tumor": True,
        }
        all_compartments = list(_COMPARTMENT_DEFS) + [tumor_def]

        # Separate plasma and tissues
        tissues = [c for c in all_compartments if c["name"] != "plasma"]
        n_tissues = len(tissues)

        # Compute rest_of_body flow
        used_flow = sum(c["blood_flow_frac"] for c in tissues if c["name"] != "rest_of_body" and c["name"] != "lungs")
        for c in tissues:
            if c["name"] == "rest_of_body":
                c["blood_flow_frac"] = max(0.0, 1.0 - used_flow - 0.02)  # minus tumor

        # Build numpy arrays
        cardiac_output = 390.0 * (patient_scale ** 0.75)
        V_plasma = 3.0 * patient_scale

        Q = np.array([c["blood_flow_frac"] * cardiac_output for c in tissues])
        V = np.array([c["volume_l"] * patient_scale for c in tissues])

        # Partition coefficients from Parameter Builder
        Kp = np.array([
            params.pk.partition_coefficients.get(c["name"], 0.4)
            for c in tissues
        ])

        # Target densities
        Ag = np.zeros(n_tissues)
        for i, c in enumerate(tissues):
            if c.get("is_tumor"):
                Ag[i] = params.tumor.tumor_target_density_nM
            else:
                Ag[i] = params.tissue_target_densities.get(c["name"], 0.0)

        # Binding kinetics
        kon = min(params.binding.kon_per_nM_per_h, 5.0)  # Cap for stability
        koff = params.binding.koff_per_h
        k_int = np.array([
            params.binding.internalization_rate_per_h if Ag[i] > 0 else 0.0
            for i in range(n_tissues)
        ])
        k_deg = 0.1  # Intracellular degradation rate

        # Clearance
        CL = params.pk.total_clearance_l_per_h
        # Apply renal/hepatic scaling
        renal_cl = CL * params.pk.renal_fraction * renal_factor
        hepatic_cl = CL * params.pk.hepatic_fraction * hepatic_factor
        other_cl = CL * (1 - params.pk.renal_fraction - params.pk.hepatic_fraction)
        CL_total = renal_cl + hepatic_cl + other_cl

        # Radioactive decay
        isotope = req.agent.isotope
        _isotope_halflife = {
            "Ga-68": 1.13, "F-18": 1.83, "Lu-177": 159.5,
            "Y-90": 64.1, "Ac-225": 240.0, "Zr-89": 78.4, "I-131": 192.5,
        }
        t_half_phys = _isotope_halflife.get(isotope or "", 0)
        lambda_decay = 0.693147 / t_half_phys if t_half_phys > 0 else 0.0

        # Initial plasma concentration
        c0 = self._compute_c0(req, params, V_plasma)

        # Time points
        t_eval = np.arange(0, req.duration_hours + req.time_step_hours, req.time_step_hours)

        # State: [C_plasma, C_tissue_1..N, B_1..N, I_1..N]
        n_states = 1 + 3 * n_tissues

        def build_derivatives(Q_p, V_p, Kp_p, Ag_p, CL_p):
            def derivatives(t, y):
                y = np.maximum(y, 0.0)
                dydt = np.zeros(n_states)
                cp = y[0]
                ct = y[1:1 + n_tissues]
                cb = y[1 + n_tissues:1 + 2 * n_tissues]
                ci = y[1 + 2 * n_tissues:]

                cv = ct / np.maximum(Kp_p, 0.01)
                flow_term = (Q_p / np.maximum(V_p, 0.001)) * (cp - cv)
                avail = np.maximum(Ag_p - cb, 0.0)
                binding = kon * ct * avail
                unbinding = koff * cb

                dydt[1:1 + n_tissues] = flow_term - binding + unbinding
                dydt[1 + n_tissues:1 + 2 * n_tissues] = binding - unbinding - k_int * cb
                dydt[1 + 2 * n_tissues:] = k_int * cb - k_deg * ci

                plasma_in = np.sum(Q_p * (cv - cp))
                dydt[0] = plasma_in / V_plasma - (CL_p / V_plasma) * cp

                if lambda_decay > 0:
                    dydt -= lambda_decay * y
                return dydt
            return derivatives

        # Log parameters
        logger.info(MODULE, "solver_parameters", data={
            "n_compartments": n_tissues + 1,
            "n_states": n_states,
            "time_span_h": req.duration_hours,
            "time_step_h": req.time_step_hours,
            "n_time_points": len(t_eval),
            "method": "BDF",
            "c0_nM": round(c0, 4),
            "CL_total_l_per_h": round(CL_total, 4),
            "lambda_decay": round(lambda_decay, 6),
            "kon_capped": round(kon, 4),
            "koff_per_h": round(koff, 4),
        })

        # Solve deterministic
        deriv_fn = build_derivatives(Q, V, Kp, Ag, CL_total)
        y0 = np.zeros(n_states)
        y0[0] = c0

        raw, method_used, nfev = self._solve(deriv_fn, y0, t_eval, req.duration_hours, logger)
        if raw is None:
            logger.error(MODULE, "solver_failed", errors=["All solver methods failed"])
            raise RuntimeError("PBPK solver failed")

        result.solver_method = method_used
        result.solver_nfev = nfev

        # Find tumor/muscle indices
        tumor_idx = next((i for i, c in enumerate(tissues) if c.get("is_tumor")), None)
        muscle_idx = next((i for i, c in enumerate(tissues) if c["name"] == "muscle"), None)

        # Extract results
        result.time_points = t_eval.tolist()
        cp = raw[0]

        # Compute total activity for %ID/g
        total_activity = cp * V_plasma
        for j in range(n_tissues):
            ct_j = raw[1 + j]
            cb_j = raw[1 + n_tissues + j]
            total_activity = total_activity + (ct_j + cb_j) * tissues[j]["volume_l"] * patient_scale

        # Build time series per organ
        result.organ_timeseries["plasma"] = {
            "free": cp.tolist(),
            "bound": [0.0] * len(cp),
            "total": cp.tolist(),
        }

        for j, comp in enumerate(tissues):
            ct_j = raw[1 + j]
            cb_j = raw[1 + n_tissues + j]
            result.organ_timeseries[comp["name"]] = {
                "free": ct_j.tolist(),
                "bound": cb_j.tolist(),
                "total": (ct_j + cb_j).tolist(),
            }

        # Tumor metrics
        if tumor_idx is not None:
            tumor_total = raw[1 + tumor_idx] + raw[1 + n_tissues + tumor_idx]
            result.tumor_peak_concentration_nM = float(np.max(tumor_total))
            result.tumor_auc = float(np.trapezoid(tumor_total, t_eval))

            # TBR
            if muscle_idx is not None:
                muscle_total = raw[1 + muscle_idx]
                bg_threshold = max(cp[0] * 0.01, 1e-6)
                with np.errstate(divide="ignore", invalid="ignore"):
                    tbr_curve = np.where(muscle_total > bg_threshold, tumor_total / muscle_total, 0.0)
                opt_idx = int(np.argmax(tbr_curve))
                result.tbr_peak = float(tbr_curve[opt_idx])
                result.optimal_imaging_time_h = float(t_eval[opt_idx])

        # Biodistribution at optimal time
        opt_idx_final = min(
            int(result.optimal_imaging_time_h / req.time_step_hours),
            len(t_eval) - 1,
        )
        for j, comp in enumerate(tissues):
            ct_j = raw[1 + j]
            cb_j = raw[1 + n_tissues + j]
            total_j = ct_j + cb_j
            result.biodistribution_at_optimal[comp["name"]] = float(total_j[opt_idx_final])

        # Plasma half-life estimation
        result.plasma_half_life_h = self._estimate_half_life(cp, t_eval, params.pk.half_life_h)

        # Monte Carlo
        n_mc = req.n_monte_carlo
        mc_success = 0
        mc_fail = 0

        logger.info(MODULE, "mc_starting", data={"n_samples": n_mc})

        for mc_i in range(n_mc):
            Q_p = Q * np.random.lognormal(0, 0.10, n_tissues)
            V_p = V * np.random.lognormal(0, 0.07, n_tissues)
            Kp_p = Kp * np.random.lognormal(0, 0.10, n_tissues)
            Ag_p = Ag * np.random.lognormal(0, 0.20, n_tissues)
            CL_p = CL_total * np.random.lognormal(0, 0.15)
            c0_p = c0 * np.random.lognormal(0, 0.05)

            deriv_mc = build_derivatives(Q_p, V_p, Kp_p, Ag_p, CL_p)
            y0_mc = np.zeros(n_states)
            y0_mc[0] = c0_p

            mc_raw, _, _ = self._solve(deriv_mc, y0_mc, t_eval, req.duration_hours, logger, quiet=True)
            if mc_raw is not None and tumor_idx is not None:
                mc_success += 1
                tumor_mc = mc_raw[1 + tumor_idx] + mc_raw[1 + n_tissues + tumor_idx]
                result.mc_tumor_peaks.append(float(np.max(tumor_mc)))

                if muscle_idx is not None:
                    muscle_mc = mc_raw[1 + muscle_idx]
                    with np.errstate(divide="ignore", invalid="ignore"):
                        tbr_mc = np.where(muscle_mc > 1e-12, tumor_mc / muscle_mc, 0.0)
                    result.mc_tbr_peaks.append(float(np.max(tbr_mc)))
            else:
                mc_fail += 1

        result.mc_success_count = mc_success
        result.mc_fail_count = mc_fail

        result.computation_time_s = time.perf_counter() - t_start

        # Log summary
        logger.audit(MODULE, "simulation_complete", data={
            "solver_method": result.solver_method,
            "solver_nfev": result.solver_nfev,
            "computation_time_s": round(result.computation_time_s, 2),
            "tumor_peak_nM": round(result.tumor_peak_concentration_nM, 2),
            "tbr_peak": round(result.tbr_peak, 2),
            "optimal_time_h": round(result.optimal_imaging_time_h, 1),
            "plasma_t_half_h": round(result.plasma_half_life_h, 1),
            "mc_success": mc_success,
            "mc_fail": mc_fail,
            "mc_tumor_cv": round(np.std(result.mc_tumor_peaks) / max(np.mean(result.mc_tumor_peaks), 1e-12), 3) if result.mc_tumor_peaks else 0,
        })

        return result

    def _solve(self, func, y0, t_eval, duration, logger, quiet=False):
        """Solve ODE with BDF primary, Radau fallback."""
        for method in ("BDF", "Radau"):
            try:
                sol = solve_ivp(
                    func, (0, duration), y0,
                    method=method, t_eval=t_eval,
                    rtol=1e-4, atol=1e-6, max_step=5.0,
                )
                if sol.success:
                    if not quiet:
                        logger.info(MODULE, "solver_success", data={
                            "method": method,
                            "nfev": sol.nfev,
                            "success": True,
                        })
                    return sol.y, method, sol.nfev
            except Exception as e:
                if not quiet:
                    logger.warning(MODULE, "solver_attempt_failed", data={
                        "method": method, "error": str(e),
                    })
        return None, "failed", 0

    def _compute_c0(self, req: NormalizedRequest, params: BuiltParameters, V_plasma: float) -> float:
        """Compute initial plasma concentration in nM."""
        dose_mg = req.dose.mass_mg
        mw_kda = req.agent.size_kDa

        if dose_mg and dose_mg > 0:
            mw_da = mw_kda * 1000
            moles = (dose_mg * 1e-3) / mw_da
            conc_m = moles / (V_plasma * 1e-3)
            return max(conc_m * 1e9, 0.001)

        # From activity
        dose_mbq = (req.dose.activity_MBq or 185.0)
        if req.agent.agent_class in ("IgG", "Fab"):
            spec_act = 0.5  # MBq/µg
            mass_ug = dose_mbq / spec_act
            mass_mg = mass_ug / 1000
        else:
            spec_act = 50.0  # MBq/nmol
            nmol = dose_mbq / spec_act
            mass_mg = nmol * mw_kda * 1e-6

        mw_da = mw_kda * 1000
        moles = (mass_mg * 1e-3) / mw_da
        conc_m = moles / (V_plasma * 1e-3)
        return max(conc_m * 1e9, 0.001)

    def _estimate_half_life(self, cp: np.ndarray, t_eval: np.ndarray, default: float) -> float:
        """Estimate terminal plasma half-life from concentration curve."""
        n = len(cp)
        mid = n // 2
        if mid > 10 and cp[mid] > 1e-12 and cp[-1] > 1e-12:
            log_c = np.log(np.maximum(cp[mid:], 1e-15))
            t_term = t_eval[mid:]
            if len(t_term) > 2:
                coeffs = np.polyfit(t_term, log_c, 1)
                k = -coeffs[0]
                if k > 1e-8:
                    return 0.693147 / k
        return default
