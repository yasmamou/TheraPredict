"""Target Engine — assess theranostic relevance of molecular targets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TargetAssessment:
    target_name: str
    tumor_type: str
    expression_score: float  # [0, 1]
    expression_ci_low: float
    expression_ci_high: float
    accessibility_score: float  # [0, 1]
    theranostic_relevance: float  # [0, 1]
    diagnostic_score: float  # [0, 1]
    therapeutic_score: float  # [0, 1]
    evidence_level: str  # A, B, C, D
    known_agents: list[str]
    notes: list[str]


# Curated target knowledge base
_TARGET_DB: dict[str, dict] = {
    "HER2": {
        "full_name": "Human Epidermal Growth Factor Receptor 2",
        "gene": "ERBB2",
        "type": "receptor_tyrosine_kinase",
        "location": "cell_surface",
        "shedding_risk": 0.2,
        "internalization": True,
        "expression_by_tumor": {
            "breast": {"frequency": 0.20, "intensity": 0.85, "evidence": "A"},
            "gastric": {"frequency": 0.18, "intensity": 0.75, "evidence": "A"},
            "colorectal": {"frequency": 0.05, "intensity": 0.40, "evidence": "B"},
            "lung": {"frequency": 0.03, "intensity": 0.35, "evidence": "B"},
            "ovarian": {"frequency": 0.10, "intensity": 0.50, "evidence": "B"},
        },
        "known_agents": ["Trastuzumab", "Pertuzumab", "T-DM1", "T-DXd", "Nanobody 2Rs15d"],
        "theranostic_pairs": [
            {"diagnostic": "89Zr-Trastuzumab", "therapeutic": "177Lu-Trastuzumab"},
            {"diagnostic": "68Ga-Nanobody", "therapeutic": "177Lu-Nanobody"},
        ],
        "normal_tissue_expression": {
            "heart": "moderate",
            "gut": "moderate",
            "liver": "low-moderate",
            "kidneys": "low",
        },
    },
    "PSMA": {
        "full_name": "Prostate-Specific Membrane Antigen",
        "gene": "FOLH1",
        "type": "membrane_enzyme",
        "location": "cell_surface",
        "shedding_risk": 0.05,
        "internalization": True,
        "expression_by_tumor": {
            "prostate": {"frequency": 0.90, "intensity": 0.90, "evidence": "A"},
            "breast": {"frequency": 0.30, "intensity": 0.40, "evidence": "C"},
            "colorectal": {"frequency": 0.25, "intensity": 0.35, "evidence": "C"},
            "lung": {"frequency": 0.15, "intensity": 0.30, "evidence": "C"},
        },
        "known_agents": ["PSMA-617", "PSMA-11", "PSMA I&T", "J591"],
        "theranostic_pairs": [
            {"diagnostic": "68Ga-PSMA-11", "therapeutic": "177Lu-PSMA-617"},
            {"diagnostic": "18F-DCFPyL", "therapeutic": "225Ac-PSMA-617"},
        ],
        "normal_tissue_expression": {
            "kidneys": "very_high",
            "salivary_glands": "high",
            "liver": "low",
            "gut": "moderate",
        },
    },
    "SSTR2": {
        "full_name": "Somatostatin Receptor Type 2",
        "gene": "SSTR2",
        "type": "gpcr",
        "location": "cell_surface",
        "shedding_risk": 0.0,
        "internalization": True,
        "expression_by_tumor": {
            "neuroendocrine": {"frequency": 0.85, "intensity": 0.90, "evidence": "A"},
            "meningioma": {"frequency": 0.90, "intensity": 0.80, "evidence": "B"},
            "pheochromocytoma": {"frequency": 0.70, "intensity": 0.70, "evidence": "B"},
            "lung": {"frequency": 0.05, "intensity": 0.20, "evidence": "C"},
        },
        "known_agents": ["DOTATATE", "DOTATOC", "DOTANOC"],
        "theranostic_pairs": [
            {"diagnostic": "68Ga-DOTATATE", "therapeutic": "177Lu-DOTATATE"},
            {"diagnostic": "68Ga-DOTATOC", "therapeutic": "90Y-DOTATOC"},
        ],
        "normal_tissue_expression": {
            "spleen": "high",
            "kidneys": "moderate",
            "adrenals": "moderate",
            "gut": "low",
        },
    },
    "CD20": {
        "full_name": "B-Lymphocyte Antigen CD20",
        "gene": "MS4A1",
        "type": "membrane_protein",
        "location": "cell_surface",
        "shedding_risk": 0.0,
        "internalization": False,  # CD20 does not internalize efficiently
        "expression_by_tumor": {
            "lymphoma": {"frequency": 0.95, "intensity": 0.90, "evidence": "A"},
            "cll": {"frequency": 0.85, "intensity": 0.70, "evidence": "A"},
        },
        "known_agents": ["Rituximab", "Obinutuzumab", "Ibritumomab tiuxetan"],
        "theranostic_pairs": [
            {"diagnostic": "89Zr-Rituximab", "therapeutic": "90Y-Ibritumomab"},
        ],
        "normal_tissue_expression": {
            "spleen": "very_high",
            "bone_marrow": "high",
            "lymph_nodes": "high",
        },
    },
    "FAP": {
        "full_name": "Fibroblast Activation Protein",
        "gene": "FAP",
        "type": "membrane_enzyme",
        "location": "cell_surface",
        "shedding_risk": 0.1,
        "internalization": True,
        "expression_by_tumor": {
            "breast": {"frequency": 0.80, "intensity": 0.70, "evidence": "B"},
            "colorectal": {"frequency": 0.75, "intensity": 0.65, "evidence": "B"},
            "lung": {"frequency": 0.75, "intensity": 0.60, "evidence": "B"},
            "pancreatic": {"frequency": 0.85, "intensity": 0.80, "evidence": "B"},
            "ovarian": {"frequency": 0.70, "intensity": 0.60, "evidence": "C"},
        },
        "known_agents": ["FAPI-04", "FAPI-46", "FAP-2286"],
        "theranostic_pairs": [
            {"diagnostic": "68Ga-FAPI-46", "therapeutic": "177Lu-FAP-2286"},
        ],
        "normal_tissue_expression": {
            "joints": "moderate",
            "uterus": "moderate",
        },
    },
}


class TargetEngine:
    """Evaluate theranostic target relevance and accessibility."""

    def __init__(self) -> None:
        self.target_db = _TARGET_DB

    def list_targets(self) -> list[str]:
        return list(self.target_db.keys())

    def get_target_info(self, target_name: str) -> Optional[dict]:
        return self.target_db.get(target_name)

    def assess(
        self,
        target_name: str,
        tumor_type: str,
        patient_expression: Optional[float] = None,
    ) -> TargetAssessment:
        """Assess a target for a given tumor type.

        Args:
            target_name: e.g., "HER2", "PSMA"
            tumor_type: e.g., "breast", "prostate"
            patient_expression: if known, patient-specific expression [0, 1]

        Returns:
            TargetAssessment with scores and metadata
        """
        target_info = self.target_db.get(target_name)
        notes: list[str] = []

        if target_info is None:
            notes.append(f"Target {target_name} not in database. Using default estimates.")
            return TargetAssessment(
                target_name=target_name,
                tumor_type=tumor_type,
                expression_score=0.3,
                expression_ci_low=0.05,
                expression_ci_high=0.60,
                accessibility_score=0.5,
                theranostic_relevance=0.3,
                diagnostic_score=0.3,
                therapeutic_score=0.3,
                evidence_level="D",
                known_agents=[],
                notes=notes,
            )

        # Expression scoring
        tumor_data = target_info["expression_by_tumor"].get(tumor_type)
        if tumor_data:
            pop_frequency = tumor_data["frequency"]
            pop_intensity = tumor_data["intensity"]
            evidence = tumor_data["evidence"]
        else:
            pop_frequency = 0.1
            pop_intensity = 0.3
            evidence = "D"
            notes.append(
                f"{target_name} expression in {tumor_type} is not well characterized."
            )

        # If patient-specific data is available, use it; otherwise use population
        if patient_expression is not None:
            expression_score = patient_expression
            ci_width = 0.1  # Narrower CI with patient data
            notes.append("Using patient-specific expression data.")
        else:
            expression_score = pop_frequency * pop_intensity
            ci_width = 0.25  # Wide CI with population data
            notes.append("Using population-level expression estimate.")

        ci_low = max(0.0, expression_score - ci_width)
        ci_high = min(1.0, expression_score + ci_width)

        # Accessibility scoring
        accessibility = self._compute_accessibility(target_info)

        # Theranostic relevance
        has_diagnostic = len(target_info.get("theranostic_pairs", [])) > 0
        has_therapeutic = any(
            "therapeutic" in p for p in target_info.get("theranostic_pairs", [])
        )
        diagnostic_score = 0.8 if has_diagnostic else 0.3
        therapeutic_score = 0.8 if has_therapeutic else 0.3

        # Combined
        theranostic_relevance = (
            0.4 * expression_score + 0.3 * accessibility + 0.3 * (diagnostic_score + therapeutic_score) / 2
        )

        return TargetAssessment(
            target_name=target_name,
            tumor_type=tumor_type,
            expression_score=round(expression_score, 3),
            expression_ci_low=round(ci_low, 3),
            expression_ci_high=round(ci_high, 3),
            accessibility_score=round(accessibility, 3),
            theranostic_relevance=round(theranostic_relevance, 3),
            diagnostic_score=round(diagnostic_score, 3),
            therapeutic_score=round(therapeutic_score, 3),
            evidence_level=evidence,
            known_agents=target_info.get("known_agents", []),
            notes=notes,
        )

    def _compute_accessibility(self, target_info: dict) -> float:
        """Compute target accessibility score based on biological properties."""
        score = 0.5  # baseline

        # Cell surface = accessible
        if target_info.get("location") == "cell_surface":
            score += 0.3

        # Low shedding = better accessibility
        shedding = target_info.get("shedding_risk", 0.0)
        score -= shedding * 0.3

        # Internalization helps for therapeutic (payload delivery)
        if target_info.get("internalization"):
            score += 0.1

        return min(1.0, max(0.0, score))
