"""Comprehensive unit tests for TheraPredict V1 pipeline.

Tests all 7 modules:
    1. Input Normalizer
    2. Knowledge Layer
    3. Parameter Builder
    4. PBPK Engine V1
    5. Dosimetry Engine V1
    6. PD Engine
    7. V1 Orchestrator

Run with:
    PYTHONPATH=src pytest tests/test_v1_pipeline.py -v
"""

from __future__ import annotations

import pytest
import numpy as np

from theranostics.services.logging_service import PipelineLogger
from theranostics.services.input_normalizer import (
    InputNormalizer,
    NormalizedRequest,
    VALID_TARGETS,
    VALID_ISOTOPES,
)
from theranostics.services.knowledge_layer import KnowledgeLayer, TargetKnowledge
from theranostics.services.parameter_builder import ParameterBuilder, BuiltParameters
from theranostics.services.pbpk_engine_v1 import PBPKEngineV1, PBPKResult
from theranostics.services.dosimetry_engine_v1 import (
    DosimetryEngineV1,
    DosimetryResultV1,
    THERAPEUTIC_ISOTOPES,
)
from theranostics.services.pd_engine import PDEngine, PDResult
from theranostics.orchestrator_v1 import V1Orchestrator, V1PipelineResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def logger():
    return PipelineLogger(request_id="test-run")


@pytest.fixture
def normalizer():
    return InputNormalizer()


@pytest.fixture
def knowledge_layer():
    return KnowledgeLayer(use_apis=False)


@pytest.fixture
def parameter_builder():
    return ParameterBuilder()


@pytest.fixture
def pbpk_engine():
    return PBPKEngineV1()


@pytest.fixture
def dosimetry_engine():
    return DosimetryEngineV1()


@pytest.fixture
def pd_engine():
    return PDEngine()


def _make_psma617_input():
    """Complete PSMA-617 + Lu-177 input."""
    return {
        "target": "PSMA",
        "agent": {
            "name": "PSMA-617",
            "class": "peptide",
            "size_kDa": 1.4,
            "kd_nM": 1.2,
            "kon_per_M_per_s": 8e5,
            "isotope": "Lu-177",
            "internalization": True,
        },
        "dose": {"activity_GBq": 7.4},
        "tumor": {"type": "prostate", "volume_ml": 30.0, "stage": "IV"},
        "patient": {"weight_kg": 75.0, "sex": "male", "age": 68},
        "n_monte_carlo": 5,
        "duration_hours": 48,
        "time_step_hours": 0.5,
    }


def _make_dotatate_ga68_input():
    """DOTATATE + Ga-68 (diagnostic)."""
    return {
        "target": "SSTR2",
        "agent": {
            "name": "DOTATATE",
            "class": "peptide",
            "size_kDa": 1.4,
            "kd_nM": 1.5,
            "kon_per_M_per_s": 7e5,
            "isotope": "Ga-68",
            "internalization": True,
        },
        "dose": {"activity_MBq": 185.0},
        "n_monte_carlo": 5,
        "duration_hours": 24,
        "time_step_hours": 0.5,
    }


def _make_trastuzumab_input():
    """Trastuzumab (IgG, no isotope)."""
    return {
        "target": "HER2",
        "agent": {
            "name": "Trastuzumab",
            "class": "IgG",
            "size_kDa": 148.0,
            "kd_nM": 0.1,
            "kon_per_M_per_s": 1.5e5,
            "has_fc_region": True,
            "internalization": True,
        },
        "dose": {"mass_mg": 440.0},
        "n_monte_carlo": 5,
        "duration_hours": 48,
        "time_step_hours": 0.5,
    }


def _normalize(normalizer, raw, logger):
    return normalizer.normalize(raw, logger)


def _build_pipeline_up_to_params(normalizer, knowledge_layer, parameter_builder, raw, logger):
    """Run modules 1-3 and return (request, knowledge, params)."""
    req = normalizer.normalize(raw, logger)
    knowledge = knowledge_layer.query(req, logger)
    params = parameter_builder.build(req, knowledge, logger)
    return req, knowledge, params


def _build_pipeline_up_to_pbpk(normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger):
    """Run modules 1-4 and return (request, knowledge, params, pbpk)."""
    req, knowledge, params = _build_pipeline_up_to_params(
        normalizer, knowledge_layer, parameter_builder, raw, logger
    )
    pbpk = pbpk_engine.simulate(req, params, logger)
    return req, knowledge, params, pbpk


# ===========================================================================
# 1. Input Normalizer
# ===========================================================================

class TestInputNormalizer:

    def test_complete_input_normalization(self, normalizer, logger):
        """Complete input should produce a valid NormalizedRequest with minimal defaults."""
        raw = _make_psma617_input()
        result = normalizer.normalize(raw, logger)

        assert isinstance(result, NormalizedRequest)
        assert result.target == "PSMA"
        assert result.agent.name == "PSMA-617"
        assert result.agent.agent_class == "peptide"
        assert result.agent.isotope == "Lu-177"
        assert result.agent.kd_nM == 1.2
        assert result.agent.kon_per_M_per_s == 8e5
        assert result.patient.weight_kg == 75.0
        assert result.dose.activity_GBq == 7.4

    def test_minimal_input_applies_defaults(self, normalizer, logger):
        """Empty input should still produce a valid request with all defaults."""
        result = normalizer.normalize({}, logger)

        assert isinstance(result, NormalizedRequest)
        assert result.target == "PSMA"  # default
        assert result.agent.agent_class == "small_molecule"  # default
        assert result.patient.weight_kg == 70.0
        assert result.patient.age == 65
        assert len(result.defaults_applied) > 0
        assert any("target=PSMA" in d for d in result.defaults_applied)

    def test_isotope_alias_68ga(self, normalizer, logger):
        """68Ga should be normalized to Ga-68."""
        raw = {"agent": {"isotope": "68Ga"}}
        result = normalizer.normalize(raw, logger)
        assert result.agent.isotope == "Ga-68"

    def test_isotope_alias_177lu(self, normalizer, logger):
        """177Lu should be normalized to Lu-177."""
        raw = {"agent": {"isotope": "177Lu"}}
        result = normalizer.normalize(raw, logger)
        assert result.agent.isotope == "Lu-177"

    def test_isotope_alias_variants(self, normalizer, logger):
        """All alias forms should normalize correctly."""
        aliases = {
            "Ga68": "Ga-68",
            "F18": "F-18",
            "18F": "F-18",
            "Lu177": "Lu-177",
            "90Y": "Y-90",
            "225Ac": "Ac-225",
            "Zr89": "Zr-89",
            "131I": "I-131",
        }
        for alias, expected in aliases.items():
            result = normalizer.normalize({"agent": {"isotope": alias}}, logger)
            assert result.agent.isotope == expected, f"Failed for alias {alias}"

    def test_unknown_target_falls_back_to_psma(self, normalizer, logger):
        """An unrecognized target should default to PSMA with a warning."""
        result = normalizer.normalize({"target": "UNKNOWN_TARGET_XYZ"}, logger)
        assert result.target == "PSMA"
        assert any("Unknown target" in w for w in result.warnings)
        assert "target=PSMA" in result.defaults_applied

    def test_koff_derived_from_kd_and_kon(self, normalizer, logger):
        """When koff is missing but kd and kon are provided, koff should be derived."""
        raw = {
            "agent": {
                "kd_nM": 5.0,
                "kon_per_M_per_s": 1e6,
                # koff intentionally omitted
            }
        }
        result = normalizer.normalize(raw, logger)
        expected_koff = 5.0 * 1e-9 * 1e6  # 5e-3
        assert result.agent.koff_per_s is not None
        assert abs(result.agent.koff_per_s - expected_koff) < 1e-6
        assert any("koff_per_s" in d and "derived" in d for d in result.defaults_applied)

    def test_defaults_are_logged(self, normalizer, logger):
        """All defaults applied should be tracked in defaults_applied list."""
        result = normalizer.normalize({}, logger)
        # With empty input, many defaults should be logged
        assert len(result.defaults_applied) >= 5
        # Check some expected defaults
        default_strs = " ".join(result.defaults_applied)
        assert "target=PSMA" in default_strs
        assert "patient.weight_kg" in default_strs

    def test_unknown_isotope_returns_none_with_warning(self, normalizer, logger):
        """An unrecognized isotope should be set to None with a warning."""
        raw = {"agent": {"isotope": "Unobtainium-999"}}
        result = normalizer.normalize(raw, logger)
        assert result.agent.isotope is None
        assert any("Unknown isotope" in w for w in result.warnings)

    def test_gbq_to_mbq_conversion(self, normalizer, logger):
        """activity_GBq should be converted to activity_MBq internally."""
        raw = {"dose": {"activity_GBq": 7.4}, "agent": {"isotope": "Lu-177"}}
        result = normalizer.normalize(raw, logger)
        assert result.dose.activity_MBq == pytest.approx(7400.0)

    def test_input_hash_populated(self, normalizer, logger):
        """The input_hash field should be populated."""
        result = normalizer.normalize({"target": "PSMA"}, logger)
        assert result.input_hash != ""
        assert len(result.input_hash) == 16


# ===========================================================================
# 2. Knowledge Layer
# ===========================================================================

class TestKnowledgeLayer:

    def test_apis_disabled_uses_curated_only(self, knowledge_layer, normalizer, logger):
        """With use_apis=False, only curated_internal should be in sources."""
        req = normalizer.normalize({"target": "PSMA"}, logger)
        knowledge = knowledge_layer.query(req, logger)

        assert isinstance(knowledge, TargetKnowledge)
        assert "curated_internal" in knowledge.sources_used
        assert len(knowledge.sources_used) == 1  # Only curated
        assert knowledge.confidence == 0.5

    def test_psma_has_kidney_and_salivary_expression(self, knowledge_layer, normalizer, logger):
        """PSMA knowledge should include kidney and salivary_glands expression."""
        req = normalizer.normalize({"target": "PSMA"}, logger)
        knowledge = knowledge_layer.query(req, logger)

        assert "kidney" in knowledge.normal_tissue_expression
        assert "salivary_glands" in knowledge.normal_tissue_expression
        assert knowledge.normal_tissue_expression["kidney"] > 0.5
        assert knowledge.normal_tissue_expression["salivary_glands"] > 0.5

    def test_her2_has_heart_expression(self, knowledge_layer, normalizer, logger):
        """HER2 knowledge should include heart expression (cardiotoxicity risk)."""
        req = normalizer.normalize({"target": "HER2"}, logger)
        knowledge = knowledge_layer.query(req, logger)

        assert "heart" in knowledge.normal_tissue_expression
        assert knowledge.normal_tissue_expression["heart"] > 0.3

    def test_cd20_has_spleen_and_bone_marrow(self, knowledge_layer, normalizer, logger):
        """CD20 knowledge should include spleen and bone_marrow expression."""
        req = normalizer.normalize({"target": "CD20"}, logger)
        knowledge = knowledge_layer.query(req, logger)

        assert "spleen" in knowledge.normal_tissue_expression
        assert "bone_marrow" in knowledge.normal_tissue_expression
        assert knowledge.normal_tissue_expression["spleen"] > 0.7
        assert knowledge.normal_tissue_expression["bone_marrow"] > 0.5

    def test_unknown_target_returns_empty_expression(self, knowledge_layer, normalizer, logger):
        """An unknown target (defaults to PSMA) should return PSMA data;
        if we bypass normalization, a truly missing target returns empty."""
        # Construct a request for a target not in curated data
        req = normalizer.normalize({"target": "PSMA"}, logger)
        # Patch target to something unknown after normalization
        req.target = "NONEXISTENT_TARGET"
        knowledge = knowledge_layer.query(req, logger)

        # Should have empty expression since target is not in curated tables
        assert len(knowledge.normal_tissue_expression) == 0
        assert knowledge.tumor_expression_score == 0.5  # default

    def test_psma_evidence_level_for_prostate_cancer(self, knowledge_layer, normalizer, logger):
        """PSMA should have evidence level A for prostate_cancer."""
        req = normalizer.normalize({"target": "PSMA"}, logger)
        knowledge = knowledge_layer.query(req, logger)
        assert knowledge.evidence_level == "A"

    def test_target_knowledge_to_dict(self, knowledge_layer, normalizer, logger):
        """to_dict should serialize all key fields."""
        req = normalizer.normalize({"target": "PSMA"}, logger)
        knowledge = knowledge_layer.query(req, logger)
        d = knowledge.to_dict()

        assert "target_profile" in d
        assert "known_agents" in d
        assert "sources_used" in d
        assert d["target_profile"]["target"] == "PSMA"

    def test_known_agents_populated(self, knowledge_layer, normalizer, logger):
        """Known agents for SSTR2 should include DOTATATE."""
        req = normalizer.normalize({"target": "SSTR2"}, logger)
        knowledge = knowledge_layer.query(req, logger)
        assert "DOTATATE" in knowledge.known_agents

    def test_internalization_score_for_cd20(self, knowledge_layer, normalizer, logger):
        """CD20 has very_low internalization rate -> low score."""
        req = normalizer.normalize({"target": "CD20"}, logger)
        knowledge = knowledge_layer.query(req, logger)
        assert knowledge.internalization_score < 0.10  # very_low -> 0.05


# ===========================================================================
# 3. Parameter Builder
# ===========================================================================

class TestParameterBuilder:

    def test_small_molecule_renal_clearance(self, normalizer, knowledge_layer, parameter_builder, logger):
        """Small molecule (<60 kDa) should get renal clearance."""
        req = normalizer.normalize({
            "agent": {"class": "peptide", "size_kDa": 1.5},
            "target": "PSMA",
        }, logger)
        knowledge = knowledge_layer.query(req, logger)
        params = parameter_builder.build(req, knowledge, logger)

        assert params.pk.clearance_route == "renal"
        assert params.pk.renal_fraction > 0
        assert any("renal" in r for r in params.rules_applied)

    def test_igg_hepatic_clearance_with_fcrn(self, normalizer, knowledge_layer, parameter_builder, logger):
        """IgG (>=60 kDa, Fc region) should get hepatic clearance with FcRn recycling."""
        req = normalizer.normalize({
            "agent": {"class": "IgG", "size_kDa": 150.0, "has_fc_region": True},
            "target": "HER2",
        }, logger)
        knowledge = knowledge_layer.query(req, logger)
        params = parameter_builder.build(req, knowledge, logger)

        assert "hepatic" in params.pk.clearance_route.lower()
        assert "FcRn" in params.pk.clearance_route
        assert params.pk.renal_fraction == 0.0
        assert any("FcRn" in r for r in params.rules_applied)

    def test_small_molecule_high_penetration(self, normalizer, knowledge_layer, parameter_builder, logger):
        """Small molecule should have high tumor penetration score."""
        req = normalizer.normalize({
            "agent": {"class": "small_molecule"},
            "target": "PSMA",
        }, logger)
        knowledge = knowledge_layer.query(req, logger)
        params = parameter_builder.build(req, knowledge, logger)

        assert params.tumor.penetration_score >= 0.7

    def test_igg_low_penetration(self, normalizer, knowledge_layer, parameter_builder, logger):
        """IgG should have low tumor penetration score."""
        req = normalizer.normalize({
            "agent": {"class": "IgG", "size_kDa": 150.0},
            "target": "HER2",
        }, logger)
        knowledge = knowledge_layer.query(req, logger)
        params = parameter_builder.build(req, knowledge, logger)

        assert params.tumor.penetration_score <= 0.40

    def test_bbb_igg_very_low(self, normalizer, knowledge_layer, parameter_builder, logger):
        """IgG should have very low BBB permeability."""
        req = normalizer.normalize({
            "agent": {"class": "IgG", "size_kDa": 150.0},
            "target": "HER2",
        }, logger)
        knowledge = knowledge_layer.query(req, logger)
        params = parameter_builder.build(req, knowledge, logger)

        assert params.pk.bbb_permeability <= 0.002

    def test_bbb_small_molecule_higher(self, normalizer, knowledge_layer, parameter_builder, logger):
        """Small molecule should have higher BBB permeability than IgG."""
        req_sm = normalizer.normalize({"agent": {"class": "small_molecule"}, "target": "PSMA"}, logger)
        req_igg = normalizer.normalize({"agent": {"class": "IgG"}, "target": "HER2"}, logger)

        k_sm = knowledge_layer.query(req_sm, logger)
        k_igg = knowledge_layer.query(req_igg, logger)

        p_sm = parameter_builder.build(req_sm, k_sm, logger)
        p_igg = parameter_builder.build(req_igg, k_igg, logger)

        assert p_sm.pk.bbb_permeability > p_igg.pk.bbb_permeability

    def test_off_target_psma_includes_kidney(self, normalizer, knowledge_layer, parameter_builder, logger):
        """PSMA targets should have kidney in off-target organs or scores."""
        req = normalizer.normalize({"target": "PSMA"}, logger)
        knowledge = knowledge_layer.query(req, logger)
        params = parameter_builder.build(req, knowledge, logger)

        assert "kidney" in params.risk.off_target_scores
        assert params.risk.off_target_scores["kidney"] > 0

    def test_rules_are_logged(self, normalizer, knowledge_layer, parameter_builder, logger):
        """rules_applied should be populated with the rules that fired."""
        req = normalizer.normalize({"target": "PSMA"}, logger)
        knowledge = knowledge_layer.query(req, logger)
        params = parameter_builder.build(req, knowledge, logger)

        assert len(params.rules_applied) >= 3
        # At minimum: clearance, penetration, off-target rules
        assert any("clearance" in r or "renal" in r for r in params.rules_applied)
        assert any("penetration" in r for r in params.rules_applied)
        assert any("off_target" in r for r in params.rules_applied)

    def test_partition_coefficients_present(self, normalizer, knowledge_layer, parameter_builder, logger):
        """Partition coefficients should be populated for multiple organs."""
        req = normalizer.normalize({"target": "PSMA"}, logger)
        knowledge = knowledge_layer.query(req, logger)
        params = parameter_builder.build(req, knowledge, logger)

        assert len(params.pk.partition_coefficients) >= 10
        assert "tumor" in params.pk.partition_coefficients
        assert "liver" in params.pk.partition_coefficients

    def test_tissue_target_densities(self, normalizer, knowledge_layer, parameter_builder, logger):
        """Tissue target densities should be derived from expression scores."""
        req = normalizer.normalize({"target": "PSMA"}, logger)
        knowledge = knowledge_layer.query(req, logger)
        params = parameter_builder.build(req, knowledge, logger)

        assert len(params.tissue_target_densities) > 0
        assert params.tumor.tumor_target_density_nM > 0


# ===========================================================================
# 4. PBPK Engine V1
# ===========================================================================

class TestPBPKEngineV1:

    def test_tumor_uptake_nonzero(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, logger):
        """Simulation should produce non-zero tumor uptake."""
        raw = _make_psma617_input()
        req, knowledge, params = _build_pipeline_up_to_params(
            normalizer, knowledge_layer, parameter_builder, raw, logger
        )
        result = pbpk_engine.simulate(req, params, logger)

        assert isinstance(result, PBPKResult)
        assert result.tumor_peak_concentration_nM > 0

    def test_plasma_decreases_over_time(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, logger):
        """Plasma concentration should generally decrease over time."""
        raw = _make_psma617_input()
        req, knowledge, params = _build_pipeline_up_to_params(
            normalizer, knowledge_layer, parameter_builder, raw, logger
        )
        result = pbpk_engine.simulate(req, params, logger)

        plasma_total = result.organ_timeseries["plasma"]["total"]
        # Initial should be higher than final (accounting for possible initial rise)
        assert plasma_total[0] > plasma_total[-1]

    def test_monte_carlo_produces_spread(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, logger):
        """Monte Carlo should produce a distribution of tumor peaks."""
        raw = _make_psma617_input()
        raw["n_monte_carlo"] = 10
        req, knowledge, params = _build_pipeline_up_to_params(
            normalizer, knowledge_layer, parameter_builder, raw, logger
        )
        result = pbpk_engine.simulate(req, params, logger)

        assert result.mc_success_count > 0
        assert len(result.mc_tumor_peaks) > 0
        # There should be some spread (not all identical)
        if len(result.mc_tumor_peaks) >= 3:
            assert np.std(result.mc_tumor_peaks) > 0

    def test_14_plus_compartments_in_output(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, logger):
        """Output should contain at least 14 compartments (organs + plasma + tumor)."""
        raw = _make_psma617_input()
        req, knowledge, params = _build_pipeline_up_to_params(
            normalizer, knowledge_layer, parameter_builder, raw, logger
        )
        result = pbpk_engine.simulate(req, params, logger)

        compartment_count = len(result.organ_timeseries)
        assert compartment_count >= 14, (
            f"Expected >= 14 compartments, got {compartment_count}: "
            f"{list(result.organ_timeseries.keys())}"
        )

    def test_time_points_populated(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, logger):
        """Time points should be populated and match duration."""
        raw = _make_psma617_input()
        req, knowledge, params = _build_pipeline_up_to_params(
            normalizer, knowledge_layer, parameter_builder, raw, logger
        )
        result = pbpk_engine.simulate(req, params, logger)

        assert len(result.time_points) > 0
        assert result.time_points[0] == 0.0
        assert result.time_points[-1] <= req.duration_hours + req.time_step_hours

    def test_tumor_auc_positive(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, logger):
        """Tumor AUC should be positive."""
        raw = _make_psma617_input()
        req, knowledge, params = _build_pipeline_up_to_params(
            normalizer, knowledge_layer, parameter_builder, raw, logger
        )
        result = pbpk_engine.simulate(req, params, logger)
        assert result.tumor_auc > 0

    def test_biodistribution_at_optimal(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, logger):
        """Biodistribution at optimal time should have entries for organs."""
        raw = _make_psma617_input()
        req, knowledge, params = _build_pipeline_up_to_params(
            normalizer, knowledge_layer, parameter_builder, raw, logger
        )
        result = pbpk_engine.simulate(req, params, logger)
        assert len(result.biodistribution_at_optimal) >= 10

    def test_metrics_dict_structure(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, logger):
        """to_metrics_dict should return expected keys."""
        raw = _make_psma617_input()
        req, knowledge, params = _build_pipeline_up_to_params(
            normalizer, knowledge_layer, parameter_builder, raw, logger
        )
        result = pbpk_engine.simulate(req, params, logger)
        metrics = result.to_metrics_dict()

        assert "tumor_peak_concentration_nM" in metrics
        assert "tumor_auc" in metrics
        assert "tbr_value" in metrics
        assert "mc_ci_tumor" in metrics
        assert len(metrics["mc_ci_tumor"]) == 2


# ===========================================================================
# 5. Dosimetry Engine V1
# ===========================================================================

class TestDosimetryEngineV1:

    def test_diagnostic_isotope_returns_none(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, dosimetry_engine, logger
    ):
        """Diagnostic isotope (Ga-68) should return None from dosimetry."""
        raw = _make_dotatate_ga68_input()
        req, knowledge, params, pbpk = _build_pipeline_up_to_pbpk(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger
        )
        result = dosimetry_engine.compute(req, pbpk, logger)
        assert result is None

    def test_f18_returns_none(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, dosimetry_engine, logger):
        """F-18 (diagnostic) should also return None."""
        raw = {"agent": {"isotope": "F-18"}, "target": "PSMA", "n_monte_carlo": 3, "duration_hours": 24, "time_step_hours": 0.5}
        req, knowledge, params, pbpk = _build_pipeline_up_to_pbpk(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger
        )
        result = dosimetry_engine.compute(req, pbpk, logger)
        assert result is None

    def test_lu177_produces_organ_doses(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, dosimetry_engine, logger
    ):
        """Lu-177 should produce organ dose results."""
        raw = _make_psma617_input()
        req, knowledge, params, pbpk = _build_pipeline_up_to_pbpk(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger
        )
        result = dosimetry_engine.compute(req, pbpk, logger)

        assert isinstance(result, DosimetryResultV1)
        assert len(result.organ_doses_gy_per_gbq) > 0
        assert len(result.organ_doses_total_gy) > 0
        # Tumor should have a dose
        assert result.tumor_dose_total_gy > 0

    def test_dose_limiting_organ_identified(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, dosimetry_engine, logger
    ):
        """A dose-limiting organ should be identified."""
        raw = _make_psma617_input()
        req, knowledge, params, pbpk = _build_pipeline_up_to_pbpk(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger
        )
        result = dosimetry_engine.compute(req, pbpk, logger)

        assert result.dose_limiting_organ != ""
        assert result.dose_limiting_dose_gy >= 0

    def test_therapeutic_index_computed(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, dosimetry_engine, logger
    ):
        """Therapeutic index should be computed and positive."""
        raw = _make_psma617_input()
        req, knowledge, params, pbpk = _build_pipeline_up_to_pbpk(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger
        )
        result = dosimetry_engine.compute(req, pbpk, logger)

        assert result.therapeutic_index > 0

    def test_s_values_recorded(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, dosimetry_engine, logger
    ):
        """S-values used should be recorded for audit trail."""
        raw = _make_psma617_input()
        req, knowledge, params, pbpk = _build_pipeline_up_to_pbpk(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger
        )
        result = dosimetry_engine.compute(req, pbpk, logger)

        assert len(result.s_values_used) > 0
        assert "kidney" in result.s_values_used

    def test_no_isotope_returns_none(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, dosimetry_engine, logger
    ):
        """No isotope at all should return None."""
        raw = _make_trastuzumab_input()
        req, knowledge, params, pbpk = _build_pipeline_up_to_pbpk(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger
        )
        result = dosimetry_engine.compute(req, pbpk, logger)
        assert result is None

    def test_residence_times_populated(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine, dosimetry_engine, logger
    ):
        """Residence times should be populated for each organ."""
        raw = _make_psma617_input()
        req, knowledge, params, pbpk = _build_pipeline_up_to_pbpk(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger
        )
        result = dosimetry_engine.compute(req, pbpk, logger)
        assert len(result.residence_times) > 0


# ===========================================================================
# 6. PD Engine
# ===========================================================================

class TestPDEngine:

    def _run_pd(self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
                dosimetry_engine, pd_engine, raw, logger):
        """Helper to run modules 1-6."""
        req, knowledge, params, pbpk = _build_pipeline_up_to_pbpk(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine, raw, logger
        )
        sim_metrics = pbpk.to_metrics_dict()
        dosimetry = dosimetry_engine.compute(req, pbpk, logger)
        dosimetry_dict = dosimetry.to_dict() if dosimetry else None
        if dosimetry_dict:
            dosimetry_dict["injected_gbq"] = req.dose.activity_GBq or 7.4

        pd_result = pd_engine.evaluate(req, params, sim_metrics, dosimetry_dict, logger)
        return req, pd_result

    def test_target_occupancy_calculation(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
        dosimetry_engine, pd_engine, logger
    ):
        """Target occupancy should be calculated (C / (C + Kd))."""
        raw = _make_psma617_input()
        _, pd_result = self._run_pd(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine,
            dosimetry_engine, pd_engine, raw, logger
        )

        assert pd_result.occupancy_estimate is not None
        assert 0.0 <= pd_result.occupancy_estimate <= 1.0
        assert any("occupancy" in f for f in pd_result.formulas_used)

    def test_radiotheranostic_pd_cytotoxic(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
        dosimetry_engine, pd_engine, logger
    ):
        """Lu-177 therapeutic isotope should produce a radiotheranostic effect."""
        raw = _make_psma617_input()
        _, pd_result = self._run_pd(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine,
            dosimetry_engine, pd_engine, raw, logger
        )

        assert pd_result.effect_type == "radiotheranostic"
        assert "cytotoxic" in pd_result.effect_direction or "subtherapeutic" in pd_result.effect_direction

    def test_diagnostic_isotope_no_therapeutic_effect(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
        dosimetry_engine, pd_engine, logger
    ):
        """Ga-68 (diagnostic) should result in no therapeutic effect."""
        raw = _make_dotatate_ga68_input()
        _, pd_result = self._run_pd(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine,
            dosimetry_engine, pd_engine, raw, logger
        )

        assert pd_result.effect_type == "diagnostic"
        assert pd_result.effect_direction == "imaging_visualization"
        assert any("diagnostic" in r for r in pd_result.rules_activated)

    def test_no_isotope_targeted_pd(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
        dosimetry_engine, pd_engine, logger
    ):
        """No isotope (Trastuzumab) should produce targeted PD."""
        raw = _make_trastuzumab_input()
        _, pd_result = self._run_pd(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine,
            dosimetry_engine, pd_engine, raw, logger
        )

        assert pd_result.effect_type == "targeted"
        assert "tumor_growth_inhibition" in pd_result.effect_direction

    def test_causal_rules_psma(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
        dosimetry_engine, pd_engine, logger
    ):
        """PSMA causal rules should flag kidney and salivary_glands toxicity."""
        raw = _make_psma617_input()
        _, pd_result = self._run_pd(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine,
            dosimetry_engine, pd_engine, raw, logger
        )

        tox_organs = [r["organ"] for r in pd_result.toxicity_risks]
        assert "kidney" in tox_organs or "salivary_glands" in tox_organs

    def test_causal_rules_her2_cardiotoxicity(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
        dosimetry_engine, pd_engine, logger
    ):
        """HER2 causal rules should flag heart (cardiotoxicity)."""
        raw = _make_trastuzumab_input()
        _, pd_result = self._run_pd(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine,
            dosimetry_engine, pd_engine, raw, logger
        )

        tox_organs = [r["organ"] for r in pd_result.toxicity_risks]
        assert "heart" in tox_organs

    def test_causal_rules_cd20_myelosuppression(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
        dosimetry_engine, pd_engine, logger
    ):
        """CD20 causal rules should flag bone_marrow (myelosuppression)."""
        raw = {
            "target": "CD20",
            "agent": {
                "name": "Rituximab",
                "class": "IgG",
                "size_kDa": 145.0,
                "has_fc_region": True,
            },
            "dose": {"mass_mg": 375.0},
            "n_monte_carlo": 3,
            "duration_hours": 24,
            "time_step_hours": 0.5,
        }
        _, pd_result = self._run_pd(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine,
            dosimetry_engine, pd_engine, raw, logger
        )

        tox_organs = [r["organ"] for r in pd_result.toxicity_risks]
        assert "bone_marrow" in tox_organs or "spleen" in tox_organs

    def test_plausibility_and_confidence_scores(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
        dosimetry_engine, pd_engine, logger
    ):
        """Plausibility and confidence scores should be between 0 and 1."""
        raw = _make_psma617_input()
        _, pd_result = self._run_pd(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine,
            dosimetry_engine, pd_engine, raw, logger
        )

        assert 0.0 <= pd_result.biological_plausibility_score <= 1.0
        assert 0.0 <= pd_result.confidence_score <= 1.0

    def test_rationale_text_not_empty(
        self, normalizer, knowledge_layer, parameter_builder, pbpk_engine,
        dosimetry_engine, pd_engine, logger
    ):
        """Rationale text should be generated."""
        raw = _make_psma617_input()
        _, pd_result = self._run_pd(
            normalizer, knowledge_layer, parameter_builder, pbpk_engine,
            dosimetry_engine, pd_engine, raw, logger
        )

        assert pd_result.rationale_text != ""
        assert len(pd_result.rationale_text) > 20


# ===========================================================================
# 7. V1 Orchestrator (integration)
# ===========================================================================

class TestV1Orchestrator:

    @pytest.fixture
    def orchestrator(self):
        return V1Orchestrator(use_apis=False)

    def test_full_pipeline_psma617_lu177(self, orchestrator):
        """Full pipeline with PSMA-617 + Lu-177 should complete without errors."""
        raw = _make_psma617_input()
        result = orchestrator.run(raw)

        assert isinstance(result, V1PipelineResult)
        assert len(result.errors) == 0, f"Pipeline errors: {result.errors}"
        assert result.normalized_request is not None
        assert result.knowledge is not None
        assert result.parameters is not None
        assert result.pbpk_result is not None
        assert result.dosimetry is not None  # Lu-177 is therapeutic
        assert result.pd_result is not None
        assert result.decision is not None
        assert result.pd_result.effect_type == "radiotheranostic"

    def test_full_pipeline_dotatate_ga68_diagnostic(self, orchestrator):
        """Full pipeline with DOTATATE + Ga-68 should produce diagnostic result."""
        raw = _make_dotatate_ga68_input()
        result = orchestrator.run(raw)

        assert isinstance(result, V1PipelineResult)
        assert len(result.errors) == 0, f"Pipeline errors: {result.errors}"
        assert result.dosimetry is None  # Ga-68 is diagnostic
        assert result.pd_result is not None
        assert result.pd_result.effect_type == "diagnostic"

    def test_full_pipeline_trastuzumab_no_isotope(self, orchestrator):
        """Full pipeline with Trastuzumab (no isotope) should produce targeted PD."""
        raw = _make_trastuzumab_input()
        result = orchestrator.run(raw)

        assert isinstance(result, V1PipelineResult)
        assert len(result.errors) == 0, f"Pipeline errors: {result.errors}"
        assert result.dosimetry is None  # No isotope
        assert result.pd_result is not None
        assert result.pd_result.effect_type == "targeted"

    def test_logs_are_generated(self, orchestrator):
        """Pipeline should generate logs."""
        raw = _make_psma617_input()
        result = orchestrator.run(raw)

        assert len(result.logs) > 0
        # Check that logs have expected structure
        first_log = result.logs[0]
        assert "module" in first_log
        assert "event" in first_log

    def test_confidence_per_module_populated(self, orchestrator):
        """confidence_per_module should have entries for key modules."""
        raw = _make_psma617_input()
        result = orchestrator.run(raw)

        assert len(result.confidence_per_module) > 0
        assert "knowledge" in result.confidence_per_module
        assert "parameters" in result.confidence_per_module
        assert "pbpk" in result.confidence_per_module
        assert "pd" in result.confidence_per_module
        assert "decision" in result.confidence_per_module

        # All confidence values should be between 0 and 1
        for module, conf in result.confidence_per_module.items():
            assert 0.0 <= conf <= 1.0, f"Module {module} confidence {conf} out of range"

    def test_to_dict_serialization(self, orchestrator):
        """to_dict should produce a valid dict with expected top-level keys."""
        raw = _make_psma617_input()
        result = orchestrator.run(raw)
        d = result.to_dict()

        assert "request_id" in d
        assert "request_summary" in d
        assert "simulation" in d
        assert "confidence_per_module" in d
        assert "warnings" in d
        assert "errors" in d

    def test_to_api_response(self, orchestrator):
        """to_api_response should produce a lighter response."""
        raw = _make_psma617_input()
        result = orchestrator.run(raw)
        api = result.to_api_response()

        assert "request_id" in api
        assert "execution_trace_count" in api

    def test_empty_input_still_runs(self, orchestrator):
        """Even empty input should produce a result (with defaults)."""
        result = orchestrator.run({})

        assert isinstance(result, V1PipelineResult)
        assert len(result.errors) == 0, f"Pipeline errors: {result.errors}"
        assert result.normalized_request is not None
        assert result.normalized_request.target == "PSMA"

    def test_request_id_propagated(self, orchestrator):
        """Custom request_id should be propagated through the pipeline."""
        raw = _make_psma617_input()
        raw["request_id"] = "custom-test-id-123"
        result = orchestrator.run(raw)

        assert result.request_id == "custom-test-id-123"
