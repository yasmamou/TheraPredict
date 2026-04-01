"""V1 Pipeline Benchmark Tests.

Validates the V1 orchestrator against known theranostic cases.
Each benchmark runs the full 7-module pipeline with use_apis=False
and checks that the output matches clinical expectations.

Run with:
    PYTHONPATH=src pytest tests/benchmark/ -v
"""

from __future__ import annotations

import json
import sys
from typing import Any

import pytest

from theranostics.orchestrator_v1 import V1Orchestrator, V1PipelineResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def orchestrator() -> V1Orchestrator:
    """Shared orchestrator instance (no API calls)."""
    return V1Orchestrator(use_apis=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_and_validate_basics(
    orchestrator: V1Orchestrator,
    raw_input: dict[str, Any],
    label: str,
) -> V1PipelineResult:
    """Run pipeline and assert that all modules produced output."""
    result = orchestrator.run(raw_input)

    assert result.request_id, f"[{label}] Missing request_id"
    assert result.normalized_request is not None, f"[{label}] Normalization failed"
    assert result.knowledge is not None, f"[{label}] Knowledge layer failed"
    assert result.parameters is not None, f"[{label}] Parameter builder failed"
    assert result.pbpk_result is not None, f"[{label}] PBPK engine failed"
    assert result.pd_result is not None, f"[{label}] PD engine failed"
    assert result.decision is not None, f"[{label}] Decision engine failed"
    assert len(result.errors) == 0, (
        f"[{label}] Pipeline errors: {result.errors}"
    )
    assert len(result.logs) > 0, f"[{label}] No logs generated"

    return result


def _get_off_target_organs(result: V1PipelineResult) -> list[str]:
    """Extract off-target organ list from parameters."""
    return result.parameters.risk.off_target_organs


def _get_off_target_scores(result: V1PipelineResult) -> dict[str, float]:
    """Extract off-target scores dict from parameters."""
    return result.parameters.risk.off_target_scores


def _get_clearance_route(result: V1PipelineResult) -> str:
    """Extract clearance route from parameters."""
    return result.parameters.pk.clearance_route


def _print_summary(label: str, result: V1PipelineResult) -> None:
    """Print a human-readable summary for manual review."""
    sep = "=" * 72
    print(f"\n{sep}")
    print(f"  BENCHMARK: {label}")
    print(sep)
    print(f"  Target:           {result.normalized_request.target}")
    print(f"  Agent:            {result.normalized_request.agent.name}")
    print(f"  Agent class:      {result.normalized_request.agent.agent_class}")
    print(f"  Isotope:          {result.normalized_request.agent.isotope}")
    print(f"  Clearance route:  {_get_clearance_route(result)}")
    print(f"  BBB permeability: {result.parameters.pk.bbb_permeability}")
    print(f"  Off-target organs: {_get_off_target_organs(result)}")
    print(f"  Off-target scores: {_get_off_target_scores(result)}")

    if result.pbpk_result:
        print(f"  Tumor peak (nM):  {result.pbpk_result.tumor_peak_concentration_nM:.2f}")
        print(f"  TBR peak:         {result.pbpk_result.tbr_peak:.2f}")
        print(f"  Plasma t1/2 (h):  {result.pbpk_result.plasma_half_life_h:.2f}")

    if result.dosimetry:
        print(f"  Dosimetry:        PRESENT")
        print(f"  Tumor dose (Gy):  {result.dosimetry.tumor_dose_total_gy:.2f}")
        print(f"  Dose-limiting:    {result.dosimetry.dose_limiting_organ}")
        print(f"  Therapeutic idx:  {result.dosimetry.therapeutic_index:.2f}")
    else:
        print(f"  Dosimetry:        ABSENT (diagnostic isotope or none)")

    if result.pd_result:
        print(f"  Effect direction: {result.pd_result.effect_direction}")
        print(f"  Effect type:      {result.pd_result.effect_type}")
        print(f"  Target engage.:   {result.pd_result.target_engagement_score:.3f}")
        tox_organs = [r["organ"] for r in result.pd_result.toxicity_risks]
        print(f"  Toxicity organs:  {tox_organs}")

    if result.decision:
        print(f"  Decision score:   {result.decision.score.combined:.3f}")
        print(f"  Why:              {result.decision.why}")
        print(f"  Why not:          {result.decision.why_not}")

    print(f"  Confidence:       {result.confidence_per_module}")
    print(f"  Warnings count:   {len(result.warnings)}")
    print(f"  Log entries:      {len(result.logs)}")
    print(sep)


# ===========================================================================
# Benchmark 1: PSMA (prostate cancer, PSMA-617, Lu-177)
# ===========================================================================

PSMA_INPUT: dict[str, Any] = {
    "target": "PSMA",
    "indication": "prostate_cancer",
    "agent": {
        "name": "PSMA-617",
        "class": "small_molecule",
        "isotope": "Lu-177",
        "kd_nM": 2.3,
        "kon_per_M_per_s": 1.2e6,
        "internalization": True,
    },
    "dose": {"activity_GBq": 7.4},
    "tumor": {"type": "prostate", "volume_ml": 40.0, "stage": "IV"},
    "patient": {"weight_kg": 75.0, "sex": "male", "age": 68},
    "n_monte_carlo": 50,
    "duration_hours": 168.0,
}


class TestPSMABenchmark:
    """PSMA-617 / Lu-177 for metastatic prostate cancer."""

    @pytest.fixture(autouse=True)
    def _run(self, orchestrator: V1Orchestrator) -> None:
        self.result = _run_and_validate_basics(orchestrator, PSMA_INPUT, "PSMA")
        _print_summary("PSMA-617 / Lu-177 / Prostate Cancer", self.result)

    # -- Off-target organs --------------------------------------------------

    def test_kidney_is_off_target(self) -> None:
        """Kidney must be flagged (PSMA expressed in proximal tubule)."""
        scores = _get_off_target_scores(self.result)
        assert "kidney" in scores, (
            f"Kidney not in off-target scores: {scores}"
        )

    def test_salivary_glands_in_off_target_scores(self) -> None:
        """Salivary glands should appear in off-target scores."""
        scores = _get_off_target_scores(self.result)
        assert "salivary_glands" in scores, (
            f"Salivary glands not in off-target scores: {scores}"
        )

    # -- Clearance ----------------------------------------------------------

    def test_renal_clearance(self) -> None:
        """Small molecule (<60 kDa) should have renal clearance."""
        route = _get_clearance_route(self.result)
        assert "renal" in route.lower(), (
            f"Expected renal clearance, got: {route}"
        )

    # -- Dosimetry ----------------------------------------------------------

    def test_dosimetry_present(self) -> None:
        """Lu-177 is therapeutic -> dosimetry must be computed."""
        assert self.result.dosimetry is not None, (
            "Dosimetry should be present for therapeutic isotope Lu-177"
        )

    def test_dosimetry_tumor_dose_positive(self) -> None:
        """Tumor should receive a non-trivial dose."""
        assert self.result.dosimetry.tumor_dose_total_gy > 0, (
            "Tumor dose should be > 0 Gy"
        )

    def test_dosimetry_has_dose_limiting_organ(self) -> None:
        """A dose-limiting organ must be identified."""
        assert self.result.dosimetry.dose_limiting_organ, (
            "Dose-limiting organ should be identified"
        )

    # -- PD / Effect --------------------------------------------------------

    def test_effect_direction_cytotoxic(self) -> None:
        """Effect direction should indicate cytotoxicity."""
        direction = self.result.pd_result.effect_direction
        assert "cytotoxic" in direction.lower(), (
            f"Expected cytotoxic effect, got: {direction}"
        )

    def test_effect_type_radiotheranostic(self) -> None:
        """Effect type should be radiotheranostic."""
        assert self.result.pd_result.effect_type == "radiotheranostic", (
            f"Expected radiotheranostic, got: {self.result.pd_result.effect_type}"
        )

    # -- Logs ---------------------------------------------------------------

    def test_logs_generated(self) -> None:
        """Pipeline must produce audit logs."""
        assert len(self.result.logs) >= 5, (
            f"Expected at least 5 log entries, got {len(self.result.logs)}"
        )


# ===========================================================================
# Benchmark 2: SSTR2 (neuroendocrine tumor, DOTATATE, Lu-177)
# ===========================================================================

SSTR2_INPUT: dict[str, Any] = {
    "target": "SSTR2",
    "indication": "neuroendocrine_tumor",
    "agent": {
        "name": "DOTATATE",
        "class": "peptide",
        "isotope": "Lu-177",
        "kd_nM": 1.5,
        "kon_per_M_per_s": 8e5,
        "internalization": True,
    },
    "dose": {"activity_GBq": 7.4},
    "tumor": {"type": "neuroendocrine", "volume_ml": 30.0, "stage": "IV"},
    "patient": {"weight_kg": 70.0, "sex": "female", "age": 58},
    "n_monte_carlo": 50,
    "duration_hours": 168.0,
}


class TestSSTR2Benchmark:
    """DOTATATE / Lu-177 for neuroendocrine tumors."""

    @pytest.fixture(autouse=True)
    def _run(self, orchestrator: V1Orchestrator) -> None:
        self.result = _run_and_validate_basics(orchestrator, SSTR2_INPUT, "SSTR2")
        _print_summary("DOTATATE / Lu-177 / Neuroendocrine Tumor", self.result)

    # -- Off-target organs --------------------------------------------------

    def test_spleen_is_off_target(self) -> None:
        """Spleen must be flagged (high SSTR2 expression)."""
        scores = _get_off_target_scores(self.result)
        assert "spleen" in scores, (
            f"Spleen not in off-target scores: {scores}"
        )

    def test_kidney_in_off_target_scores(self) -> None:
        """Kidney should appear in off-target scores (peptide renal clearance)."""
        scores = _get_off_target_scores(self.result)
        assert "kidney" in scores, (
            f"Kidney not in off-target scores: {scores}"
        )

    # -- Clearance ----------------------------------------------------------

    def test_renal_clearance(self) -> None:
        """Peptide (<60 kDa) should have renal clearance."""
        route = _get_clearance_route(self.result)
        assert "renal" in route.lower(), (
            f"Expected renal clearance, got: {route}"
        )

    # -- Dosimetry ----------------------------------------------------------

    def test_dosimetry_present(self) -> None:
        """Lu-177 is therapeutic -> dosimetry must be computed."""
        assert self.result.dosimetry is not None, (
            "Dosimetry should be present for therapeutic isotope Lu-177"
        )

    def test_dosimetry_tumor_dose_positive(self) -> None:
        """Tumor should receive a non-trivial dose."""
        assert self.result.dosimetry.tumor_dose_total_gy > 0, (
            "Tumor dose should be > 0 Gy"
        )

    def test_dose_limiting_organ_identified(self) -> None:
        """A dose-limiting organ must be identified."""
        dlo = self.result.dosimetry.dose_limiting_organ
        assert dlo, "Dose-limiting organ should be identified"

    # -- PD / Effect --------------------------------------------------------

    def test_effect_direction_cytotoxic(self) -> None:
        """Effect direction should indicate cytotoxicity."""
        direction = self.result.pd_result.effect_direction
        assert "cytotoxic" in direction.lower(), (
            f"Expected cytotoxic effect, got: {direction}"
        )

    def test_effect_type_radiotheranostic(self) -> None:
        """Effect type should be radiotheranostic."""
        assert self.result.pd_result.effect_type == "radiotheranostic", (
            f"Expected radiotheranostic, got: {self.result.pd_result.effect_type}"
        )

    # -- Logs ---------------------------------------------------------------

    def test_logs_generated(self) -> None:
        """Pipeline must produce audit logs."""
        assert len(self.result.logs) >= 5


# ===========================================================================
# Benchmark 3: HER2 (breast cancer, Trastuzumab-like IgG, Zr-89)
# ===========================================================================

HER2_INPUT: dict[str, Any] = {
    "target": "HER2",
    "indication": "breast_cancer",
    "agent": {
        "name": "Trastuzumab-Zr89",
        "class": "IgG",
        "isotope": "Zr-89",
        "size_kDa": 150.0,
        "kd_nM": 0.1,
        "kon_per_M_per_s": 1.5e5,
        "internalization": True,
        "has_fc_region": True,
    },
    "dose": {"activity_MBq": 74.0},
    "tumor": {"type": "breast", "volume_ml": 25.0, "stage": "III"},
    "patient": {"weight_kg": 65.0, "sex": "female", "age": 52},
    "n_monte_carlo": 50,
    "duration_hours": 168.0,
}


class TestHER2Benchmark:
    """Trastuzumab-Zr89 (IgG) for HER2+ breast cancer imaging."""

    @pytest.fixture(autouse=True)
    def _run(self, orchestrator: V1Orchestrator) -> None:
        self.result = _run_and_validate_basics(orchestrator, HER2_INPUT, "HER2")
        _print_summary("Trastuzumab-Zr89 / IgG / Breast Cancer", self.result)

    # -- Off-target organs --------------------------------------------------

    def test_liver_is_off_target(self) -> None:
        """Liver must be flagged (Fc-mediated hepatic uptake)."""
        scores = _get_off_target_scores(self.result)
        assert "liver" in scores, (
            f"Liver not in off-target scores: {scores}"
        )

    # -- Clearance ----------------------------------------------------------

    def test_hepatic_clearance(self) -> None:
        """IgG (>60 kDa) should have hepatic clearance."""
        route = _get_clearance_route(self.result)
        assert "hepatic" in route.lower(), (
            f"Expected hepatic clearance, got: {route}"
        )

    # -- Dosimetry ----------------------------------------------------------

    def test_dosimetry_absent(self) -> None:
        """Zr-89 is diagnostic -> no dosimetry should be computed."""
        assert self.result.dosimetry is None, (
            "Dosimetry should be absent for diagnostic isotope Zr-89"
        )

    # -- PD / Effect --------------------------------------------------------

    def test_effect_type_diagnostic(self) -> None:
        """Effect type should be diagnostic (Zr-89 is imaging isotope)."""
        assert self.result.pd_result.effect_type == "diagnostic", (
            f"Expected diagnostic, got: {self.result.pd_result.effect_type}"
        )

    def test_effect_direction_imaging(self) -> None:
        """Effect direction should indicate imaging, not cytotoxicity."""
        direction = self.result.pd_result.effect_direction
        assert "imaging" in direction.lower() or "visualization" in direction.lower(), (
            f"Expected imaging/visualization effect, got: {direction}"
        )

    # -- BBB permeability ---------------------------------------------------

    def test_low_bbb_permeability(self) -> None:
        """IgG should have very low BBB permeability."""
        bbb = self.result.parameters.pk.bbb_permeability
        assert bbb <= 0.01, (
            f"IgG BBB permeability should be <= 0.01, got: {bbb}"
        )

    # -- Binding site barrier -----------------------------------------------

    def test_binding_site_barrier_risk(self) -> None:
        """IgG with high affinity (low Kd) should have binding site barrier penalty."""
        penalty = self.result.parameters.tumor.binding_site_barrier_penalty
        assert penalty > 0, (
            f"Expected binding site barrier penalty > 0 for high-affinity IgG, got: {penalty}"
        )

    # -- Tumor uptake -------------------------------------------------------

    def test_tumor_uptake_moderate(self) -> None:
        """IgG tumor uptake should be lower than small-molecule benchmarks (slower kinetics)."""
        penetration = self.result.parameters.tumor.penetration_score
        assert penetration < 0.5, (
            f"IgG penetration score should be < 0.5 (slow extravasation), got: {penetration}"
        )

    # -- Logs ---------------------------------------------------------------

    def test_logs_generated(self) -> None:
        """Pipeline must produce audit logs."""
        assert len(self.result.logs) >= 5


# ===========================================================================
# Cross-benchmark comparisons
# ===========================================================================

class TestCrossBenchmarkSanity:
    """Sanity checks across all three benchmarks."""

    @pytest.fixture(autouse=True)
    def _run_all(self, orchestrator: V1Orchestrator) -> None:
        self.psma = _run_and_validate_basics(orchestrator, PSMA_INPUT, "PSMA-cross")
        self.sstr2 = _run_and_validate_basics(orchestrator, SSTR2_INPUT, "SSTR2-cross")
        self.her2 = _run_and_validate_basics(orchestrator, HER2_INPUT, "HER2-cross")

    def test_therapeutic_isotopes_have_dosimetry(self) -> None:
        """Lu-177 cases must have dosimetry; Zr-89 must not."""
        assert self.psma.dosimetry is not None
        assert self.sstr2.dosimetry is not None
        assert self.her2.dosimetry is None

    def test_small_agents_renal_large_agents_hepatic(self) -> None:
        """Small molecule and peptide -> renal; IgG -> hepatic."""
        assert "renal" in _get_clearance_route(self.psma).lower()
        assert "renal" in _get_clearance_route(self.sstr2).lower()
        assert "hepatic" in _get_clearance_route(self.her2).lower()

    def test_igg_lower_penetration_than_small_molecule(self) -> None:
        """IgG penetration score should be lower than small molecule."""
        psma_pen = self.psma.parameters.tumor.penetration_score
        her2_pen = self.her2.parameters.tumor.penetration_score
        assert her2_pen < psma_pen, (
            f"IgG penetration ({her2_pen}) should be < small molecule ({psma_pen})"
        )

    def test_igg_lower_bbb_than_small_molecule(self) -> None:
        """IgG BBB permeability should be lower than small molecule."""
        psma_bbb = self.psma.parameters.pk.bbb_permeability
        her2_bbb = self.her2.parameters.pk.bbb_permeability
        assert her2_bbb < psma_bbb, (
            f"IgG BBB ({her2_bbb}) should be < small molecule BBB ({psma_bbb})"
        )

    def test_all_pipelines_have_decision_scores(self) -> None:
        """Every benchmark should produce a combined decision score > 0."""
        for label, res in [("PSMA", self.psma), ("SSTR2", self.sstr2), ("HER2", self.her2)]:
            score = res.decision.score.combined
            assert score > 0, f"[{label}] Decision score should be > 0, got {score}"

    def test_all_pipelines_produce_confidence(self) -> None:
        """Every benchmark should have confidence per module."""
        for label, res in [("PSMA", self.psma), ("SSTR2", self.sstr2), ("HER2", self.her2)]:
            assert len(res.confidence_per_module) >= 3, (
                f"[{label}] Expected at least 3 module confidences, "
                f"got {len(res.confidence_per_module)}"
            )
