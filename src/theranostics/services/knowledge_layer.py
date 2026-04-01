"""Knowledge Layer — Module 2 of TheraPredict V1 pipeline.

Interrogates external sources (Open Targets, HPA, UniProt) and internal
curated tables to retrieve biological facts about the target.

This module provides *facts*, not predictions.
Correct: "PSMA expression: high in tumor, moderate in kidney"
Incorrect: "the molecule will go to kidney"
"""

from __future__ import annotations

from typing import Any, Optional

from theranostics.integrations.open_targets import OpenTargetsClient
from theranostics.integrations.human_protein_atlas import HumanProteinAtlasClient
from theranostics.integrations.uniprot import UniProtClient
from theranostics.services.input_normalizer import NormalizedRequest
from theranostics.services.logging_service import PipelineLogger, ModuleTimer

MODULE = "knowledge_layer"


# ---------------------------------------------------------------------------
# Curated fallback data (used when APIs are unavailable)
# ---------------------------------------------------------------------------

_CURATED_EXPRESSION: dict[str, dict[str, float]] = {
    "PSMA": {
        "kidney": 0.62, "salivary_glands": 0.58, "liver": 0.10,
        "gut": 0.20, "spleen": 0.08, "muscle": 0.03,
        "lungs": 0.05, "brain": 0.02, "bone_marrow": 0.05,
        "heart": 0.03, "skin": 0.03, "prostate": 0.15,
    },
    "SSTR2": {
        "spleen": 0.55, "kidney": 0.25, "adrenals": 0.40,
        "gut": 0.20, "liver": 0.12, "lungs": 0.08,
        "brain": 0.15, "pancreas": 0.30, "muscle": 0.03,
        "bone_marrow": 0.05, "heart": 0.03, "skin": 0.03,
        "salivary_glands": 0.05,
    },
    "HER2": {
        "heart": 0.35, "gut": 0.30, "liver": 0.20,
        "kidney": 0.15, "skin": 0.15, "lungs": 0.10,
        "muscle": 0.05, "bone_marrow": 0.08, "spleen": 0.08,
        "brain": 0.05, "salivary_glands": 0.05, "breast": 0.20,
    },
    "FAP": {
        "joints": 0.35, "uterus": 0.30, "skin": 0.10,
        "liver": 0.05, "kidney": 0.05, "lungs": 0.05,
        "gut": 0.05, "muscle": 0.03, "bone_marrow": 0.03,
        "spleen": 0.03, "heart": 0.03, "brain": 0.01,
        "salivary_glands": 0.02,
    },
    "CD20": {
        "spleen": 0.80, "bone_marrow": 0.60, "lymph_nodes": 0.75,
        "liver": 0.10, "kidney": 0.03, "lungs": 0.08,
        "gut": 0.10, "muscle": 0.01, "heart": 0.01,
        "brain": 0.01, "skin": 0.03, "salivary_glands": 0.02,
    },
}

_CURATED_TARGET_PROFILES: dict[str, dict[str, Any]] = {
    "PSMA": {
        "full_name": "Prostate-Specific Membrane Antigen",
        "gene": "FOLH1",
        "location": "cell_surface",
        "internalization": True,
        "internalization_rate": "high",
        "shedding": False,
        "shedding_risk": 0.05,
        "accessibility": "high",
        "evidence_levels": {
            "prostate_cancer": "A",
            "breast_cancer": "C",
            "colorectal_cancer": "C",
        },
        "known_agents": ["PSMA-617", "PSMA-11", "PSMA-I&T", "J591"],
        "tumor_expression_typical": 0.90,
    },
    "SSTR2": {
        "full_name": "Somatostatin Receptor Type 2",
        "gene": "SSTR2",
        "location": "cell_surface",
        "internalization": True,
        "internalization_rate": "high",
        "shedding": False,
        "shedding_risk": 0.0,
        "accessibility": "high",
        "evidence_levels": {
            "neuroendocrine_tumor": "A",
            "meningioma": "B",
        },
        "known_agents": ["DOTATATE", "DOTATOC", "DOTANOC"],
        "tumor_expression_typical": 0.85,
    },
    "HER2": {
        "full_name": "Human Epidermal Growth Factor Receptor 2",
        "gene": "ERBB2",
        "location": "cell_surface",
        "internalization": True,
        "internalization_rate": "moderate",
        "shedding": True,
        "shedding_risk": 0.20,
        "accessibility": "high",
        "evidence_levels": {
            "breast_cancer": "A",
            "gastric_cancer": "A",
            "colorectal_cancer": "B",
        },
        "known_agents": ["Trastuzumab", "Pertuzumab", "T-DM1", "T-DXd"],
        "tumor_expression_typical": 0.85,
    },
    "FAP": {
        "full_name": "Fibroblast Activation Protein",
        "gene": "FAP",
        "location": "cell_surface",
        "internalization": True,
        "internalization_rate": "moderate",
        "shedding": False,
        "shedding_risk": 0.10,
        "accessibility": "moderate",
        "evidence_levels": {
            "breast_cancer": "B",
            "colorectal_cancer": "B",
            "pancreatic_cancer": "B",
        },
        "known_agents": ["FAPI-04", "FAPI-46", "FAP-2286"],
        "tumor_expression_typical": 0.70,
    },
    "CD20": {
        "full_name": "B-Lymphocyte Antigen CD20",
        "gene": "MS4A1",
        "location": "cell_surface",
        "internalization": False,
        "internalization_rate": "very_low",
        "shedding": False,
        "shedding_risk": 0.0,
        "accessibility": "high",
        "evidence_levels": {
            "lymphoma": "A",
            "cll": "A",
        },
        "known_agents": ["Rituximab", "Obinutuzumab", "Ibritumomab"],
        "tumor_expression_typical": 0.90,
    },
}

_INTERNALIZATION_SCORES: dict[str, float] = {
    "very_low": 0.05,
    "low": 0.15,
    "moderate": 0.45,
    "high": 0.80,
    "very_high": 0.95,
}

_ACCESSIBILITY_SCORES: dict[str, float] = {
    "very_low": 0.10,
    "low": 0.30,
    "moderate": 0.55,
    "high": 0.80,
    "very_high": 0.95,
}


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

class TargetKnowledge:
    """Structured output from the Knowledge Layer."""

    def __init__(self) -> None:
        self.target: str = ""
        self.tumor_expression_score: float = 0.5
        self.normal_tissue_expression: dict[str, float] = {}
        self.accessibility_score: float = 0.5
        self.internalization_score: float = 0.5
        self.shedding_risk: float = 0.0
        self.evidence_level: str = "D"
        self.known_agents: list[str] = []

        # Source tracking
        self.sources_used: list[str] = []
        self.api_data: dict[str, Any] = {}
        self.conflicts: list[str] = []
        self.confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_profile": {
                "target": self.target,
                "tumor_expression_score": self.tumor_expression_score,
                "normal_tissue_expression": self.normal_tissue_expression,
                "accessibility_score": self.accessibility_score,
                "internalization_score": self.internalization_score,
                "shedding_risk": self.shedding_risk,
                "evidence_level": self.evidence_level,
            },
            "known_agents": self.known_agents,
            "sources_used": self.sources_used,
            "conflicts": self.conflicts,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Knowledge Layer service
# ---------------------------------------------------------------------------

class KnowledgeLayer:
    """Module 2: Retrieve biological knowledge about the target."""

    def __init__(self, use_apis: bool = True) -> None:
        self.use_apis = use_apis
        if use_apis:
            self.ot_client = OpenTargetsClient()
            self.hpa_client = HumanProteinAtlasClient()
            self.uniprot_client = UniProtClient()

    def query(
        self,
        request: NormalizedRequest,
        logger: PipelineLogger,
    ) -> TargetKnowledge:
        """Query all sources for target knowledge.

        Returns biological facts, NOT predictions about biodistribution.
        """
        with ModuleTimer(logger, MODULE, "knowledge_query"):
            return self._do_query(request, logger)

    def _do_query(
        self,
        request: NormalizedRequest,
        logger: PipelineLogger,
    ) -> TargetKnowledge:
        target = request.target
        indication = request.indication
        result = TargetKnowledge()
        result.target = target

        # 1. Start with curated fallback
        curated = _CURATED_TARGET_PROFILES.get(target, {})
        curated_expr = _CURATED_EXPRESSION.get(target, {})

        result.normal_tissue_expression = dict(curated_expr)
        result.known_agents = curated.get("known_agents", [])
        result.internalization_score = _INTERNALIZATION_SCORES.get(
            curated.get("internalization_rate", "moderate"), 0.5
        )
        result.accessibility_score = _ACCESSIBILITY_SCORES.get(
            curated.get("accessibility", "moderate"), 0.5
        )
        result.shedding_risk = curated.get("shedding_risk", 0.0)
        result.tumor_expression_score = curated.get("tumor_expression_typical", 0.5)
        result.evidence_level = curated.get("evidence_levels", {}).get(indication, "D")
        result.sources_used.append("curated_internal")
        result.confidence = 0.5

        logger.info(MODULE, "curated_data_loaded", data={
            "target": target,
            "tissues_with_expression": len(curated_expr),
            "evidence_level": result.evidence_level,
        })

        if not self.use_apis:
            logger.info(MODULE, "apis_disabled", data={"reason": "use_apis=False"})
            return result

        # 2. Query Open Targets for disease association
        ot_data = self.ot_client.get_target_disease_association(
            target, indication, logger
        )
        if ot_data and ot_data.get("overall_score", 0) > 0:
            ot_score = ot_data["overall_score"]
            result.api_data["open_targets"] = ot_data
            result.sources_used.append("open_targets")

            # Upgrade evidence level if OT has strong association
            if ot_score > 0.7 and result.evidence_level in ("C", "D"):
                old = result.evidence_level
                result.evidence_level = "B"
                logger.info(MODULE, "evidence_upgraded", data={
                    "from": old, "to": "B",
                    "reason": f"Open Targets score={ot_score:.2f}",
                })

            # Blend tumor expression with OT score
            result.tumor_expression_score = max(
                result.tumor_expression_score,
                ot_score * 0.9,  # OT association score as proxy
            )
            result.confidence += 0.15

        # 3. Query Open Targets for target info
        ot_target = self.ot_client.get_target_info(target, logger)
        if ot_target:
            result.api_data["open_targets_target"] = ot_target
            if "open_targets" not in result.sources_used:
                result.sources_used.append("open_targets")

        # 4. Query HPA for tissue expression
        hpa_data = self.hpa_client.get_tissue_expression(target, logger)
        if hpa_data:
            hpa_expr = hpa_data.get("expression_by_compartment", {})
            result.api_data["hpa"] = hpa_data
            result.sources_used.append("human_protein_atlas")
            result.confidence += 0.15

            # Merge HPA data with curated: prefer HPA when available,
            # but flag conflicts
            for tissue, hpa_score in hpa_expr.items():
                curated_score = result.normal_tissue_expression.get(tissue)
                if curated_score is not None:
                    diff = abs(hpa_score - curated_score)
                    if diff > 0.3:
                        result.conflicts.append(
                            f"{tissue}: curated={curated_score:.2f} vs HPA={hpa_score:.2f}"
                        )
                        logger.warning(MODULE, "expression_conflict", data={
                            "tissue": tissue,
                            "curated": curated_score,
                            "hpa": hpa_score,
                            "using": "average",
                        })
                        # Use average when conflict
                        result.normal_tissue_expression[tissue] = (hpa_score + curated_score) / 2
                    else:
                        # HPA takes precedence
                        result.normal_tissue_expression[tissue] = hpa_score
                else:
                    # New tissue from HPA
                    result.normal_tissue_expression[tissue] = hpa_score

        # 5. Query UniProt
        uniprot_data = self.uniprot_client.get_protein_info(target, logger)
        if uniprot_data:
            result.api_data["uniprot"] = uniprot_data
            result.sources_used.append("uniprot")

            # Validate cell-surface accessibility
            if uniprot_data.get("has_extracellular_domain"):
                result.accessibility_score = max(result.accessibility_score, 0.75)
            if not uniprot_data.get("has_transmembrane") and curated.get("location") == "cell_surface":
                result.conflicts.append(
                    "UniProt does not confirm transmembrane domain"
                )

        # Final confidence capping
        result.confidence = min(result.confidence, 1.0)

        # Log summary
        logger.audit(MODULE, "knowledge_query_complete", data={
            "target": target,
            "sources_used": result.sources_used,
            "conflicts": result.conflicts,
            "confidence": round(result.confidence, 2),
            "tissue_count": len(result.normal_tissue_expression),
            "evidence_level": result.evidence_level,
        }, confidence=round(result.confidence, 2))

        return result
