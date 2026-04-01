"""V1 Simulation API routes.

All endpoints use the V1 pipeline orchestrator with full logging
and structured output.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from theranostics.orchestrator_v1 import V1Orchestrator

router = APIRouter(prefix="/v1", tags=["v1-simulation"])

# Single orchestrator instance
_orchestrator = V1Orchestrator(use_apis=True)
_orchestrator_no_api = V1Orchestrator(use_apis=False)


@router.post("/simulate")
async def run_v1_simulation(request: dict[str, Any]) -> dict[str, Any]:
    """Run a V1 theranostic simulation.

    Accepts a flexible JSON input. Minimal required fields:
    - target: str (e.g., "PSMA", "HER2")

    Optional fields:
    - agent: {name, class, size_kDa, kd_nM, isotope, ...}
    - dose: {activity_GBq, activity_MBq, mass_mg}
    - tumor: {type, volume_ml, target_expression_override}
    - patient: {weight_kg, sex, age, renal_function, hepatic_function}
    - duration_hours, n_monte_carlo, time_step_hours
    """
    try:
        result = _orchestrator.run(request)
        if result.errors:
            return {
                "status": "partial_error",
                "errors": result.errors,
                **result.to_api_response(),
            }
        return {
            "status": "success",
            **result.to_api_response(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"V1 simulation failed: {str(e)}")


@router.post("/simulate/offline")
async def run_v1_simulation_offline(request: dict[str, Any]) -> dict[str, Any]:
    """Run V1 simulation without external API calls (curated data only)."""
    try:
        result = _orchestrator_no_api.run(request)
        return {
            "status": "success",
            "mode": "offline",
            **result.to_api_response(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"V1 offline simulation failed: {str(e)}")


@router.post("/compare")
async def compare_v1_strategies(requests: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare multiple theranostic strategies.

    Send an array of simulation inputs (2-10).
    """
    if len(requests) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 strategies")
    if len(requests) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 strategies")

    try:
        result = _orchestrator.run_comparison(requests)
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"V1 comparison failed: {str(e)}")


@router.get("/targets")
async def list_v1_targets() -> dict[str, Any]:
    """List all V1 supported targets with metadata."""
    from theranostics.services.knowledge_layer import _CURATED_TARGET_PROFILES
    targets = []
    for name, profile in _CURATED_TARGET_PROFILES.items():
        targets.append({
            "name": name,
            "full_name": profile["full_name"],
            "gene": profile["gene"],
            "evidence_levels": profile["evidence_levels"],
            "known_agents": profile["known_agents"],
        })
    return {"targets": targets}


@router.get("/isotopes")
async def list_v1_isotopes() -> dict[str, Any]:
    """List all V1 supported isotopes."""
    from theranostics.models.agent_properties import ISOTOPE_LIBRARY
    isotopes = []
    for key, iso in ISOTOPE_LIBRARY.items():
        isotopes.append({
            "key": key,
            "name": iso.name,
            "symbol": iso.symbol,
            "half_life_hours": iso.half_life_hours,
            "type": iso.isotope_type.value,
            "emission": iso.emission_type,
        })
    return {"isotopes": isotopes}


@router.get("/agent-classes")
async def list_v1_agent_classes() -> dict[str, Any]:
    """List supported agent classes with default parameters."""
    from theranostics.services.input_normalizer import _CLASS_DEFAULTS
    return {"agent_classes": {k: v for k, v in _CLASS_DEFAULTS.items()}}
