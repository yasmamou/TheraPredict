"""Tests for the Body Simulation Engine."""

import numpy as np

from theranostics.engines.body import BodySimulationEngine
from theranostics.models.agent_properties import AGENT_LIBRARY
from theranostics.models.patient import (
    Demographics,
    OrganFunction,
    PatientProfile,
    Sex,
    TumorProfile,
    TumorType,
)


def _default_patient() -> PatientProfile:
    return PatientProfile(
        demographics=Demographics(age=60, sex=Sex.FEMALE, weight_kg=70.0, height_cm=165.0),
        tumor=TumorProfile(
            tumor_type=TumorType.BREAST,
            tumor_volume_ml=50.0,
            target_expression_level=0.7,
        ),
        organ_function=OrganFunction(egfr_ml_per_min=90.0),
    )


def test_simulation_runs():
    """Basic smoke test: simulation completes without error."""
    engine = BodySimulationEngine()
    agent = AGENT_LIBRARY["trastuzumab-89Zr"]
    patient = _default_patient()

    result = engine.simulate(
        agent=agent,
        patient=patient,
        dose_mbq=37.0,
        duration_hours=72,
        time_step_hours=0.5,
        n_monte_carlo=10,
    )

    assert result is not None
    assert len(result.time_points_hours) > 0
    assert len(result.organ_results) > 0


def test_tumor_uptake_positive():
    """Tumor should accumulate agent over time."""
    engine = BodySimulationEngine()
    agent = AGENT_LIBRARY["trastuzumab-89Zr"]
    patient = _default_patient()

    result = engine.simulate(
        agent=agent,
        patient=patient,
        dose_mbq=37.0,
        duration_hours=120,
        time_step_hours=0.5,
        n_monte_carlo=5,
    )

    # Tumor uptake should be positive
    assert result.tumor_uptake_percent_id_per_g.value > 0


def test_tbr_positive():
    """Tumor-to-background ratio should be > 1 for a targeted agent."""
    engine = BodySimulationEngine()
    agent = AGENT_LIBRARY["trastuzumab-89Zr"]
    patient = _default_patient()

    result = engine.simulate(
        agent=agent,
        patient=patient,
        dose_mbq=37.0,
        duration_hours=120,
        time_step_hours=0.5,
        n_monte_carlo=5,
    )

    assert result.tumor_to_background_ratio.value > 0


def test_plasma_decreases_over_time():
    """Plasma concentration should decrease over time (clearance)."""
    engine = BodySimulationEngine()
    agent = AGENT_LIBRARY["trastuzumab-89Zr"]
    patient = _default_patient()

    result = engine.simulate(
        agent=agent,
        patient=patient,
        dose_mbq=37.0,
        duration_hours=72,
        time_step_hours=0.5,
        n_monte_carlo=1,
    )

    plasma_ts = next(
        (ts for ts in result.organ_results if ts.organ_name == "plasma"), None
    )
    assert plasma_ts is not None

    # Plasma should decrease
    early = np.mean(plasma_ts.concentrations_total[:10])
    late = np.mean(plasma_ts.concentrations_total[-10:])
    assert late < early


def test_small_molecule_faster_clearance():
    """Small molecules should clear faster than IgG."""
    engine = BodySimulationEngine()
    patient = _default_patient()
    patient.tumor.tumor_type = TumorType.PROSTATE

    igg_result = engine.simulate(
        agent=AGENT_LIBRARY["trastuzumab-89Zr"],
        patient=patient,
        dose_mbq=37.0,
        duration_hours=48,
        time_step_hours=0.5,
        n_monte_carlo=1,
    )

    sm_result = engine.simulate(
        agent=AGENT_LIBRARY["PSMA-617-68Ga"],
        patient=patient,
        dose_mbq=150.0,
        duration_hours=48,
        time_step_hours=0.5,
        n_monte_carlo=1,
    )

    # IgG should retain more in plasma at 48h
    igg_plasma = next(
        ts for ts in igg_result.organ_results if ts.organ_name == "plasma"
    )
    sm_plasma = next(
        ts for ts in sm_result.organ_results if ts.organ_name == "plasma"
    )

    # Compare late plasma levels (relative to initial)
    igg_retention = igg_plasma.concentrations_total[-1] / max(igg_plasma.concentrations_total[0], 1e-12)
    sm_retention = sm_plasma.concentrations_total[-1] / max(sm_plasma.concentrations_total[0], 1e-12)

    assert igg_retention > sm_retention


def test_monte_carlo_provides_ci():
    """Monte Carlo should provide confidence intervals."""
    engine = BodySimulationEngine()
    agent = AGENT_LIBRARY["trastuzumab-89Zr"]
    patient = _default_patient()

    result = engine.simulate(
        agent=agent,
        patient=patient,
        dose_mbq=37.0,
        duration_hours=48,
        time_step_hours=1.0,
        n_monte_carlo=20,
    )

    # CI should bracket the median
    uptake = result.tumor_uptake_percent_id_per_g
    assert uptake.ci_low <= uptake.value
    assert uptake.ci_high >= uptake.value


def test_biodistribution_all_organs():
    """All compartments should have biodistribution data."""
    engine = BodySimulationEngine()
    agent = AGENT_LIBRARY["trastuzumab-89Zr"]
    patient = _default_patient()

    result = engine.simulate(
        agent=agent,
        patient=patient,
        dose_mbq=37.0,
        duration_hours=48,
        time_step_hours=1.0,
        n_monte_carlo=1,
    )

    assert len(result.biodistribution_at_optimal) > 5
    assert "tumor" in result.biodistribution_at_optimal
    assert "liver" in result.biodistribution_at_optimal
