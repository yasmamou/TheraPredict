"""Parameter Builder — Module 3 of TheraPredict V1 pipeline.

Transforms biological knowledge + agent properties into parameters
usable by the PBPK/PD engines.

This is the core business logic module. Every rule is explicit, logged,
and traceable.
"""

from __future__ import annotations

import math
from typing import Any, Optional

from theranostics.services.input_normalizer import NormalizedRequest
from theranostics.services.knowledge_layer import TargetKnowledge
from theranostics.services.logging_service import PipelineLogger, ModuleTimer

MODULE = "parameter_builder"


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

class PKParameters:
    """PK parameters for the PBPK engine."""

    def __init__(self) -> None:
        self.clearance_route: str = "renal"
        self.half_life_h: float = 6.0
        self.total_clearance_l_per_h: float = 0.1
        self.volume_of_distribution_l: float = 5.0
        self.renal_fraction: float = 0.6
        self.hepatic_fraction: float = 0.2
        self.partition_coefficients: dict[str, float] = {}
        self.bbb_permeability: float = 0.01
        self.extravasation_rates: dict[str, float] = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "clearance_route": self.clearance_route,
            "half_life_h": self.half_life_h,
            "total_clearance_l_per_h": round(self.total_clearance_l_per_h, 4),
            "volume_of_distribution_l": round(self.volume_of_distribution_l, 2),
            "renal_fraction": round(self.renal_fraction, 3),
            "hepatic_fraction": round(self.hepatic_fraction, 3),
            "partition_coefficients": {k: round(v, 3) for k, v in self.partition_coefficients.items()},
            "bbb_permeability": self.bbb_permeability,
        }


class BindingParameters:
    """Binding kinetics parameters."""

    def __init__(self) -> None:
        self.kd_nM: float = 5.0
        self.kon_per_M_per_s: float = 1e5
        self.koff_per_s: float = 5e-4
        self.internalization_rate_per_h: float = 0.05
        self.kon_per_nM_per_h: float = 0.0
        self.koff_per_h: float = 0.0

    def compute_derived(self) -> None:
        self.kon_per_nM_per_h = self.kon_per_M_per_s * 1e-9 * 3600
        self.koff_per_h = self.koff_per_s * 3600

    def to_dict(self) -> dict[str, Any]:
        return {
            "kd_nM": self.kd_nM,
            "kon_per_M_per_s": self.kon_per_M_per_s,
            "koff_per_s": self.koff_per_s,
            "kon_per_nM_per_h": round(self.kon_per_nM_per_h, 6),
            "koff_per_h": round(self.koff_per_h, 4),
            "internalization_rate_per_h": self.internalization_rate_per_h,
        }


class TumorParameters:
    """Tumor-specific parameters."""

    def __init__(self) -> None:
        self.penetration_score: float = 0.5
        self.binding_site_barrier_penalty: float = 0.0
        self.tumor_target_density_nM: float = 100.0
        self.thiele_modulus: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "penetration_score": round(self.penetration_score, 3),
            "binding_site_barrier_penalty": round(self.binding_site_barrier_penalty, 3),
            "tumor_target_density_nM": round(self.tumor_target_density_nM, 1),
            "thiele_modulus": round(self.thiele_modulus, 2),
        }


class RiskParameters:
    """Off-target and risk parameters."""

    def __init__(self) -> None:
        self.off_target_organs: list[str] = []
        self.off_target_scores: dict[str, float] = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "off_target_organs": self.off_target_organs,
            "off_target_scores": {k: round(v, 3) for k, v in self.off_target_scores.items()},
        }


class BuiltParameters:
    """Complete parameter set built by the Parameter Builder."""

    def __init__(self) -> None:
        self.pk = PKParameters()
        self.binding = BindingParameters()
        self.tumor = TumorParameters()
        self.risk = RiskParameters()
        self.tissue_target_densities: dict[str, float] = {}
        self.rules_applied: list[str] = []
        self.rules_skipped: list[str] = []
        self.hypotheses: list[str] = []
        self.confidence_per_param: dict[str, float] = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "pk_params": self.pk.to_dict(),
            "binding_params": self.binding.to_dict(),
            "tumor_params": self.tumor.to_dict(),
            "risk_params": self.risk.to_dict(),
            "tissue_target_densities": {k: round(v, 2) for k, v in self.tissue_target_densities.items()},
            "rules_applied": self.rules_applied,
            "rules_skipped": self.rules_skipped,
            "hypotheses": self.hypotheses,
            "confidence_per_param": self.confidence_per_param,
        }


# ---------------------------------------------------------------------------
# Parameter Builder service
# ---------------------------------------------------------------------------

class ParameterBuilder:
    """Module 3: Transform knowledge + agent into PBPK/PD parameters."""

    def build(
        self,
        request: NormalizedRequest,
        knowledge: TargetKnowledge,
        logger: PipelineLogger,
    ) -> BuiltParameters:
        with ModuleTimer(logger, MODULE, "parameter_build"):
            return self._do_build(request, knowledge, logger)

    def _do_build(
        self,
        req: NormalizedRequest,
        knowledge: TargetKnowledge,
        logger: PipelineLogger,
    ) -> BuiltParameters:
        params = BuiltParameters()
        agent = req.agent

        # === 7.1 Clearance ===
        self._build_clearance(agent, params, logger)

        # === 7.2 Tumor penetration ===
        self._build_penetration(agent, params, logger)

        # === 7.3 Off-target ===
        self._build_off_target(knowledge, agent, params, logger)

        # === 7.4 BBB permeability ===
        self._build_bbb(agent, params, logger)

        # === 7.5 Kon / Koff ===
        self._build_binding(agent, params, logger)

        # === 7.6 Tissue target densities ===
        self._build_tissue_densities(req, knowledge, params, logger)

        # === Partition coefficients ===
        self._build_partition_coefficients(agent, knowledge, params, logger)

        # === Extravasation rates ===
        self._build_extravasation(agent, params, logger)

        # Log summary
        logger.audit(MODULE, "parameters_built", data={
            "rules_applied": params.rules_applied,
            "rules_skipped": params.rules_skipped,
            "hypotheses": params.hypotheses,
            "confidence_per_param": params.confidence_per_param,
        })

        return params

    # -- 7.1 Clearance --------------------------------------------------------

    def _build_clearance(
        self, agent: Any, params: BuiltParameters, logger: PipelineLogger
    ) -> None:
        size = agent.size_kDa
        agent_class = agent.agent_class

        if size < 60:
            params.pk.clearance_route = "renal"
            params.pk.renal_fraction = agent.renal_filtration_fraction or 0.6
            params.pk.hepatic_fraction = agent.hepatic_clearance_fraction or 0.2
            params.rules_applied.append("renal_clearance_if_size_lt_60kDa")
            params.confidence_per_param["clearance_route"] = 0.85
            logger.info(MODULE, "rule_applied", data={
                "rule": "renal_clearance_if_size_lt_60kDa",
                "input": {"size_kDa": size},
                "output": {"clearance_route": "renal"},
            }, confidence=0.85)
        else:
            if agent_class == "IgG" and agent.has_fc_region:
                params.pk.clearance_route = "hepatic_with_FcRn_recycling"
                params.pk.hepatic_fraction = (agent.hepatic_clearance_fraction or 0.3) * 0.3
                params.pk.renal_fraction = 0.0
                params.rules_applied.append("hepatic_FcRn_recycling_for_IgG")
                params.hypotheses.append(
                    "IgG FcRn recycling reduces hepatic clearance by ~70%"
                )
                params.confidence_per_param["clearance_route"] = 0.80
                logger.info(MODULE, "rule_applied", data={
                    "rule": "hepatic_FcRn_recycling_for_IgG",
                    "input": {"size_kDa": size, "has_fc": True},
                    "output": {"clearance_route": "hepatic_with_FcRn_recycling"},
                }, confidence=0.80)
            else:
                params.pk.clearance_route = "hepatic_RES"
                params.pk.hepatic_fraction = agent.hepatic_clearance_fraction or 0.5
                params.pk.renal_fraction = 0.0
                params.rules_applied.append("hepatic_RES_if_size_gte_60kDa")
                params.confidence_per_param["clearance_route"] = 0.70
                logger.info(MODULE, "rule_applied", data={
                    "rule": "hepatic_RES_if_size_gte_60kDa",
                    "input": {"size_kDa": size},
                    "output": {"clearance_route": "hepatic_RES"},
                }, confidence=0.70)

        # Half-life
        if agent.plasma_half_life_hours:
            params.pk.half_life_h = agent.plasma_half_life_hours
            params.confidence_per_param["half_life"] = 0.80
        else:
            # Estimate from class
            _class_halflife = {
                "small_molecule": 4.0, "peptide": 2.0, "nanobody": 3.0,
                "Fab": 15.0, "IgG": 450.0,
            }
            params.pk.half_life_h = _class_halflife.get(agent.agent_class, 6.0)
            params.rules_applied.append(f"half_life_from_class_default={agent.agent_class}")
            params.confidence_per_param["half_life"] = 0.50
            logger.warning(MODULE, "default_used", data={
                "parameter": "half_life_h",
                "value": params.pk.half_life_h,
                "reason": "No half-life provided, using class default",
            })

        # Vd
        if agent.agent_class == "IgG":
            params.pk.volume_of_distribution_l = 3.5
        elif agent.agent_class in ("small_molecule", "peptide"):
            params.pk.volume_of_distribution_l = max(10.0, agent.size_kDa * 5)
        else:
            params.pk.volume_of_distribution_l = max(5.0, agent.size_kDa * 0.3)

        # Total clearance = ln2 / t½ × Vd
        params.pk.total_clearance_l_per_h = (
            0.693147 / params.pk.half_life_h * params.pk.volume_of_distribution_l
        )

    # -- 7.2 Tumor penetration ------------------------------------------------

    def _build_penetration(
        self, agent: Any, params: BuiltParameters, logger: PipelineLogger
    ) -> None:
        size = agent.size_kDa
        kd = agent.kd_nM or 5.0
        agent_class = agent.agent_class

        # Thurber-inspired heuristic
        # High affinity + large size = binding site barrier
        if agent_class in ("small_molecule", "peptide"):
            base_penetration = 0.85
            barrier_penalty = 0.0
            params.rules_applied.append("high_penetration_small_agent")
        elif agent_class == "nanobody":
            base_penetration = 0.70
            barrier_penalty = 0.05 if kd < 1.0 else 0.0
            params.rules_applied.append("moderate_high_penetration_nanobody")
        elif agent_class == "Fab":
            base_penetration = 0.55
            barrier_penalty = 0.10 if kd < 1.0 else 0.03
            params.rules_applied.append("moderate_penetration_Fab")
        else:  # IgG
            base_penetration = 0.35
            barrier_penalty = 0.20 if kd < 1.0 else 0.10
            params.rules_applied.append("low_penetration_IgG")

        # Size penalty
        size_penalty = min(0.3, max(0, (size - 50) / 500))
        penetration = max(0.05, base_penetration - size_penalty - barrier_penalty)

        # Thiele modulus approximation
        D = agent.interstitial_diffusivity_cm2_per_s or 1e-7
        kon = agent.kon_per_M_per_s or 1e5
        R_krogh = 0.005  # ~50 µm in cm
        Ag = 100e-9  # 100 nM reference
        phi_sq = (R_krogh ** 2) * kon * Ag / D
        phi = math.sqrt(phi_sq) if phi_sq > 0 else 0

        params.tumor.penetration_score = round(penetration, 3)
        params.tumor.binding_site_barrier_penalty = round(barrier_penalty, 3)
        params.tumor.thiele_modulus = round(phi, 2)
        params.confidence_per_param["penetration"] = 0.60

        logger.info(MODULE, "rule_applied", data={
            "rule": "tumor_penetration",
            "input": {"size_kDa": size, "kd_nM": kd, "class": agent_class},
            "output": {
                "penetration_score": penetration,
                "barrier_penalty": barrier_penalty,
                "thiele_modulus": phi,
            },
        }, confidence=0.60)

    # -- 7.3 Off-target -------------------------------------------------------

    def _build_off_target(
        self, knowledge: TargetKnowledge, agent: Any,
        params: BuiltParameters, logger: PipelineLogger,
    ) -> None:
        off_target: dict[str, float] = {}

        # For each tissue with expression, compute off-target score
        # score = expression × exposure_probability
        exposure_map = self._estimate_exposure_map(agent)

        for tissue, expression in knowledge.normal_tissue_expression.items():
            if expression > 0.10:  # Only care about meaningful expression
                exposure = exposure_map.get(tissue, 0.3)
                score = expression * exposure
                if score > 0.05:
                    off_target[tissue] = round(score, 3)

        # Sort by score descending
        off_target = dict(sorted(off_target.items(), key=lambda x: x[1], reverse=True))

        params.risk.off_target_scores = off_target
        params.risk.off_target_organs = [t for t, s in off_target.items() if s > 0.15]
        params.rules_applied.append("off_target_expression_x_exposure")
        params.confidence_per_param["off_target"] = 0.55

        logger.info(MODULE, "rule_applied", data={
            "rule": "off_target_expression_x_exposure",
            "output": {"off_target_organs": params.risk.off_target_organs},
        }, confidence=0.55)

    def _estimate_exposure_map(self, agent: Any) -> dict[str, float]:
        """Estimate relative exposure per tissue based on agent class."""
        base = {
            "kidney": 0.7, "liver": 0.8, "spleen": 0.6,
            "gut": 0.5, "lungs": 0.5, "bone_marrow": 0.4,
            "heart": 0.4, "salivary_glands": 0.4, "muscle": 0.3,
            "skin": 0.3, "brain": 0.05, "lymph_nodes": 0.3,
            "adrenals": 0.4, "pancreas": 0.4, "prostate": 0.4,
            "breast": 0.3, "joints": 0.3, "uterus": 0.3,
        }
        if agent.agent_class in ("small_molecule", "peptide"):
            base["kidney"] = 0.9  # Renal clearance → high kidney exposure
        if agent.agent_class == "IgG" and agent.has_fc_region:
            base["liver"] = 0.9
            base["spleen"] = 0.8
        return base

    # -- 7.4 BBB permeability -------------------------------------------------

    def _build_bbb(
        self, agent: Any, params: BuiltParameters, logger: PipelineLogger
    ) -> None:
        agent_class = agent.agent_class
        size = agent.size_kDa

        if agent_class == "IgG":
            bbb = 0.001
            rule = "bbb_very_low_IgG"
        elif agent_class == "Fab":
            bbb = 0.002
            rule = "bbb_very_low_Fab"
        elif agent_class == "nanobody":
            bbb = 0.005
            rule = "bbb_very_low_nanobody"
        elif agent_class == "peptide":
            bbb = 0.02
            rule = "bbb_low_to_moderate_peptide"
        elif agent_class == "small_molecule":
            # Variable, depends on lipophilicity (not modeled in V1)
            bbb = 0.05
            rule = "bbb_variable_small_molecule"
            params.hypotheses.append(
                "BBB permeability for small molecules is variable; "
                "using moderate default without lipophilicity data"
            )
        else:
            bbb = 0.01
            rule = "bbb_default"

        params.pk.bbb_permeability = bbb
        params.rules_applied.append(rule)
        params.confidence_per_param["bbb"] = 0.50

        logger.info(MODULE, "rule_applied", data={
            "rule": rule,
            "input": {"class": agent_class, "size_kDa": size},
            "output": {"bbb_permeability": bbb},
        }, confidence=0.50)

    # -- 7.5 Kon / Koff -------------------------------------------------------

    def _build_binding(
        self, agent: Any, params: BuiltParameters, logger: PipelineLogger
    ) -> None:
        kd = agent.kd_nM
        kon = agent.kon_per_M_per_s
        koff = agent.koff_per_s

        if kd is not None and kon is not None and koff is None:
            koff = kd * 1e-9 * kon
            params.rules_applied.append("koff_derived_from_Kd_and_kon")
            params.confidence_per_param["koff"] = 0.80
            logger.info(MODULE, "rule_applied", data={
                "rule": "koff_derived_from_Kd_and_kon",
                "input": {"kd_nM": kd, "kon": kon},
                "output": {"koff_per_s": koff},
            }, confidence=0.80)
        elif kd is None:
            # Use class default
            _class_kd = {
                "small_molecule": 5.0, "peptide": 2.0, "nanobody": 5.0,
                "Fab": 1.0, "IgG": 1.0,
            }
            kd = _class_kd.get(agent.agent_class, 5.0)
            if kon is None:
                kon = 1e5
            koff = kd * 1e-9 * kon
            params.rules_applied.append("kd_from_class_default")
            params.confidence_per_param["kd"] = 0.40
            logger.warning(MODULE, "default_used", data={
                "parameter": "kd_nM",
                "value": kd,
                "reason": "No Kd provided, using class default",
            })

        if koff is None:
            koff = 1e-4
        if kon is None:
            kon = 1e5

        params.binding.kd_nM = kd or 5.0
        params.binding.kon_per_M_per_s = kon
        params.binding.koff_per_s = koff

        # Internalization rate
        int_rate_map = {
            "small_molecule": 0.15, "peptide": 0.12, "nanobody": 0.08,
            "Fab": 0.05, "IgG": 0.03,
        }
        if agent.internalization:
            params.binding.internalization_rate_per_h = int_rate_map.get(agent.agent_class, 0.05)
        else:
            params.binding.internalization_rate_per_h = 0.005  # Minimal
            params.hypotheses.append("Agent does not internalize; minimal internalization rate")

        params.binding.compute_derived()
        params.confidence_per_param["binding"] = 0.70

    # -- 7.6 Tissue target densities ------------------------------------------

    def _build_tissue_densities(
        self, req: NormalizedRequest, knowledge: TargetKnowledge,
        params: BuiltParameters, logger: PipelineLogger,
    ) -> None:
        """Convert expression scores to approximate target density in nM."""
        # Reference density: tumor is the anchor
        if req.tumor.target_expression_override is not None:
            tumor_density = req.tumor.target_expression_override * 200.0
        else:
            tumor_density = knowledge.tumor_expression_score * 200.0

        params.tumor.tumor_target_density_nM = tumor_density

        # Normal tissues: scale relative to tumor
        max_normal_expr = max(knowledge.normal_tissue_expression.values()) if knowledge.normal_tissue_expression else 1.0
        for tissue, score in knowledge.normal_tissue_expression.items():
            # Density proportional to expression score
            density = score * 200.0  # Same scale as tumor
            params.tissue_target_densities[tissue] = density

        params.rules_applied.append("tissue_density_from_expression_scores")
        params.confidence_per_param["tissue_densities"] = 0.55

        logger.info(MODULE, "rule_applied", data={
            "rule": "tissue_density_from_expression_scores",
            "output": {
                "tumor_density_nM": tumor_density,
                "tissue_count": len(params.tissue_target_densities),
            },
        }, confidence=0.55)

    # -- Partition coefficients -----------------------------------------------

    def _build_partition_coefficients(
        self, agent: Any, knowledge: TargetKnowledge,
        params: BuiltParameters, logger: PipelineLogger,
    ) -> None:
        """Build tissue:plasma partition coefficients (Kp)."""
        # Base Kp depends on vascular permeability
        if agent.agent_class in ("small_molecule", "peptide"):
            base_kp = 0.6
        elif agent.agent_class == "nanobody":
            base_kp = 0.4
        elif agent.agent_class == "Fab":
            base_kp = 0.35
        else:  # IgG
            base_kp = 0.3

        kp = {
            "lungs": base_kp * 0.8,
            "liver": base_kp * 1.2,  # Fenestrated
            "kidney": base_kp * 1.1,  # Fenestrated
            "spleen": base_kp * 1.3,  # Open sinusoids
            "heart": base_kp * 0.9,
            "muscle": base_kp * 0.6,
            "bone_marrow": base_kp * 1.0,
            "skin": base_kp * 0.7,
            "gut": base_kp * 1.0,
            "brain": params.pk.bbb_permeability * 2,  # BBB limited
            "salivary_glands": base_kp * 0.9,
            "bone": base_kp * 0.3,
            "rest_of_body": base_kp * 0.8,
            "tumor": base_kp * 1.4,  # Enhanced permeability
        }

        # Boost Kp for organs with high target expression
        for tissue, density in params.tissue_target_densities.items():
            if tissue in kp and density > 50:
                boost = min(0.5, density / 400)
                kp[tissue] = kp.get(tissue, base_kp) + boost

        params.pk.partition_coefficients = kp
        params.rules_applied.append("partition_coefficients_from_agent_class")
        params.confidence_per_param["Kp"] = 0.55

    # -- Extravasation rates --------------------------------------------------

    def _build_extravasation(
        self, agent: Any, params: BuiltParameters, logger: PipelineLogger
    ) -> None:
        """Build extravasation rates per tissue."""
        perm = agent.vascular_permeability_cm_per_s or 3e-8

        # Convert to rate per hour (approximate)
        base_rate = perm * 3600 * 100  # cm/s → cm/h → rough rate/h

        rates = {
            "lungs": base_rate * 1.0,
            "liver": base_rate * 5.0,   # Fenestrated
            "kidney": base_rate * 4.0,  # Fenestrated
            "spleen": base_rate * 6.0,  # Open sinusoids
            "heart": base_rate * 1.0,
            "muscle": base_rate * 0.5,
            "bone_marrow": base_rate * 3.0,
            "skin": base_rate * 0.8,
            "gut": base_rate * 3.0,
            "brain": base_rate * 0.01,  # BBB
            "salivary_glands": base_rate * 2.0,
            "bone": base_rate * 0.3,
            "rest_of_body": base_rate * 1.0,
            "tumor": base_rate * 2.0,   # EPR effect
        }

        params.pk.extravasation_rates = rates
        params.rules_applied.append("extravasation_from_vascular_permeability")
