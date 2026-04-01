"""V1 Pipeline Orchestrator — coordinates all 7 modules.

Pipeline:
    Input Normalizer → Knowledge Layer → Parameter Builder →
    PBPK Engine → Dosimetry Engine → PD/Effect Engine → Decision Engine

Each module receives structured input, produces structured output,
and logs everything.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from theranostics.services.logging_service import (
    PipelineLogger, ModuleTimer, hash_dict, setup_logging,
)
from theranostics.services.input_normalizer import InputNormalizer, NormalizedRequest
from theranostics.services.knowledge_layer import KnowledgeLayer, TargetKnowledge
from theranostics.services.parameter_builder import ParameterBuilder, BuiltParameters
from theranostics.services.pbpk_engine_v1 import PBPKEngineV1, PBPKResult
from theranostics.services.dosimetry_engine_v1 import DosimetryEngineV1, DosimetryResultV1
from theranostics.services.pd_engine import PDEngine, PDResult
from theranostics.services.decision_engine_v1 import DecisionEngineV1, DecisionResultV1, DecisionReportV1

from theranostics.config import PROJECT_ROOT


LOGS_DIR = PROJECT_ROOT / "logs"


# ---------------------------------------------------------------------------
# V1 Pipeline result
# ---------------------------------------------------------------------------

class V1PipelineResult:
    """Complete output of the V1 pipeline."""

    def __init__(self) -> None:
        self.request_id: str = ""
        self.normalized_request: Optional[NormalizedRequest] = None
        self.knowledge: Optional[TargetKnowledge] = None
        self.parameters: Optional[BuiltParameters] = None
        self.pbpk_result: Optional[PBPKResult] = None
        self.dosimetry: Optional[DosimetryResultV1] = None
        self.pd_result: Optional[PDResult] = None
        self.decision: Optional[DecisionResultV1] = None
        self.logs: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.confidence_per_module: dict[str, float] = {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize full result for API response."""
        result = {
            "request_id": self.request_id,
            "request_summary": {
                "target": self.normalized_request.target if self.normalized_request else "",
                "agent": self.normalized_request.agent.name if self.normalized_request else "",
                "isotope": self.normalized_request.agent.isotope if self.normalized_request else None,
                "indication": self.normalized_request.indication if self.normalized_request else "",
            },
        }

        # PBPK results
        if self.pbpk_result:
            metrics = self.pbpk_result.to_metrics_dict()
            result["simulation"] = {
                "time_points": self.pbpk_result.time_points,
                "organ_timeseries": self.pbpk_result.organ_timeseries,
                "tumor_peak_concentration_nM": self.pbpk_result.tumor_peak_concentration_nM,
                "tumor_auc": self.pbpk_result.tumor_auc,
                "tbr_peak": self.pbpk_result.tbr_peak,
                "optimal_imaging_time_h": self.pbpk_result.optimal_imaging_time_h,
                "plasma_half_life_h": self.pbpk_result.plasma_half_life_h,
                "biodistribution_at_optimal": self.pbpk_result.biodistribution_at_optimal,
                "mc_ci_tumor": metrics.get("mc_ci_tumor", [0, 0]),
                "mc_ci_tbr": metrics.get("mc_ci_tbr", [0, 0]),
                "mc_success": self.pbpk_result.mc_success_count,
                "computation_time_s": round(self.pbpk_result.computation_time_s, 2),
            }

        # Dosimetry
        if self.dosimetry:
            result["dosimetry"] = self.dosimetry.to_dict()

        # PD
        if self.pd_result:
            result["pd_effect"] = self.pd_result.to_dict()

        # Decision
        if self.decision:
            result["decision"] = self.decision.to_dict()

        # Knowledge sources
        if self.knowledge:
            result["knowledge"] = {
                "target_profile": {
                    "target": self.knowledge.target,
                    "tumor_expression_score": self.knowledge.tumor_expression_score,
                    "normal_tissue_expression": self.knowledge.normal_tissue_expression,
                    "accessibility_score": self.knowledge.accessibility_score,
                    "internalization_score": self.knowledge.internalization_score,
                    "evidence_level": self.knowledge.evidence_level,
                },
                "sources_used": self.knowledge.sources_used,
                "conflicts": self.knowledge.conflicts,
            }

        # Parameters
        if self.parameters:
            result["parameters"] = self.parameters.to_dict()

        # Confidence per module
        result["confidence_per_module"] = self.confidence_per_module

        # Warnings and errors
        result["warnings"] = self.warnings
        result["errors"] = self.errors

        # Logs (audit trail)
        result["execution_trace"] = self.logs

        return result

    def to_api_response(self) -> dict[str, Any]:
        """Lighter response for API (without full time series in logs)."""
        full = self.to_dict()
        # Remove verbose logs from API response, keep count
        if "execution_trace" in full:
            full["execution_trace_count"] = len(full["execution_trace"])
            # Keep only audit-level logs in response
            full["execution_trace"] = [
                log for log in full["execution_trace"]
                if log.get("level") in ("AUDIT", "WARNING", "ERROR")
            ]
        return full


# ---------------------------------------------------------------------------
# V1 Orchestrator
# ---------------------------------------------------------------------------

class V1Orchestrator:
    """Orchestrate the complete V1 pipeline."""

    def __init__(self, use_apis: bool = True) -> None:
        self.input_normalizer = InputNormalizer()
        self.knowledge_layer = KnowledgeLayer(use_apis=use_apis)
        self.parameter_builder = ParameterBuilder()
        self.pbpk_engine = PBPKEngineV1()
        self.dosimetry_engine = DosimetryEngineV1()
        self.pd_engine = PDEngine()
        self.decision_engine = DecisionEngineV1()

    def run(self, raw_input: dict[str, Any]) -> V1PipelineResult:
        """Run the complete 7-module pipeline.

        Args:
            raw_input: User input dict (can be incomplete).

        Returns:
            V1PipelineResult with all outputs, logs, and trace.
        """
        result = V1PipelineResult()
        request_id = raw_input.get("request_id") or str(uuid.uuid4())
        result.request_id = request_id

        logger = PipelineLogger(request_id=request_id)
        logger.info("orchestrator", "pipeline_started", data={
            "input_hash": hash_dict(raw_input),
        })

        try:
            # Module 1: Input Normalizer
            normalized = self.input_normalizer.normalize(raw_input, logger)
            normalized.request_id = request_id
            result.normalized_request = normalized
            result.warnings.extend(normalized.warnings)

            # Module 2: Knowledge Layer
            knowledge = self.knowledge_layer.query(normalized, logger)
            result.knowledge = knowledge
            result.confidence_per_module["knowledge"] = knowledge.confidence

            # Module 3: Parameter Builder
            params = self.parameter_builder.build(normalized, knowledge, logger)
            result.parameters = params
            avg_confidence = (
                sum(params.confidence_per_param.values()) / max(len(params.confidence_per_param), 1)
            )
            result.confidence_per_module["parameters"] = round(avg_confidence, 2)

            # Module 4: PBPK Engine
            pbpk = self.pbpk_engine.simulate(normalized, params, logger)
            result.pbpk_result = pbpk
            mc_stability = min(1.0, pbpk.mc_success_count / max(normalized.n_monte_carlo, 1))
            result.confidence_per_module["pbpk"] = round(mc_stability * 0.8, 2)

            # Module 5: Dosimetry Engine
            dosimetry = self.dosimetry_engine.compute(normalized, pbpk, logger)
            result.dosimetry = dosimetry
            if dosimetry:
                result.confidence_per_module["dosimetry"] = 0.65
                result.warnings.extend(dosimetry.warnings)

            # Module 6: PD/Effect Engine
            sim_metrics = pbpk.to_metrics_dict()
            dosimetry_dict = dosimetry.to_dict() if dosimetry else None
            if dosimetry_dict:
                dosimetry_dict["injected_gbq"] = normalized.dose.activity_GBq or 7.4

            pd = self.pd_engine.evaluate(
                normalized, params, sim_metrics, dosimetry_dict, logger,
            )
            result.pd_result = pd
            result.confidence_per_module["pd"] = round(pd.confidence_score, 2)

            # Module 7: Decision Engine
            decision = self.decision_engine.score_strategy(
                agent_name=normalized.agent.name,
                isotope=normalized.agent.isotope,
                simulation_metrics=sim_metrics,
                dosimetry=dosimetry_dict,
                pd_result=pd.to_dict(),
                params=params.to_dict(),
                knowledge=knowledge.to_dict(),
                logger=logger,
            )
            result.decision = decision
            result.confidence_per_module["decision"] = round(decision.score.confidence, 2)

        except Exception as e:
            logger.error("orchestrator", "pipeline_failed", errors=[str(e)])
            result.errors.append(str(e))

        # Collect logs
        result.logs = logger.get_logs()
        result.warnings.extend(logger.get_warnings())

        # Persist logs
        try:
            logger.flush_to_file(LOGS_DIR)
        except Exception:
            pass

        logger.info("orchestrator", "pipeline_completed", data={
            "request_id": request_id,
            "has_errors": len(result.errors) > 0,
            "confidence_per_module": result.confidence_per_module,
        })

        return result

    def run_comparison(
        self, raw_inputs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Run multiple simulations and compare strategies."""
        results = []
        decisions = []

        logger = PipelineLogger(request_id=f"comparison_{uuid.uuid4().hex[:8]}")

        for raw in raw_inputs:
            pipeline_result = self.run(raw)
            results.append(pipeline_result)
            if pipeline_result.decision:
                decisions.append(pipeline_result.decision)

        report = self.decision_engine.rank_strategies(decisions, logger)

        return {
            "comparison": report.to_dict(),
            "individual_results": [r.to_api_response() for r in results],
        }
