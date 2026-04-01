"""Tests for the Agent Engine."""

from theranostics.engines.agent import AgentEngine
from theranostics.models.agent_properties import AGENT_LIBRARY, AgentType


def test_list_agents():
    engine = AgentEngine()
    agents = engine.list_agents()
    assert "trastuzumab" in agents
    assert "PSMA-617" in agents


def test_assess_trastuzumab():
    engine = AgentEngine()
    agent = AGENT_LIBRARY["trastuzumab"]
    result = engine.assess(agent)

    assert result.agent.name == "Trastuzumab"
    assert result.penetration.penetration_depth_um > 0
    assert result.clearance.predicted_half_life_hours > 100  # IgG: long half-life
    assert "liver" in result.off_target_risk


def test_assess_nanobody():
    engine = AgentEngine()
    agent = AGENT_LIBRARY["her2-nanobody"]
    result = engine.assess(agent)

    assert result.agent.agent_type == AgentType.NANOBODY
    assert result.clearance.predicted_half_life_hours < 10  # Short half-life
    assert result.clearance.renal_fraction > 0  # Renally cleared


def test_nanobody_better_penetration_than_igg():
    engine = AgentEngine()
    igg = engine.assess(AGENT_LIBRARY["trastuzumab"])
    nano = engine.assess(AGENT_LIBRARY["her2-nanobody"])

    # Nanobody should penetrate better (higher uniformity score)
    assert nano.penetration.uniformity_score > igg.penetration.uniformity_score


def test_small_molecule_properties():
    engine = AgentEngine()
    agent = AGENT_LIBRARY["PSMA-617"]
    result = engine.assess(agent)

    assert result.clearance.renal_fraction > 0
    assert result.agent.molecular_weight_kda < 5


def test_imaging_window():
    engine = AgentEngine()

    # IgG: late imaging window
    igg = engine.assess(AGENT_LIBRARY["trastuzumab-89Zr"])
    assert igg.optimal_imaging_window_hours is not None
    assert igg.optimal_imaging_window_hours[0] >= 48  # Days for IgG

    # Small molecule: early window
    sm = engine.assess(AGENT_LIBRARY["PSMA-617-68Ga"])
    assert sm.optimal_imaging_window_hours is not None
    assert sm.optimal_imaging_window_hours[0] < 10


def test_off_target_psma():
    engine = AgentEngine()
    agent = AGENT_LIBRARY["PSMA-617"]
    result = engine.assess(agent)

    # PSMA agents should flag salivary glands
    assert "salivary_glands" in result.off_target_risk
    assert result.off_target_risk["salivary_glands"] > 0.5
