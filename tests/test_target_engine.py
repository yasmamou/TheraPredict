"""Tests for the Target Engine."""

from theranostics.engines.target import TargetEngine


def test_list_targets():
    engine = TargetEngine()
    targets = engine.list_targets()
    assert "HER2" in targets
    assert "PSMA" in targets
    assert "SSTR2" in targets
    assert "CD20" in targets


def test_assess_her2_breast():
    engine = TargetEngine()
    result = engine.assess("HER2", "breast")

    assert result.target_name == "HER2"
    assert result.tumor_type == "breast"
    assert 0.0 < result.expression_score < 1.0
    assert result.accessibility_score > 0.5  # Cell surface target
    assert result.evidence_level == "A"
    assert len(result.known_agents) > 0


def test_assess_psma_prostate():
    engine = TargetEngine()
    result = engine.assess("PSMA", "prostate")

    assert result.expression_score > 0.5  # High expression
    assert result.evidence_level == "A"


def test_assess_unknown_target():
    engine = TargetEngine()
    result = engine.assess("UNKNOWN_TARGET", "breast")

    assert result.evidence_level == "D"
    assert result.expression_score == 0.3  # Default


def test_assess_unknown_tumor_type():
    engine = TargetEngine()
    result = engine.assess("HER2", "unknown_cancer")

    assert result.evidence_level == "D"
    assert len(result.notes) > 0


def test_assess_with_patient_expression():
    engine = TargetEngine()
    result = engine.assess("HER2", "breast", patient_expression=0.9)

    assert result.expression_score == 0.9
    assert "patient-specific" in result.notes[0].lower() or "patient" in result.notes[0].lower()


def test_theranostic_relevance():
    engine = TargetEngine()
    her2 = engine.assess("HER2", "breast")
    unknown = engine.assess("UNKNOWN", "breast")

    # Known theranostic target should score higher
    assert her2.theranostic_relevance > unknown.theranostic_relevance
