"""Simulation API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from theranostics.models.simulation import SimulationRequest, SimulationResult
from theranostics.orchestrator import SimulationOrchestrator

router = APIRouter(prefix="/simulate", tags=["simulation"])

orchestrator = SimulationOrchestrator()


@router.post("/", response_model=SimulationResult)
async def run_simulation(request: SimulationRequest) -> SimulationResult:
    """Run a single theranostic simulation."""
    try:
        result = orchestrator.run_simulation(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/compare")
async def compare_strategies(requests: list[SimulationRequest]) -> dict:
    """Compare multiple theranostic strategies."""
    if len(requests) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 strategies to compare")
    if len(requests) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 strategies per comparison")

    try:
        report = orchestrator.run_comparison(requests)
        return {
            "target": {
                "name": report.target_assessment.target_name,
                "tumor_type": report.target_assessment.tumor_type,
                "expression_score": report.target_assessment.expression_score,
                "evidence_level": report.target_assessment.evidence_level,
            },
            "ranked_strategies": [
                {
                    "rank": s.rank,
                    "agent": s.agent_name,
                    "isotope": s.isotope,
                    "scores": {
                        "efficacy": s.scores.efficacy_score,
                        "safety": s.scores.safety_score,
                        "practical": s.scores.practical_score,
                        "combined": s.scores.combined_score,
                    },
                    "key_drivers": s.key_drivers,
                    "risks": s.risks,
                    "confidence": s.confidence,
                    "summary": s.summary,
                }
                for s in report.ranked_strategies
            ],
            "overall_recommendation": report.overall_recommendation,
            "scientific_caveats": report.scientific_caveats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/quick")
async def quick_simulation(
    agent_key: str = "trastuzumab-89Zr",
    dose_mbq: float = 37.0,
    tumor_type: str = "breast",
    patient_weight_kg: float = 73.0,
) -> SimulationResult:
    """Quick simulation with minimal parameters."""
    request = SimulationRequest(
        agent_key=agent_key,
        dose_mbq=dose_mbq,
        tumor_type=tumor_type,
        patient_weight_kg=patient_weight_kg,
        n_monte_carlo=50,  # Fewer MC samples for speed
        time_step_hours=0.5,  # Coarser time step
    )
    return orchestrator.run_simulation(request)
