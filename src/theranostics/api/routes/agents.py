"""Agent and target API routes."""

from __future__ import annotations

from fastapi import APIRouter

from theranostics.models.agent_properties import AGENT_LIBRARY, ISOTOPE_LIBRARY
from theranostics.orchestrator import SimulationOrchestrator

router = APIRouter(tags=["catalog"])

orchestrator = SimulationOrchestrator()


@router.get("/agents")
async def list_agents() -> list[dict]:
    """List all available theranostic agents."""
    return orchestrator.get_available_agents()


@router.get("/agents/{agent_key}")
async def get_agent(agent_key: str) -> dict:
    """Get detailed properties of a specific agent."""
    agent = AGENT_LIBRARY.get(agent_key)
    if agent is None:
        return {"error": f"Agent '{agent_key}' not found"}
    return agent.model_dump()


@router.get("/targets")
async def list_targets() -> list[dict]:
    """List all available theranostic targets."""
    return orchestrator.get_available_targets()


@router.get("/targets/{target_name}")
async def get_target(target_name: str, tumor_type: str = "breast") -> dict:
    """Assess a target for a specific tumor type."""
    assessment = orchestrator.target_engine.assess(target_name, tumor_type)
    return {
        "target_name": assessment.target_name,
        "tumor_type": assessment.tumor_type,
        "expression_score": assessment.expression_score,
        "expression_ci": [assessment.expression_ci_low, assessment.expression_ci_high],
        "accessibility_score": assessment.accessibility_score,
        "theranostic_relevance": assessment.theranostic_relevance,
        "diagnostic_score": assessment.diagnostic_score,
        "therapeutic_score": assessment.therapeutic_score,
        "evidence_level": assessment.evidence_level,
        "known_agents": assessment.known_agents,
        "notes": assessment.notes,
    }


@router.get("/isotopes")
async def list_isotopes() -> list[dict]:
    """List all available isotopes."""
    return [
        {
            "key": key,
            "name": iso.name,
            "symbol": iso.symbol,
            "half_life_hours": iso.half_life_hours,
            "type": iso.isotope_type.value,
            "emission": iso.emission_type,
        }
        for key, iso in ISOTOPE_LIBRARY.items()
    ]
