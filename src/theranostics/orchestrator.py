"""Simulation Orchestrator — coordinates all engines into a single pipeline."""

from __future__ import annotations

from typing import Optional

from theranostics.engines.agent import AgentAssessment, AgentEngine
from theranostics.engines.body import BodySimulationEngine
from theranostics.engines.decision import DecisionEngine, DecisionReport, StrategyRecommendation
from theranostics.engines.pkpd import PKPDEngine
from theranostics.engines.target import TargetAssessment, TargetEngine
from theranostics.models.agent_properties import AGENT_LIBRARY, AgentProperties
from theranostics.models.patient import (
    Demographics,
    OrganFunction,
    PatientProfile,
    Sex,
    TumorProfile,
    TumorType,
)
from theranostics.models.simulation import SimulationRequest, SimulationResult


class SimulationOrchestrator:
    """Coordinate all engines to run a complete simulation pipeline."""

    def __init__(self) -> None:
        self.target_engine = TargetEngine()
        self.agent_engine = AgentEngine()
        self.body_engine = BodySimulationEngine()
        self.pkpd_engine = PKPDEngine()
        self.decision_engine = DecisionEngine()

    def run_simulation(self, request: SimulationRequest) -> SimulationResult:
        """Run a complete simulation from a user request."""

        # 1. Resolve agent
        agent = AGENT_LIBRARY.get(request.agent_key)
        if agent is None:
            raise ValueError(f"Unknown agent: {request.agent_key}")

        # Override isotope if specified
        if request.isotope_key:
            agent = agent.model_copy(update={"isotope": request.isotope_key})

        # 2. Build patient profile
        patient = self._build_patient(request)

        # 3. Run body simulation
        result = self.body_engine.simulate(
            agent=agent,
            patient=patient,
            dose_mbq=request.dose_mbq,
            dose_mg=request.dose_mg,
            duration_hours=request.duration_hours,
            time_step_hours=request.time_step_hours,
            n_monte_carlo=request.n_monte_carlo,
        )

        # 4. Compute dosimetry if therapeutic isotope
        dosimetry = self.pkpd_engine.compute_dosimetry(
            organ_results=result.organ_results,
            agent=agent,
            dose_gbq=request.dose_mbq / 1000.0,
        )
        result.dosimetry = dosimetry

        return result

    def run_comparison(
        self, requests: list[SimulationRequest]
    ) -> DecisionReport:
        """Run multiple simulations and generate a comparative report."""

        # Assess target (same for all strategies)
        first = requests[0]
        agent = AGENT_LIBRARY.get(first.agent_key)
        target_assessment = self.target_engine.assess(
            target_name=agent.target_name if agent else first.target_name,
            tumor_type=first.tumor_type,
        )

        strategies: list[StrategyRecommendation] = []

        for req in requests:
            # Run simulation
            sim_result = self.run_simulation(req)

            # Get agent assessment
            agent = AGENT_LIBRARY.get(req.agent_key)
            if agent is None:
                continue
            agent_assessment = self.agent_engine.assess(
                agent=agent,
                tumor_antigen_density_nm=req.tumor_target_density,
            )

            # Evaluate strategy
            recommendation = self.decision_engine.evaluate_strategy(
                target=target_assessment,
                agent_assessment=agent_assessment,
                simulation=sim_result,
            )
            strategies.append(recommendation)

        # Rank
        ranked = self.decision_engine.rank_strategies(strategies)

        # Generate report
        return self.decision_engine.generate_report(target_assessment, ranked)

    def get_available_agents(self) -> list[dict]:
        """List all available agents with their properties."""
        agents = []
        for key, agent in AGENT_LIBRARY.items():
            agents.append({
                "key": key,
                "name": agent.name,
                "type": agent.agent_type.value,
                "target": agent.target_name,
                "mw_kda": agent.molecular_weight_kda,
                "half_life_hours": agent.plasma_half_life_hours,
                "isotope": agent.isotope,
            })
        return agents

    def get_available_targets(self) -> list[dict]:
        """List all available targets."""
        targets = []
        for target_name in self.target_engine.list_targets():
            info = self.target_engine.get_target_info(target_name)
            if info:
                targets.append({
                    "name": target_name,
                    "full_name": info.get("full_name", ""),
                    "tumor_types": list(info.get("expression_by_tumor", {}).keys()),
                    "known_agents": info.get("known_agents", []),
                })
        return targets

    def _build_patient(self, request: SimulationRequest) -> PatientProfile:
        """Build a PatientProfile from a SimulationRequest."""
        sex = Sex.MALE if request.patient_sex.lower() == "male" else Sex.FEMALE

        try:
            tumor_type = TumorType(request.tumor_type)
        except ValueError:
            tumor_type = TumorType.OTHER

        expression = request.tumor_target_density
        # Normalize: if > 1, it's in nM; convert to [0,1] for the model
        if expression > 1.0:
            expression_normalized = min(1.0, expression / 200.0)
        else:
            expression_normalized = expression

        return PatientProfile(
            demographics=Demographics(
                age=request.patient_age,
                sex=sex,
                weight_kg=request.patient_weight_kg,
                height_cm=request.patient_height_cm,
            ),
            tumor=TumorProfile(
                tumor_type=tumor_type,
                tumor_volume_ml=request.tumor_volume_ml,
                n_metastases=request.n_metastases,
                target_expression_level=expression_normalized,
            ),
            organ_function=OrganFunction(
                egfr_ml_per_min=request.patient_egfr,
                liver_function_score=request.patient_liver_function,
            ),
        )
