"""Decision Engine — rank candidate strategies and generate recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from theranostics.engines.target import TargetAssessment
from theranostics.engines.agent import AgentAssessment
from theranostics.models.simulation import SimulationResult, DosimetryResult


@dataclass
class StrategyScore:
    efficacy_score: float  # [0, 1]
    safety_score: float  # [0, 1]
    practical_score: float  # [0, 1]
    combined_score: float  # [0, 1]


@dataclass
class StrategyRecommendation:
    rank: int
    agent_name: str
    isotope: Optional[str]
    scores: StrategyScore
    key_drivers: list[str]
    risks: list[str]
    confidence: str
    summary: str


@dataclass
class DecisionReport:
    target_assessment: TargetAssessment
    ranked_strategies: list[StrategyRecommendation]
    overall_recommendation: str
    scientific_caveats: list[str]


class DecisionEngine:
    """Integrate all engine outputs to rank and recommend theranostic strategies."""

    def __init__(
        self,
        efficacy_weight: float = 0.45,
        safety_weight: float = 0.35,
        practical_weight: float = 0.20,
    ) -> None:
        self.w_eff = efficacy_weight
        self.w_safe = safety_weight
        self.w_prac = practical_weight

    def evaluate_strategy(
        self,
        target: TargetAssessment,
        agent_assessment: AgentAssessment,
        simulation: SimulationResult,
    ) -> StrategyRecommendation:
        """Evaluate a single strategy (target + agent + simulation)."""
        scores = self._compute_scores(target, agent_assessment, simulation)
        drivers = self._identify_drivers(target, agent_assessment, simulation)
        risks = self._identify_risks(target, agent_assessment, simulation)
        confidence = self._assess_confidence(target, agent_assessment, simulation)
        summary = self._generate_summary(
            agent_assessment.agent.name,
            scores,
            drivers,
            risks,
            confidence,
        )

        return StrategyRecommendation(
            rank=0,  # Set during ranking
            agent_name=agent_assessment.agent.name,
            isotope=agent_assessment.agent.isotope,
            scores=scores,
            key_drivers=drivers,
            risks=risks,
            confidence=confidence,
            summary=summary,
        )

    def rank_strategies(
        self,
        strategies: list[StrategyRecommendation],
    ) -> list[StrategyRecommendation]:
        """Rank strategies by combined score."""
        sorted_strategies = sorted(
            strategies, key=lambda s: s.scores.combined_score, reverse=True
        )
        for i, s in enumerate(sorted_strategies):
            s.rank = i + 1
        return sorted_strategies

    def generate_report(
        self,
        target: TargetAssessment,
        ranked_strategies: list[StrategyRecommendation],
    ) -> DecisionReport:
        """Generate a full decision report."""
        if ranked_strategies:
            best = ranked_strategies[0]
            overall = (
                f"Recommended strategy: {best.agent_name}"
                f" (score: {best.scores.combined_score:.2f}, "
                f"confidence: {best.confidence}). "
                f"{best.summary}"
            )
        else:
            overall = "No strategies could be evaluated."

        caveats = [
            "All predictions are based on mechanistic modeling with literature-derived parameters.",
            "Individual patient response may differ significantly from population-level predictions.",
            "Dosimetry estimates use simplified S-values and standard organ geometries.",
            "These results are for research and hypothesis generation, not clinical decision-making.",
        ]

        return DecisionReport(
            target_assessment=target,
            ranked_strategies=ranked_strategies,
            overall_recommendation=overall,
            scientific_caveats=caveats,
        )

    def _compute_scores(
        self,
        target: TargetAssessment,
        agent_assessment: AgentAssessment,
        simulation: SimulationResult,
    ) -> StrategyScore:
        """Compute efficacy, safety, and practical scores."""

        # === Efficacy ===
        # Tumor uptake (higher = better, normalize to [0,1])
        tumor_uptake = simulation.tumor_uptake_percent_id_per_g.value
        uptake_score = min(1.0, tumor_uptake / 0.01)  # 0.01 %ID/g = excellent for antibodies

        # TBR (higher = better)
        tbr = simulation.tumor_to_background_ratio.value
        tbr_score = min(1.0, tbr / 20.0)  # TBR of 20 = excellent

        # Target expression
        expression_score = target.expression_score

        # Penetration
        penetration_score = agent_assessment.penetration.uniformity_score

        efficacy = (
            0.30 * uptake_score
            + 0.25 * tbr_score
            + 0.25 * expression_score
            + 0.20 * penetration_score
        )

        # === Safety ===
        safety = 1.0

        # Off-target risk penalties
        for organ, risk in agent_assessment.off_target_risk.items():
            safety -= risk * 0.15

        # Dosimetry-based safety
        if simulation.dosimetry:
            for organ, dose in simulation.dosimetry.organ_doses_gy_per_gbq.items():
                if organ in ("tumor", "plasma"):
                    continue
                tolerance = _SIMPLE_TOLERANCES.get(organ, 50.0)
                fraction = dose / tolerance
                safety -= fraction * 0.2

        safety = max(0.0, min(1.0, safety))

        # === Practical ===
        practical = 0.5  # baseline

        # Isotope availability
        agent = agent_assessment.agent
        if agent.isotope in ("Ga-68", "F-18"):
            practical += 0.3  # Generator or cyclotron
        elif agent.isotope in ("Lu-177", "I-131"):
            practical += 0.2  # Reactor-produced, available
        elif agent.isotope in ("Zr-89", "Cu-64"):
            practical += 0.1  # Cyclotron, less available
        elif agent.isotope in ("Ac-225",):
            practical -= 0.1  # Very limited supply

        # Imaging window feasibility
        window = agent_assessment.optimal_imaging_window_hours
        if window:
            if window[0] < 4:
                practical += 0.1  # Same-day imaging
            elif window[0] < 24:
                practical += 0.05  # Next-day
            else:
                practical -= 0.05  # Multi-day protocol

        practical = max(0.0, min(1.0, practical))

        # Combined
        combined = self.w_eff * efficacy + self.w_safe * safety + self.w_prac * practical

        return StrategyScore(
            efficacy_score=round(efficacy, 3),
            safety_score=round(safety, 3),
            practical_score=round(practical, 3),
            combined_score=round(combined, 3),
        )

    def _identify_drivers(
        self,
        target: TargetAssessment,
        agent_assessment: AgentAssessment,
        simulation: SimulationResult,
    ) -> list[str]:
        """Identify key factors driving this strategy's score."""
        drivers = []

        if target.expression_score > 0.5:
            drivers.append(
                f"High {target.target_name} expression in {target.tumor_type} "
                f"(score: {target.expression_score:.2f})"
            )

        tbr = simulation.tumor_to_background_ratio.value
        if tbr > 5:
            drivers.append(f"Good tumor-to-background ratio ({tbr:.1f})")

        pen = agent_assessment.penetration
        if pen.uniformity_score > 0.5:
            drivers.append(
                f"Good tumor penetration (depth: {pen.penetration_depth_um:.0f} μm)"
            )

        opt_time = simulation.optimal_imaging_time_hours.value
        drivers.append(f"Optimal imaging at {opt_time:.1f}h post-injection")

        return drivers

    def _identify_risks(
        self,
        target: TargetAssessment,
        agent_assessment: AgentAssessment,
        simulation: SimulationResult,
    ) -> list[str]:
        """Identify risk factors for this strategy."""
        risks = []

        if agent_assessment.penetration.binding_site_barrier_risk:
            risks.append("Binding site barrier may limit tumor penetration uniformity")

        for organ, risk in agent_assessment.off_target_risk.items():
            if risk > 0.5:
                risks.append(f"Significant off-target uptake expected in {organ}")

        if simulation.dosimetry:
            for organ in ("kidneys", "bone_marrow"):
                dose = simulation.dosimetry.organ_doses_gy_per_gbq.get(organ, 0)
                tol = _SIMPLE_TOLERANCES.get(organ, 50)
                if dose > tol * 0.5:
                    risks.append(f"{organ} dose ({dose:.2f} Gy/GBq) approaching tolerance ({tol} Gy)")

        if target.evidence_level in ("C", "D"):
            risks.append(
                f"Limited clinical evidence for {target.target_name} in "
                f"{target.tumor_type} (level {target.evidence_level})"
            )

        return risks

    def _assess_confidence(
        self,
        target: TargetAssessment,
        agent_assessment: AgentAssessment,
        simulation: SimulationResult,
    ) -> str:
        """Assess overall confidence in this recommendation."""
        score = 0.5  # baseline

        if target.evidence_level == "A":
            score += 0.3
        elif target.evidence_level == "B":
            score += 0.15

        if simulation.confidence.level == "moderate":
            score += 0.1
        elif simulation.confidence.level == "high":
            score += 0.2

        if score >= 0.7:
            return "moderate"
        elif score >= 0.5:
            return "low"
        return "very_low"

    def _generate_summary(
        self,
        agent_name: str,
        scores: StrategyScore,
        drivers: list[str],
        risks: list[str],
        confidence: str,
    ) -> str:
        """Generate a natural language summary."""
        parts = [f"{agent_name}: "]

        if scores.combined_score > 0.7:
            parts.append("Strong candidate. ")
        elif scores.combined_score > 0.5:
            parts.append("Moderate candidate. ")
        else:
            parts.append("Weak candidate. ")

        if drivers:
            parts.append(drivers[0] + ". ")

        if risks:
            parts.append(f"Key risk: {risks[0]}. ")

        parts.append(f"Confidence: {confidence}.")

        return "".join(parts)


_SIMPLE_TOLERANCES: dict[str, float] = {
    "kidneys": 23.0,
    "bone_marrow": 2.0,
    "liver": 30.0,
    "lungs": 20.0,
    "spleen": 20.0,
    "heart": 25.0,
    "gut": 45.0,
}
