"""Integration tests — full pipeline from request to result."""

from theranostics.models.simulation import SimulationRequest
from theranostics.orchestrator import SimulationOrchestrator


def test_full_simulation_her2():
    """End-to-end: HER2 antibody simulation."""
    orchestrator = SimulationOrchestrator()
    request = SimulationRequest(
        target_name="HER2",
        tumor_type="breast",
        agent_key="trastuzumab-89Zr",
        dose_mbq=37.0,
        patient_weight_kg=70.0,
        tumor_volume_ml=50.0,
        duration_hours=72,
        time_step_hours=0.5,
        n_monte_carlo=10,
    )

    result = orchestrator.run_simulation(request)

    assert result is not None
    assert result.tumor_uptake_percent_id_per_g.value > 0
    assert result.tumor_to_background_ratio.value > 0
    assert result.optimal_imaging_time_hours.value > 0
    assert len(result.organ_results) > 0
    assert result.confidence.level in ("high", "moderate", "low", "very_low")


def test_full_simulation_psma():
    """End-to-end: PSMA small molecule simulation."""
    orchestrator = SimulationOrchestrator()
    request = SimulationRequest(
        target_name="PSMA",
        tumor_type="prostate",
        agent_key="PSMA-617",
        dose_mbq=7400.0,
        patient_weight_kg=80.0,
        tumor_volume_ml=30.0,
        tumor_target_density=150.0,
        duration_hours=168,
        time_step_hours=0.5,
        n_monte_carlo=10,
    )

    result = orchestrator.run_simulation(request)

    assert result is not None
    # PSMA-617 with Lu-177 should produce dosimetry
    assert result.dosimetry is not None
    assert result.dosimetry.tumor_dose_gy_per_gbq > 0
    assert result.dosimetry.dose_limiting_organ in (
        "kidneys", "bone_marrow", "liver", "spleen"
    )


def test_full_simulation_dotatate():
    """End-to-end: DOTATATE simulation for neuroendocrine tumors."""
    orchestrator = SimulationOrchestrator()
    request = SimulationRequest(
        target_name="SSTR2",
        tumor_type="neuroendocrine",
        agent_key="DOTATATE",
        dose_mbq=7400.0,
        patient_weight_kg=75.0,
        tumor_volume_ml=20.0,
        duration_hours=168,
        time_step_hours=0.5,
        n_monte_carlo=10,
    )

    result = orchestrator.run_simulation(request)
    assert result is not None
    assert result.dosimetry is not None


def test_comparison():
    """Compare multiple strategies."""
    orchestrator = SimulationOrchestrator()

    requests = [
        SimulationRequest(
            target_name="HER2",
            tumor_type="breast",
            agent_key="trastuzumab-89Zr",
            dose_mbq=37.0,
            duration_hours=48,
            time_step_hours=1.0,
            n_monte_carlo=5,
        ),
        SimulationRequest(
            target_name="HER2",
            tumor_type="breast",
            agent_key="her2-nanobody-68Ga",
            dose_mbq=150.0,
            duration_hours=48,
            time_step_hours=1.0,
            n_monte_carlo=5,
        ),
    ]

    report = orchestrator.run_comparison(requests)

    assert len(report.ranked_strategies) == 2
    assert report.ranked_strategies[0].rank == 1
    assert report.ranked_strategies[1].rank == 2
    assert report.overall_recommendation != ""


def test_available_agents():
    orchestrator = SimulationOrchestrator()
    agents = orchestrator.get_available_agents()
    assert len(agents) > 5
    assert any(a["name"] == "Trastuzumab" for a in agents)


def test_available_targets():
    orchestrator = SimulationOrchestrator()
    targets = orchestrator.get_available_targets()
    assert len(targets) > 3
    assert any(t["name"] == "HER2" for t in targets)
