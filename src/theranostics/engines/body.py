"""Body Simulation Engine — multi-compartment PBPK biodistribution model.

This is the core simulation engine. It solves a system of ODEs representing
agent distribution across body compartments using standard PBPK equations:

    V_t * dC_t/dt = Q_t * (C_plasma - C_t/Kp_t) - binding + unbinding

    V_p * dC_p/dt = Σ Q_t * (C_t/Kp_t - C_plasma) - CL * C_plasma

where:
    C_t = tissue concentration, C_p = plasma concentration
    Q_t = blood flow to tissue, V_t = tissue volume
    Kp_t = tissue:plasma partition coefficient
    CL = total clearance
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np
from scipy.integrate import solve_ivp

from theranostics.models.agent_properties import AgentProperties, AgentType
from theranostics.models.compartment import BodyModel, build_default_body_model
from theranostics.models.patient import PatientProfile
from theranostics.models.simulation import (
    ConfidenceAssessment,
    OrganTimeSeries,
    PredictionResult,
    SimulationResult,
)


class BodySimulationEngine:
    """Solve the multi-compartment PBPK model for agent biodistribution."""

    def simulate(
        self,
        agent: AgentProperties,
        patient: PatientProfile,
        dose_mbq: float = 37.0,
        dose_mg: Optional[float] = None,
        duration_hours: float = 168.0,
        time_step_hours: float = 0.1,
        n_monte_carlo: int = 200,
    ) -> SimulationResult:
        """Run the full simulation with Monte Carlo uncertainty."""
        t_start = time.time()

        # Build body model scaled to patient
        target_name = agent.target_name
        tumor_density = patient.tumor.target_expression_level
        if tumor_density is None:
            tumor_density = self._default_tumor_density(target_name)
        tumor_density_nm = tumor_density * 200.0 if tumor_density <= 1.0 else tumor_density

        body = build_default_body_model(
            target_name=target_name,
            tumor_volume_ml=patient.tumor.tumor_volume_ml,
            tumor_target_density=tumor_density_nm,
        )
        body = body.scale_to_patient(
            weight_kg=patient.demographics.weight_kg,
            renal_factor=patient.renal_scaling_factor,
            hepatic_factor=patient.organ_function.liver_function_score,
        )

        # Compute initial plasma concentration (nM)
        c0 = self._compute_initial_concentration(agent, body, dose_mbq, dose_mg)

        # Time points
        t_eval = np.arange(0, duration_hours + time_step_hours, time_step_hours)

        # Tissue compartments (everything except plasma)
        tissues = [(i, c) for i, c in enumerate(body.compartments) if c.name != "plasma"]
        plasma_idx = next(i for i, c in enumerate(body.compartments) if c.name == "plasma")
        n_tissues = len(tissues)

        # Build parameter arrays for vectorized ODE
        Q = np.array([body.blood_flow_l_per_h(c) for _, c in tissues])
        V = np.array([c.volume_l for _, c in tissues])
        Kp = np.array([c.partition_coefficient for _, c in tissues])
        Ag = np.array([c.target_density_nm for _, c in tissues])
        k_int = np.array([c.internalization_rate_per_h for _, c in tissues])
        k_deg = np.array([c.degradation_rate_per_h for _, c in tissues])

        V_plasma = body.plasma_volume_l

        # Clearance rate
        CL = self._compute_clearance(agent, body)

        # Binding rate constants (capped for stability)
        kon = min(agent.kon_per_nm_per_h, 5.0)
        koff = agent.koff_per_h

        # Radioactive decay
        isotope = agent.isotope_properties
        lambda_decay = isotope.decay_constant if isotope else 0.0

        # State: [C_plasma, C_tissue_1..N, B_1..N (bound), I_1..N (internalized)]
        n_states = 1 + 3 * n_tissues

        def derivatives(t, y):
            y = np.maximum(y, 0.0)
            dydt = np.zeros(n_states)

            cp = y[0]
            ct = y[1:1 + n_tissues]
            cb = y[1 + n_tissues:1 + 2 * n_tissues]
            ci = y[1 + 2 * n_tissues:]

            # Tissue free: dCt/dt = (Q/V) * (Cp - Ct/Kp) - binding + unbinding
            cv = ct / np.maximum(Kp, 0.01)  # venous concentration leaving tissue
            flow_term = (Q / np.maximum(V, 0.001)) * (cp - cv)
            available = np.maximum(Ag - cb, 0.0)
            binding = kon * ct * available
            unbinding = koff * cb

            dydt[1:1 + n_tissues] = flow_term - binding + unbinding

            # Bound: dCb/dt = binding - unbinding - internalization
            internalization = k_int * cb
            dydt[1 + n_tissues:1 + 2 * n_tissues] = binding - unbinding - internalization

            # Internalized: dCi/dt = internalization - degradation
            dydt[1 + 2 * n_tissues:] = internalization - k_deg * ci

            # Plasma: dCp/dt = (1/Vp) * Σ Q*(Ct/Kp - Cp) - CL/Vp * Cp
            plasma_inflow = np.sum(Q * (cv - cp))
            dydt[0] = plasma_inflow / V_plasma - (CL / V_plasma) * cp

            # Radioactive decay
            if lambda_decay > 0:
                dydt -= lambda_decay * y

            return dydt

        # Run deterministic (median)
        y0 = np.zeros(n_states)
        y0[0] = c0

        median_raw = self._solve_ode(derivatives, y0, t_eval, duration_hours)
        if median_raw is None:
            raise RuntimeError("ODE solver failed for median simulation")

        # Monte Carlo
        mc_tumor_peaks = []
        mc_tbr_peaks = []
        effective_mc = min(n_monte_carlo, 200) if n_monte_carlo > 1 else 0

        for _ in range(effective_mc):
            # Perturb parameters
            Q_p = Q * np.random.lognormal(0, 0.10, n_tissues)
            V_p = V * np.random.lognormal(0, 0.07, n_tissues)
            Kp_p = Kp * np.random.lognormal(0, 0.10, n_tissues)
            Ag_p = Ag * np.random.lognormal(0, 0.20, n_tissues)
            CL_p = CL * np.random.lognormal(0, 0.15)
            c0_p = c0 * np.random.lognormal(0, 0.05)

            def derivatives_mc(t, y, Qm=Q_p, Vm=V_p, Kpm=Kp_p, Agm=Ag_p, CLm=CL_p):
                y = np.maximum(y, 0.0)
                dydt = np.zeros(n_states)
                cp = y[0]
                ct = y[1:1 + n_tissues]
                cb = y[1 + n_tissues:1 + 2 * n_tissues]
                ci = y[1 + 2 * n_tissues:]

                cv = ct / np.maximum(Kpm, 0.01)
                flow_term = (Qm / np.maximum(Vm, 0.001)) * (cp - cv)
                avail = np.maximum(Agm - cb, 0.0)
                b = kon * ct * avail
                ub = koff * cb
                dydt[1:1 + n_tissues] = flow_term - b + ub
                dydt[1 + n_tissues:1 + 2 * n_tissues] = b - ub - k_int * cb
                dydt[1 + 2 * n_tissues:] = k_int * cb - k_deg * ci
                plasma_in = np.sum(Qm * (cv - cp))
                dydt[0] = plasma_in / V_plasma - (CLm / V_plasma) * cp
                if lambda_decay > 0:
                    dydt -= lambda_decay * y
                return dydt

            y0_mc = np.zeros(n_states)
            y0_mc[0] = c0_p

            mc_raw = self._solve_ode(
                derivatives_mc, y0_mc, t_eval, duration_hours
            )
            if mc_raw is not None:
                tumor_idx_in_tissues = self._find_tumor_tissue_idx(tissues)
                if tumor_idx_in_tissues is not None:
                    tumor_c = mc_raw[1 + tumor_idx_in_tissues] + mc_raw[1 + n_tissues + tumor_idx_in_tissues]
                    mc_tumor_peaks.append(float(np.max(tumor_c)))
                    muscle_idx = self._find_tissue_idx(tissues, "muscle")
                    if muscle_idx is not None:
                        muscle_c = mc_raw[1 + muscle_idx]
                        with np.errstate(divide="ignore", invalid="ignore"):
                            tbr = np.where(muscle_c > 1e-12, tumor_c / muscle_c, 0.0)
                        mc_tbr_peaks.append(float(np.max(tbr)))

        # Package results
        result = self._package_results(
            median_raw, t_eval, tissues, n_tissues, plasma_idx,
            body, agent, patient, dose_mbq, mc_tumor_peaks, mc_tbr_peaks,
            n_monte_carlo,
        )
        result.simulation_duration_seconds = round(time.time() - t_start, 2)
        return result

    def _solve_ode(self, func, y0, t_eval, duration):
        try:
            sol = solve_ivp(
                func, (0, duration), y0,
                method="BDF", t_eval=t_eval,
                rtol=1e-4, atol=1e-6, max_step=5.0,
            )
            if sol.success:
                return sol.y
        except Exception:
            pass

        # Fallback to Radau
        try:
            sol = solve_ivp(
                func, (0, duration), y0,
                method="Radau", t_eval=t_eval,
                rtol=1e-3, atol=1e-5, max_step=5.0,
            )
            if sol.success:
                return sol.y
        except Exception:
            pass

        return None

    def _compute_initial_concentration(
        self, agent: AgentProperties, body: BodyModel,
        dose_mbq: float, dose_mg: Optional[float],
    ) -> float:
        """Compute initial plasma concentration in nM."""
        if dose_mg is not None:
            mw_da = agent.molecular_weight_kda * 1000
            moles = (dose_mg * 1e-3) / mw_da
            conc_m = moles / (body.plasma_volume_l * 1e-3)  # mol/L
            return conc_m * 1e9  # nM
        else:
            if agent.agent_type in (AgentType.IGG, AgentType.FAB, AgentType.MINIBODY):
                spec_act = 0.5  # MBq/μg
                mass_ug = dose_mbq / spec_act
                mass_mg = mass_ug / 1000
            else:
                spec_act = 50.0  # MBq/nmol
                nmol = dose_mbq / spec_act
                mass_mg = nmol * agent.molecular_weight_kda * 1e-6

            mw_da = agent.molecular_weight_kda * 1000
            moles = (mass_mg * 1e-3) / mw_da
            conc_m = moles / (body.plasma_volume_l * 1e-3)
            return max(conc_m * 1e9, 0.001)

    def _compute_clearance(self, agent: AgentProperties, body: BodyModel) -> float:
        """Compute total clearance in L/h from half-life."""
        vd = agent.volume_of_distribution_l or body.plasma_volume_l
        cl = 0.693147 / agent.plasma_half_life_hours * vd
        return cl

    def _find_tumor_tissue_idx(self, tissues):
        for j, (_, c) in enumerate(tissues):
            if c.is_tumor:
                return j
        return None

    def _find_tissue_idx(self, tissues, name):
        for j, (_, c) in enumerate(tissues):
            if c.name == name:
                return j
        return None

    def _package_results(
        self, raw, t_eval, tissues, n_tissues, plasma_idx,
        body, agent, patient, dose_mbq,
        mc_tumor_peaks, mc_tbr_peaks, n_monte_carlo,
    ) -> SimulationResult:
        t = t_eval.tolist()
        cp = raw[0]  # plasma

        # Build organ time series
        organ_results = []
        biodist: dict = {}

        # Find tumor and muscle for TBR
        tumor_tissue_idx = self._find_tumor_tissue_idx(tissues)
        muscle_tissue_idx = self._find_tissue_idx(tissues, "muscle")

        # Compute tumor TBR curve for optimal timing
        if tumor_tissue_idx is not None and muscle_tissue_idx is not None:
            tumor_total = raw[1 + tumor_tissue_idx] + raw[1 + n_tissues + tumor_tissue_idx]
            muscle_total = raw[1 + muscle_tissue_idx]
            # Use a minimum background threshold to avoid division-by-near-zero artifacts
            # Threshold: 1% of initial plasma concentration
            bg_threshold = max(raw[0][0] * 0.01, 1e-6)
            with np.errstate(divide="ignore", invalid="ignore"):
                tbr_curve = np.where(
                    muscle_total > bg_threshold,
                    tumor_total / muscle_total,
                    0.0,
                )
            optimal_idx = int(np.argmax(tbr_curve))
            optimal_time = t[optimal_idx]
            tbr_peak = float(tbr_curve[optimal_idx])
        else:
            optimal_idx = len(t) // 2
            optimal_time = t[optimal_idx]
            tbr_peak = 0.0

        # Total in body for %ID/g
        total_activity = np.zeros(len(t))
        all_tissue_totals = []
        for j, (orig_idx, comp) in enumerate(tissues):
            ct = raw[1 + j]
            cb = raw[1 + n_tissues + j]
            total = ct + cb  # free + bound
            all_tissue_totals.append((comp, total))
            total_activity += total * comp.volume_l

        total_activity += cp * body.plasma_volume_l

        # Plasma time series
        plasma_comp = body.compartments[plasma_idx]
        plasma_mass_g = body.plasma_volume_l * 1000
        with np.errstate(divide="ignore", invalid="ignore"):
            plasma_id_g = np.where(
                total_activity > 1e-12,
                (cp * body.plasma_volume_l / total_activity) * 100.0 / plasma_mass_g,
                0.0,
            )
        organ_results.append(OrganTimeSeries(
            organ_name="plasma",
            times_hours=t,
            concentrations_free=cp.tolist(),
            concentrations_bound=[0.0] * len(t),
            concentrations_total=cp.tolist(),
            uptake_percent_id_per_g=plasma_id_g.tolist(),
            is_tumor=False,
        ))
        biodist["plasma"] = round(float(plasma_id_g[optimal_idx]) if optimal_idx < len(plasma_id_g) else 0.0, 6)

        # Tissue time series
        for j, (orig_idx, comp) in enumerate(tissues):
            ct = raw[1 + j]
            cb = raw[1 + n_tissues + j]
            total = ct + cb
            mass_g = comp.volume_l * 1000

            with np.errstate(divide="ignore", invalid="ignore"):
                id_g = np.where(
                    (total_activity > 1e-12) & (mass_g > 0),
                    (total * comp.volume_l / total_activity) * 100.0 / mass_g,
                    0.0,
                )

            organ_results.append(OrganTimeSeries(
                organ_name=comp.name,
                times_hours=t,
                concentrations_free=ct.tolist(),
                concentrations_bound=cb.tolist(),
                concentrations_total=total.tolist(),
                uptake_percent_id_per_g=id_g.tolist(),
                is_tumor=comp.is_tumor,
            ))
            biodist[comp.name] = round(float(id_g[optimal_idx]) if optimal_idx < len(id_g) else 0.0, 6)

        # Tumor uptake
        tumor_peak = 0.0
        if tumor_tissue_idx is not None:
            tumor_total = raw[1 + tumor_tissue_idx] + raw[1 + n_tissues + tumor_tissue_idx]
            tumor_peak = float(np.max(tumor_total))

        # CI from Monte Carlo
        if mc_tumor_peaks:
            tumor_ci_low = float(np.percentile(mc_tumor_peaks, 5))
            tumor_ci_high = float(np.percentile(mc_tumor_peaks, 95))
        else:
            tumor_ci_low = tumor_peak * 0.5
            tumor_ci_high = tumor_peak * 2.0

        if mc_tbr_peaks:
            tbr_ci_low = float(np.percentile(mc_tbr_peaks, 5))
            tbr_ci_high = float(np.percentile(mc_tbr_peaks, 95))
        else:
            tbr_ci_low = tbr_peak * 0.5
            tbr_ci_high = tbr_peak * 2.0

        # Plasma half-life: terminal phase (beta phase)
        # Use last 50% of the curve to estimate terminal slope
        n_pts = len(cp)
        mid = n_pts // 2
        if mid > 10 and cp[mid] > 1e-12 and cp[-1] > 1e-12:
            # Log-linear regression on terminal phase
            log_c = np.log(np.maximum(cp[mid:], 1e-15))
            t_term = np.array(t[mid:])
            # Simple linear fit: log(C) = a - k*t => t½ = ln2/k
            if len(t_term) > 2:
                coeffs = np.polyfit(t_term, log_c, 1)
                k_elim = -coeffs[0]
                if k_elim > 1e-8:
                    sim_half_life = 0.693147 / k_elim
                else:
                    sim_half_life = agent.plasma_half_life_hours
            else:
                sim_half_life = agent.plasma_half_life_hours
        else:
            sim_half_life = agent.plasma_half_life_hours

        confidence = self._assess_confidence(agent, patient)

        return SimulationResult(
            request_summary={
                "agent": agent.name,
                "target": agent.target_name,
                "dose_mbq": dose_mbq,
                "patient_weight_kg": patient.demographics.weight_kg,
                "tumor_volume_ml": patient.tumor.tumor_volume_ml,
            },
            time_points_hours=t,
            organ_results=organ_results,
            tumor_uptake_percent_id_per_g=PredictionResult(
                value=round(tumor_peak, 4),
                ci_low=round(tumor_ci_low, 4),
                ci_high=round(tumor_ci_high, 4),
                unit="nM (tumor concentration)",
            ),
            tumor_to_background_ratio=PredictionResult(
                value=round(tbr_peak, 2),
                ci_low=round(tbr_ci_low, 2),
                ci_high=round(tbr_ci_high, 2),
                unit="ratio (tumor/muscle)",
            ),
            optimal_imaging_time_hours=PredictionResult(
                value=round(optimal_time, 1),
                ci_low=round(max(0, optimal_time * 0.7), 1),
                ci_high=round(optimal_time * 1.5, 1),
                unit="hours post-injection",
            ),
            plasma_half_life_hours=round(sim_half_life, 1),
            biodistribution_at_optimal=biodist,
            confidence=confidence,
            n_monte_carlo_samples=n_monte_carlo,
        )

    def _assess_confidence(self, agent, patient):
        factors = []
        level = "moderate"
        if agent.name in ("Trastuzumab", "Trastuzumab-89Zr", "PSMA-617", "DOTATATE"):
            factors.append(f"{agent.name} PK model based on published clinical data")
        else:
            factors.append("Agent PK parameters estimated from class averages")
            level = "low"
        if patient.tumor.target_expression_level is not None:
            factors.append("Patient-specific target expression data available")
        else:
            factors.append("Target expression estimated from population data")
        factors.append("Body model scaled to patient weight and organ function")
        return ConfidenceAssessment(
            level=level, factors=factors, data_support="literature_informed",
            recommendation=(
                "Use as hypothesis-generating. Predictions based on mechanistic "
                "modeling with literature-derived parameters. Confirm with "
                "diagnostic imaging before therapeutic decisions."
            ),
        )

    def _default_tumor_density(self, target_name):
        return {"HER2": 0.7, "PSMA": 0.8, "SSTR2": 0.75, "CD20": 0.85, "FAP": 0.65}.get(
            target_name, 0.5
        )
