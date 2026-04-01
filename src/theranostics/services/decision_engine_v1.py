"""Decision Engine V1 — Module 7 of TheraPredict V1 pipeline.

Transparent scoring with visible weights. Produces:
- recommended option
- top alternatives
- why / why not
- all intermediate scores visible
"""

from __future__ import annotations

from typing import Any, Optional

from theranostics.services.logging_service import PipelineLogger, ModuleTimer

MODULE = "decision_engine"


# ---------------------------------------------------------------------------
# Scoring weights (V1 defaults, configurable)
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = {
    "efficacy": 0.40,
    "safety": 0.30,
    "practicality": 0.15,
    "confidence": 0.15,
}


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

class StrategyScoreV1:
    """Transparent strategy score with all sub-components visible."""

    def __init__(self) -> None:
        # Sub-scores
        self.tumor_uptake_score: float = 0.0
        self.tbr_score: float = 0.0
        self.target_engagement_score: float = 0.0
        self.penetration_score: float = 0.0

        self.organ_safety_score: float = 1.0
        self.off_target_penalty: float = 0.0
        self.dosimetry_safety_score: float = 1.0

        self.isotope_availability_score: float = 0.5
        self.imaging_feasibility_score: float = 0.5
        self.agent_complexity_score: float = 0.5

        self.data_quality_score: float = 0.5
        self.mc_stability_score: float = 0.5
        self.evidence_level_score: float = 0.5

        # Aggregated
        self.efficacy: float = 0.0
        self.safety: float = 0.0
        self.practicality: float = 0.0
        self.confidence: float = 0.0
        self.combined: float = 0.0

        # Weights used
        self.weights: dict[str, float] = dict(DEFAULT_WEIGHTS)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sub_scores": {
                "tumor_uptake": round(self.tumor_uptake_score, 3),
                "tbr": round(self.tbr_score, 3),
                "target_engagement": round(self.target_engagement_score, 3),
                "penetration": round(self.penetration_score, 3),
                "organ_safety": round(self.organ_safety_score, 3),
                "off_target_penalty": round(self.off_target_penalty, 3),
                "dosimetry_safety": round(self.dosimetry_safety_score, 3),
                "isotope_availability": round(self.isotope_availability_score, 3),
                "imaging_feasibility": round(self.imaging_feasibility_score, 3),
                "data_quality": round(self.data_quality_score, 3),
                "mc_stability": round(self.mc_stability_score, 3),
                "evidence_level": round(self.evidence_level_score, 3),
            },
            "aggregated": {
                "efficacy": round(self.efficacy, 3),
                "safety": round(self.safety, 3),
                "practicality": round(self.practicality, 3),
                "confidence": round(self.confidence, 3),
                "combined": round(self.combined, 3),
            },
            "weights": self.weights,
        }


class DecisionResultV1:
    """Decision engine output for a single strategy."""

    def __init__(self) -> None:
        self.agent_name: str = ""
        self.isotope: Optional[str] = None
        self.score: StrategyScoreV1 = StrategyScoreV1()
        self.rank: int = 0
        self.why: list[str] = []
        self.why_not: list[str] = []
        self.summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "isotope": self.isotope,
            "rank": self.rank,
            "score": self.score.to_dict(),
            "why": self.why,
            "why_not": self.why_not,
            "summary": self.summary,
        }


class DecisionReportV1:
    """Full decision report with ranking and comparisons."""

    def __init__(self) -> None:
        self.strategies: list[DecisionResultV1] = []
        self.recommended: Optional[DecisionResultV1] = None
        self.scoring_version: str = "v1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended": self.recommended.to_dict() if self.recommended else None,
            "all_strategies": [s.to_dict() for s in self.strategies],
            "scoring_version": self.scoring_version,
        }


# ---------------------------------------------------------------------------
# Decision Engine
# ---------------------------------------------------------------------------

class DecisionEngineV1:
    """Module 7: Score, rank, and recommend strategies."""

    def __init__(self, weights: Optional[dict[str, float]] = None) -> None:
        self.weights = weights or dict(DEFAULT_WEIGHTS)

    def score_strategy(
        self,
        agent_name: str,
        isotope: Optional[str],
        simulation_metrics: dict[str, Any],
        dosimetry: Optional[dict[str, Any]],
        pd_result: dict[str, Any],
        params: dict[str, Any],
        knowledge: dict[str, Any],
        logger: PipelineLogger,
    ) -> DecisionResultV1:
        """Score a single strategy."""
        with ModuleTimer(logger, MODULE, "scoring"):
            return self._do_score(
                agent_name, isotope, simulation_metrics, dosimetry,
                pd_result, params, knowledge, logger,
            )

    def _do_score(
        self,
        agent_name: str,
        isotope: Optional[str],
        sim: dict[str, Any],
        dosimetry: Optional[dict[str, Any]],
        pd: dict[str, Any],
        params: dict[str, Any],
        knowledge: dict[str, Any],
        logger: PipelineLogger,
    ) -> DecisionResultV1:
        result = DecisionResultV1()
        result.agent_name = agent_name
        result.isotope = isotope
        s = result.score
        s.weights = dict(self.weights)

        # === EFFICACY ===
        # Tumor uptake (normalize: 0.01 %ID/g → score 1.0 for antibodies)
        tumor_uptake = sim.get("tumor_uptake_value", 0)
        s.tumor_uptake_score = min(1.0, tumor_uptake / 50.0)  # 50 nM peak → good

        # TBR
        tbr = sim.get("tbr_value", 0)
        s.tbr_score = min(1.0, tbr / 20.0)

        # Target engagement from PD
        s.target_engagement_score = pd.get("target_engagement_score", 0)

        # Penetration from params
        s.penetration_score = params.get("tumor_params", {}).get("penetration_score", 0.5)

        s.efficacy = (
            0.30 * s.tumor_uptake_score
            + 0.25 * s.tbr_score
            + 0.25 * s.target_engagement_score
            + 0.20 * s.penetration_score
        )

        # === SAFETY ===
        s.organ_safety_score = 1.0

        # Off-target
        off_target = params.get("risk_params", {}).get("off_target_scores", {})
        total_off = sum(off_target.values())
        s.off_target_penalty = min(0.5, total_off * 0.1)
        s.organ_safety_score -= s.off_target_penalty

        # Dosimetry safety
        if dosimetry:
            organ_doses = dosimetry.get("organ_doses_gy_per_gbq", {})
            _tolerances = {"kidney": 23, "bone_marrow": 2, "liver": 30, "salivary_glands": 25}
            for organ, tol in _tolerances.items():
                dose = organ_doses.get(organ, 0)
                frac = dose / tol
                s.dosimetry_safety_score -= frac * 0.3
            s.dosimetry_safety_score = max(0, s.dosimetry_safety_score)

        s.safety = max(0, min(1.0, (s.organ_safety_score + s.dosimetry_safety_score) / 2))

        # === PRACTICALITY ===
        _isotope_avail = {
            "Ga-68": 0.9, "F-18": 0.9, "Lu-177": 0.8, "I-131": 0.8,
            "Zr-89": 0.5, "Y-90": 0.7, "Ac-225": 0.3,
        }
        s.isotope_availability_score = _isotope_avail.get(isotope or "", 0.5)

        optimal_time = sim.get("optimal_imaging_time", 24)
        if optimal_time < 4:
            s.imaging_feasibility_score = 0.9
        elif optimal_time < 24:
            s.imaging_feasibility_score = 0.7
        elif optimal_time < 72:
            s.imaging_feasibility_score = 0.5
        else:
            s.imaging_feasibility_score = 0.3

        s.practicality = (s.isotope_availability_score + s.imaging_feasibility_score) / 2

        # === CONFIDENCE ===
        evidence_map = {"A": 0.9, "B": 0.7, "C": 0.4, "D": 0.2}
        evidence_level = knowledge.get("target_profile", {}).get("evidence_level", "D")
        s.evidence_level_score = evidence_map.get(evidence_level, 0.3)

        mc_samples = sim.get("n_monte_carlo", 100)
        s.mc_stability_score = min(1.0, mc_samples / 200)

        s.data_quality_score = knowledge.get("confidence", 0.5)

        s.confidence = (
            0.40 * s.evidence_level_score
            + 0.30 * s.data_quality_score
            + 0.30 * s.mc_stability_score
        )

        # === COMBINED ===
        s.combined = (
            self.weights["efficacy"] * s.efficacy
            + self.weights["safety"] * s.safety
            + self.weights["practicality"] * s.practicality
            + self.weights["confidence"] * s.confidence
        )

        # === WHY / WHY NOT ===
        result.why = self._identify_strengths(s, sim, knowledge)
        result.why_not = self._identify_weaknesses(s, pd, params)
        result.summary = self._build_summary(agent_name, s, result.why, result.why_not)

        logger.audit(MODULE, "strategy_scored", data={
            "agent": agent_name,
            "isotope": isotope,
            "combined_score": round(s.combined, 3),
            "efficacy": round(s.efficacy, 3),
            "safety": round(s.safety, 3),
            "practicality": round(s.practicality, 3),
            "confidence": round(s.confidence, 3),
        })

        return result

    def rank_strategies(
        self, strategies: list[DecisionResultV1], logger: PipelineLogger,
    ) -> DecisionReportV1:
        """Rank strategies and produce report."""
        ranked = sorted(strategies, key=lambda s: s.score.combined, reverse=True)
        for i, s in enumerate(ranked):
            s.rank = i + 1

        report = DecisionReportV1()
        report.strategies = ranked
        report.recommended = ranked[0] if ranked else None

        logger.audit(MODULE, "strategies_ranked", data={
            "count": len(ranked),
            "top_agent": ranked[0].agent_name if ranked else "none",
            "top_score": round(ranked[0].score.combined, 3) if ranked else 0,
            "weights": self.weights,
        })

        return report

    def _identify_strengths(self, s: StrategyScoreV1, sim: dict, knowledge: dict) -> list[str]:
        strengths = []
        if s.tumor_uptake_score > 0.6:
            strengths.append("High tumor uptake")
        if s.tbr_score > 0.5:
            strengths.append(f"Good tumor-to-background ratio ({sim.get('tbr_value', 0):.1f})")
        if s.target_engagement_score > 0.7:
            strengths.append("High target engagement")
        if s.evidence_level_score > 0.7:
            strengths.append("Strong clinical evidence base")
        if s.isotope_availability_score > 0.7:
            strengths.append("Good isotope availability")
        return strengths

    def _identify_weaknesses(self, s: StrategyScoreV1, pd: dict, params: dict) -> list[str]:
        weaknesses = []
        if s.off_target_penalty > 0.2:
            organs = params.get("risk_params", {}).get("off_target_organs", [])
            weaknesses.append(f"Off-target risk: {', '.join(organs[:3])}")
        if s.dosimetry_safety_score < 0.5:
            weaknesses.append("Significant organ dose concerns")
        if s.penetration_score < 0.4:
            weaknesses.append("Poor tumor penetration predicted")
        if s.confidence < 0.4:
            weaknesses.append("Low confidence in predictions")
        toxicity = pd.get("toxicity_risks", [])
        for risk in toxicity[:2]:
            if risk.get("severity") in ("high", "moderate"):
                weaknesses.append(f"{risk['organ']}: {risk.get('effect', risk.get('severity', ''))} toxicity risk")
        return weaknesses

    def _build_summary(
        self, agent_name: str, s: StrategyScoreV1,
        why: list[str], why_not: list[str],
    ) -> str:
        if s.combined > 0.7:
            grade = "Strong candidate"
        elif s.combined > 0.5:
            grade = "Moderate candidate"
        else:
            grade = "Weak candidate"

        parts = [f"{agent_name}: {grade} (score {s.combined:.2f})."]
        if why:
            parts.append(f"Strengths: {why[0]}.")
        if why_not:
            parts.append(f"Key concern: {why_not[0]}.")
        return " ".join(parts)
