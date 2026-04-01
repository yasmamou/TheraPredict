"""PD / Effect Engine — Module 6 of TheraPredict V1 pipeline.

Produces a directional, plausible, explainable biological effect prediction.
V1 does NOT predict exact clinical outcomes. It produces:
- effect direction
- target engagement score
- biological plausibility score
- confidence score
- rationale text

PD types supported in V1:
1. Radiotheranostic PD (isotope-based cytotoxic/diagnostic)
2. Targeted PD (blocking/depleting known targets)
3. Target occupancy (Hill/Emax)
"""

from __future__ import annotations

from typing import Any, Optional

from theranostics.services.input_normalizer import NormalizedRequest
from theranostics.services.parameter_builder import BuiltParameters
from theranostics.services.logging_service import PipelineLogger, ModuleTimer

MODULE = "pd_engine"


# ---------------------------------------------------------------------------
# Causal rules for target-effect relationships
# ---------------------------------------------------------------------------

_CAUSAL_RULES: dict[str, dict[str, Any]] = {
    "PSMA": {
        "effect_when_targeted": "cytotoxic_to_PSMA_expressing_cells",
        "effect_direction": "tumor_cell_death",
        "mechanism": "Receptor-mediated internalization delivers cytotoxic payload "
                     "(radiation or drug) to PSMA+ cells",
        "primary_context": "prostate_cancer",
        "off_target_effects": {
            "kidney": "nephrotoxicity_from_PSMA_expression_proximal_tubule",
            "salivary_glands": "xerostomia_from_PSMA_expression",
        },
    },
    "SSTR2": {
        "effect_when_targeted": "cytotoxic_to_NET_cells",
        "effect_direction": "tumor_cell_death",
        "mechanism": "SSTR2-mediated internalization of radiolabeled somatostatin "
                     "analogs delivers radiation to NET cells",
        "primary_context": "neuroendocrine_tumor",
        "off_target_effects": {
            "spleen": "splenic_irradiation",
            "kidney": "renal_toxicity",
        },
    },
    "HER2": {
        "effect_when_targeted": "antiproliferative_and_ADCC",
        "effect_direction": "tumor_growth_inhibition",
        "mechanism": "Blocking HER2 dimerization inhibits downstream proliferative "
                     "signaling (MAPK, PI3K/AKT). Fc-mediated ADCC provides "
                     "additional immune-mediated killing",
        "primary_context": "breast_cancer",
        "off_target_effects": {
            "heart": "cardiotoxicity_from_HER2_in_cardiomyocytes",
        },
    },
    "FAP": {
        "effect_when_targeted": "tumor_stroma_disruption",
        "effect_direction": "tumor_microenvironment_modification",
        "mechanism": "Targeting FAP+ cancer-associated fibroblasts disrupts "
                     "tumor stroma support and may enhance immune infiltration",
        "primary_context": "solid_tumor",
        "off_target_effects": {
            "joints": "potential_musculoskeletal_effects",
        },
    },
    "CD20": {
        "effect_when_targeted": "B_cell_depletion",
        "effect_direction": "lymphoma_cell_killing",
        "mechanism": "CD20 targeting depletes B cells through complement-dependent "
                     "cytotoxicity (CDC), ADCC, and direct apoptosis",
        "primary_context": "lymphoma",
        "off_target_effects": {
            "bone_marrow": "myelosuppression_from_normal_B_cell_depletion",
            "spleen": "splenic_B_cell_depletion",
        },
    },
}

# Dose thresholds for therapeutic isotopes (Gy for meaningful effect)
_THERAPEUTIC_DOSE_THRESHOLDS: dict[str, dict[str, float]] = {
    "Lu-177": {"min_tumor_gy": 20.0, "strong_tumor_gy": 60.0},
    "Y-90": {"min_tumor_gy": 30.0, "strong_tumor_gy": 80.0},
    "Ac-225": {"min_tumor_gy": 5.0, "strong_tumor_gy": 15.0},  # Alpha: lower dose needed
    "I-131": {"min_tumor_gy": 25.0, "strong_tumor_gy": 70.0},
}

# Organ toxicity thresholds
_TOXICITY_THRESHOLDS: dict[str, float] = {
    "kidney": 23.0,
    "bone_marrow": 2.0,
    "liver": 30.0,
    "salivary_glands": 25.0,
    "heart": 25.0,
    "lungs": 20.0,
}

# Therapeutic isotopes
_THERAPEUTIC_ISOTOPES = {"Lu-177", "Y-90", "Ac-225", "I-131"}


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

class PDResult:
    """Output of the PD/Effect Engine."""

    def __init__(self) -> None:
        self.effect_direction: str = "unknown"
        self.effect_type: str = "unknown"  # radiotheranostic, targeted, occupancy
        self.target_engagement_score: float = 0.0
        self.biological_plausibility_score: float = 0.0
        self.confidence_score: float = 0.0
        self.rationale_text: str = ""
        self.toxicity_risks: list[dict[str, Any]] = []
        self.occupancy_estimate: Optional[float] = None
        self.rules_activated: list[str] = []
        self.formulas_used: list[str] = []
        self.thresholds_used: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "effect_direction": self.effect_direction,
            "effect_type": self.effect_type,
            "target_engagement_score": round(self.target_engagement_score, 3),
            "biological_plausibility_score": round(self.biological_plausibility_score, 3),
            "confidence_score": round(self.confidence_score, 3),
            "rationale_text": self.rationale_text,
            "toxicity_risks": self.toxicity_risks,
            "occupancy_estimate": round(self.occupancy_estimate, 3) if self.occupancy_estimate is not None else None,
            "rules_activated": self.rules_activated,
            "formulas_used": self.formulas_used,
            "thresholds_used": self.thresholds_used,
        }


# ---------------------------------------------------------------------------
# PD Engine service
# ---------------------------------------------------------------------------

class PDEngine:
    """Module 6: Estimate biological effect from PK/dosimetry results."""

    def evaluate(
        self,
        request: NormalizedRequest,
        params: BuiltParameters,
        simulation_metrics: dict[str, Any],
        dosimetry: Optional[dict[str, Any]],
        logger: PipelineLogger,
    ) -> PDResult:
        """Evaluate PD effect.

        Args:
            request: Normalized input request.
            params: Built parameters from Parameter Builder.
            simulation_metrics: Key metrics from PBPK (tumor_uptake, TBR, etc.).
            dosimetry: Dosimetry results if therapeutic isotope.
            logger: Pipeline logger.
        """
        with ModuleTimer(logger, MODULE, "pd_evaluation"):
            return self._do_evaluate(request, params, simulation_metrics, dosimetry, logger)

    def _do_evaluate(
        self,
        req: NormalizedRequest,
        params: BuiltParameters,
        sim: dict[str, Any],
        dosimetry: Optional[dict[str, Any]],
        logger: PipelineLogger,
    ) -> PDResult:
        result = PDResult()
        target = req.target
        isotope = req.agent.isotope

        # 1. Target occupancy (always computed)
        self._compute_occupancy(req, params, sim, result, logger)

        # 2. Radiotheranostic PD (if therapeutic isotope)
        if isotope and isotope in _THERAPEUTIC_ISOTOPES and dosimetry:
            self._evaluate_radiotheranostic(
                target, isotope, dosimetry, result, logger
            )
        elif isotope and isotope not in _THERAPEUTIC_ISOTOPES:
            # Diagnostic isotope: effect is imaging, not therapeutic
            result.effect_type = "diagnostic"
            result.effect_direction = "imaging_visualization"
            result.rules_activated.append("diagnostic_isotope_no_therapeutic_effect")
            logger.info(MODULE, "diagnostic_mode", data={
                "isotope": isotope,
                "note": "Diagnostic isotope — no therapeutic effect modeled",
            })
        else:
            # No isotope: targeted PD
            self._evaluate_targeted_pd(target, result, logger)

        # 3. Causal rules
        self._apply_causal_rules(target, result, logger)

        # 4. Compute plausibility and confidence
        self._compute_scores(req, params, result, logger)

        # 5. Build rationale
        result.rationale_text = self._build_rationale(req, result)

        logger.audit(MODULE, "pd_evaluation_complete", data=result.to_dict(),
                     confidence=result.confidence_score)

        return result

    def _compute_occupancy(
        self, req: NormalizedRequest, params: BuiltParameters,
        sim: dict[str, Any], result: PDResult, logger: PipelineLogger,
    ) -> None:
        """Compute target occupancy: C / (C + Kd)."""
        tumor_conc = sim.get("tumor_peak_concentration_nM", 0)
        kd = params.binding.kd_nM

        if kd > 0 and tumor_conc > 0:
            occupancy = tumor_conc / (tumor_conc + kd)
        else:
            occupancy = 0.0

        result.occupancy_estimate = occupancy
        result.target_engagement_score = occupancy
        result.formulas_used.append(f"occupancy = C/(C+Kd) = {tumor_conc:.1f}/({tumor_conc:.1f}+{kd:.1f}) = {occupancy:.3f}")

        logger.info(MODULE, "occupancy_computed", data={
            "tumor_concentration_nM": tumor_conc,
            "kd_nM": kd,
            "occupancy": round(occupancy, 3),
        }, confidence=0.70)

    def _evaluate_radiotheranostic(
        self, target: str, isotope: str,
        dosimetry: dict[str, Any], result: PDResult,
        logger: PipelineLogger,
    ) -> None:
        """Evaluate radiotheranostic PD: dose-based effect prediction."""
        result.effect_type = "radiotheranostic"
        thresholds = _THERAPEUTIC_DOSE_THRESHOLDS.get(isotope, {})
        result.thresholds_used = thresholds

        tumor_dose = dosimetry.get("tumor_dose_gy_per_gbq", 0)
        dose_gbq = dosimetry.get("injected_gbq", 7.4)
        total_tumor_dose = tumor_dose * dose_gbq

        min_gy = thresholds.get("min_tumor_gy", 20)
        strong_gy = thresholds.get("strong_tumor_gy", 60)

        if total_tumor_dose >= strong_gy:
            result.effect_direction = "strong_cytotoxic_effect"
            result.target_engagement_score = min(1.0, result.target_engagement_score + 0.3)
            result.rules_activated.append("strong_tumor_dose_threshold_exceeded")
        elif total_tumor_dose >= min_gy:
            result.effect_direction = "moderate_cytotoxic_effect"
            result.rules_activated.append("min_tumor_dose_threshold_exceeded")
        else:
            result.effect_direction = "subtherapeutic_dose"
            result.rules_activated.append("tumor_dose_below_threshold")

        # Toxicity assessment
        organ_doses = dosimetry.get("organ_doses_gy_per_gbq", {})
        for organ, threshold in _TOXICITY_THRESHOLDS.items():
            organ_dose = organ_doses.get(organ, 0) * dose_gbq
            if organ_dose > threshold * 0.8:
                severity = "high" if organ_dose > threshold else "moderate"
                result.toxicity_risks.append({
                    "organ": organ,
                    "estimated_dose_gy": round(organ_dose, 2),
                    "threshold_gy": threshold,
                    "severity": severity,
                })
                result.rules_activated.append(f"toxicity_risk_{organ}_{severity}")

        logger.info(MODULE, "radiotheranostic_pd", data={
            "isotope": isotope,
            "total_tumor_dose_gy": round(total_tumor_dose, 2),
            "effect_direction": result.effect_direction,
            "toxicity_risks_count": len(result.toxicity_risks),
        })

    def _evaluate_targeted_pd(
        self, target: str, result: PDResult, logger: PipelineLogger,
    ) -> None:
        """Evaluate non-radioactive targeted PD."""
        result.effect_type = "targeted"
        rule = _CAUSAL_RULES.get(target)
        if rule:
            result.effect_direction = rule["effect_direction"]
            result.rules_activated.append(f"causal_rule_{target}")
        else:
            result.effect_direction = "unknown_target_effect"
            result.rules_activated.append("no_causal_rule_available")

        logger.info(MODULE, "targeted_pd", data={
            "target": target,
            "effect_direction": result.effect_direction,
        })

    def _apply_causal_rules(
        self, target: str, result: PDResult, logger: PipelineLogger,
    ) -> None:
        """Apply causal rules for off-target effects."""
        rule = _CAUSAL_RULES.get(target)
        if not rule:
            return

        for organ, effect in rule.get("off_target_effects", {}).items():
            # Check if this organ is already in toxicity risks
            already_flagged = any(
                r["organ"] == organ for r in result.toxicity_risks
            )
            if not already_flagged:
                result.toxicity_risks.append({
                    "organ": organ,
                    "effect": effect,
                    "source": "causal_rule",
                    "severity": "potential",
                })

    def _compute_scores(
        self, req: NormalizedRequest, params: BuiltParameters,
        result: PDResult, logger: PipelineLogger,
    ) -> None:
        """Compute plausibility and confidence scores."""
        # Biological plausibility
        plausibility = 0.3  # baseline
        if result.occupancy_estimate and result.occupancy_estimate > 0.5:
            plausibility += 0.3
        if result.effect_type == "radiotheranostic":
            plausibility += 0.2
        if _CAUSAL_RULES.get(req.target):
            plausibility += 0.2
        result.biological_plausibility_score = min(1.0, plausibility)

        # Confidence
        confidence = 0.3  # baseline
        if params.confidence_per_param.get("binding", 0) > 0.6:
            confidence += 0.2
        if result.effect_type != "unknown":
            confidence += 0.2
        if req.target in _CAUSAL_RULES:
            confidence += 0.15
        result.confidence_score = min(1.0, confidence)

    def _build_rationale(self, req: NormalizedRequest, result: PDResult) -> str:
        """Build human-readable rationale text."""
        parts = []
        rule = _CAUSAL_RULES.get(req.target)

        if result.effect_type == "radiotheranostic":
            parts.append(
                f"Radiotheranostic approach targeting {req.target} with {req.agent.isotope}."
            )
            parts.append(f"Predicted effect: {result.effect_direction.replace('_', ' ')}.")
            if rule:
                parts.append(f"Mechanism: {rule['mechanism']}")
        elif result.effect_type == "diagnostic":
            parts.append(
                f"Diagnostic imaging of {req.target} with {req.agent.isotope}. "
                "No therapeutic effect expected."
            )
        elif result.effect_type == "targeted":
            if rule:
                parts.append(f"Targeted therapy against {req.target}.")
                parts.append(f"Expected effect: {rule['effect_when_targeted'].replace('_', ' ')}.")
                parts.append(f"Mechanism: {rule['mechanism']}")

        if result.occupancy_estimate is not None:
            parts.append(
                f"Estimated target occupancy: {result.occupancy_estimate:.0%}."
            )

        if result.toxicity_risks:
            risk_organs = [r["organ"] for r in result.toxicity_risks if r.get("severity") in ("high", "moderate")]
            if risk_organs:
                parts.append(
                    f"Toxicity concerns: {', '.join(risk_organs)}."
                )

        return " ".join(parts)
