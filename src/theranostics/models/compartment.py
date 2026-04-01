"""Body compartment models for PBPK simulation."""

from __future__ import annotations

from typing import Optional

import numpy as np
from pydantic import BaseModel, Field


class Compartment(BaseModel):
    name: str
    volume_l: float = Field(description="Compartment volume in liters")
    blood_flow_fraction: float = Field(
        description="Fraction of cardiac output going to this compartment"
    )
    vascular_fraction: float = Field(
        default=0.05, description="Vascular volume fraction within compartment"
    )
    interstitial_fraction: float = Field(
        default=0.15, description="Interstitial volume fraction"
    )
    partition_coefficient: float = Field(
        default=0.5, description="Tissue-to-plasma partition coefficient (Kp)"
    )

    # Target-related
    target_density_nm: float = Field(
        default=0.0, description="Target antigen density in nM equivalent"
    )
    internalization_rate_per_h: float = Field(
        default=0.0, description="Receptor-mediated internalization rate"
    )
    degradation_rate_per_h: float = Field(
        default=0.1, description="Intracellular degradation rate"
    )

    # Elimination
    elimination_rate_per_h: float = Field(
        default=0.0, description="Local elimination rate (e.g., renal, hepatic)"
    )

    # Agent-specific modifiers
    extravasation_rate_per_h: float = Field(
        default=0.01, description="Rate of agent leaving vasculature"
    )
    lymphatic_drainage_rate_per_h: float = Field(
        default=0.001, description="Lymphatic return rate"
    )

    # Flags
    is_tumor: bool = False
    is_elimination_organ: bool = False


class BodyModel(BaseModel):
    """Complete body model with all compartments."""

    compartments: list[Compartment]
    cardiac_output_l_per_h: float = Field(default=390.0)
    plasma_volume_l: float = Field(default=3.0)

    def get_compartment(self, name: str) -> Optional[Compartment]:
        for c in self.compartments:
            if c.name == name:
                return c
        return None

    @property
    def compartment_names(self) -> list[str]:
        return [c.name for c in self.compartments]

    @property
    def n_compartments(self) -> int:
        return len(self.compartments)

    def blood_flow_l_per_h(self, compartment: Compartment) -> float:
        return compartment.blood_flow_fraction * self.cardiac_output_l_per_h

    def scale_to_patient(self, weight_kg: float, renal_factor: float = 1.0,
                         hepatic_factor: float = 1.0) -> "BodyModel":
        """Scale body model parameters to individual patient."""
        scale = weight_kg / 73.0
        scaled_compartments = []

        for c in self.compartments:
            new_c = c.model_copy()
            new_c.volume_l = c.volume_l * scale

            if c.name == "kidneys":
                new_c.elimination_rate_per_h = c.elimination_rate_per_h * renal_factor
            elif c.name == "liver":
                new_c.elimination_rate_per_h = c.elimination_rate_per_h * hepatic_factor

            scaled_compartments.append(new_c)

        return BodyModel(
            compartments=scaled_compartments,
            cardiac_output_l_per_h=self.cardiac_output_l_per_h * (scale ** 0.75),
            plasma_volume_l=self.plasma_volume_l * scale,
        )


def build_default_body_model(
    target_name: str = "HER2",
    tumor_volume_ml: float = 50.0,
    tumor_target_density: float = 100.0,
) -> BodyModel:
    """Build the default 12-compartment adult body model.

    Target densities are set based on known expression patterns.
    """
    # Normal tissue target expression (nM equivalent)
    normal_expression = _get_normal_expression(target_name)

    compartments = [
        Compartment(
            name="plasma",
            volume_l=3.0,
            blood_flow_fraction=0.0,
            vascular_fraction=1.0,
            interstitial_fraction=0.0,
            partition_coefficient=1.0,
            target_density_nm=0.0,
        ),
        Compartment(
            name="lungs",
            volume_l=0.5,
            blood_flow_fraction=1.0,  # All CO passes through lungs
            vascular_fraction=0.30,
            interstitial_fraction=0.15,
            partition_coefficient=0.4,
            target_density_nm=normal_expression.get("lungs", 0.0),
            extravasation_rate_per_h=0.02,
        ),
        Compartment(
            name="liver",
            volume_l=1.8,
            blood_flow_fraction=0.25,
            vascular_fraction=0.15,
            interstitial_fraction=0.15,
            partition_coefficient=0.5,
            target_density_nm=normal_expression.get("liver", 0.0),
            elimination_rate_per_h=0.01,
            is_elimination_organ=True,
            extravasation_rate_per_h=0.05,  # Fenestrated endothelium
        ),
        Compartment(
            name="kidneys",
            volume_l=0.3,
            blood_flow_fraction=0.19,
            vascular_fraction=0.15,
            interstitial_fraction=0.15,
            partition_coefficient=0.5,
            target_density_nm=normal_expression.get("kidneys", 0.0),
            elimination_rate_per_h=0.0,  # Set dynamically based on agent size
            is_elimination_organ=True,
            extravasation_rate_per_h=0.04,  # Fenestrated
        ),
        Compartment(
            name="spleen",
            volume_l=0.15,
            blood_flow_fraction=0.03,
            vascular_fraction=0.20,
            interstitial_fraction=0.15,
            partition_coefficient=0.5,
            target_density_nm=normal_expression.get("spleen", 0.0),
            extravasation_rate_per_h=0.06,  # Open sinusoids
        ),
        Compartment(
            name="heart",
            volume_l=0.3,
            blood_flow_fraction=0.04,
            vascular_fraction=0.10,
            interstitial_fraction=0.15,
            partition_coefficient=0.5,
            target_density_nm=normal_expression.get("heart", 0.0),
            extravasation_rate_per_h=0.01,
        ),
        Compartment(
            name="muscle",
            volume_l=28.0,
            blood_flow_fraction=0.17,
            vascular_fraction=0.03,
            interstitial_fraction=0.12,
            partition_coefficient=0.3,
            target_density_nm=normal_expression.get("muscle", 0.0),
            extravasation_rate_per_h=0.005,
        ),
        Compartment(
            name="bone_marrow",
            volume_l=1.5,
            blood_flow_fraction=0.05,
            vascular_fraction=0.10,
            interstitial_fraction=0.20,
            partition_coefficient=0.4,
            target_density_nm=normal_expression.get("bone_marrow", 0.0),
            extravasation_rate_per_h=0.03,  # Sinusoidal
        ),
        Compartment(
            name="skin",
            volume_l=3.0,
            blood_flow_fraction=0.05,
            vascular_fraction=0.03,
            interstitial_fraction=0.30,
            partition_coefficient=0.3,
            target_density_nm=normal_expression.get("skin", 0.0),
            extravasation_rate_per_h=0.008,
        ),
        Compartment(
            name="gut",
            volume_l=1.2,
            blood_flow_fraction=0.15,
            vascular_fraction=0.05,
            interstitial_fraction=0.15,
            partition_coefficient=0.5,
            target_density_nm=normal_expression.get("gut", 0.0),
            extravasation_rate_per_h=0.03,
        ),
        Compartment(
            name="brain",
            volume_l=1.4,
            blood_flow_fraction=0.12,
            vascular_fraction=0.04,
            interstitial_fraction=0.15,
            partition_coefficient=0.05,  # BBB limits distribution
            target_density_nm=0.0,  # BBB prevents access
            extravasation_rate_per_h=0.0001,  # BBB
        ),
        Compartment(
            name="rest_of_body",
            volume_l=10.0,
            blood_flow_fraction=0.0,  # Computed as remainder
            vascular_fraction=0.04,
            interstitial_fraction=0.15,
            partition_coefficient=0.4,
            target_density_nm=normal_expression.get("rest", 0.0),
            extravasation_rate_per_h=0.01,
        ),
        Compartment(
            name="tumor",
            volume_l=tumor_volume_ml / 1000.0,
            blood_flow_fraction=0.02,
            vascular_fraction=0.08,
            interstitial_fraction=0.35,
            partition_coefficient=0.6,
            target_density_nm=tumor_target_density,
            internalization_rate_per_h=0.05,
            degradation_rate_per_h=0.1,
            is_tumor=True,
            extravasation_rate_per_h=0.02,  # Enhanced permeability (EPR-like)
        ),
    ]

    # Ensure rest_of_body gets the remaining blood flow
    used_flow = sum(c.blood_flow_fraction for c in compartments if c.name != "rest_of_body")
    # Lungs gets 100% (series circulation), so actual parallel distribution is from arterial
    # Subtract lungs from calculation - all other organs share the arterial output
    parallel_flow = sum(
        c.blood_flow_fraction for c in compartments
        if c.name not in ("rest_of_body", "lungs", "plasma")
    )
    rest_flow = max(0.0, 1.0 - parallel_flow)
    for c in compartments:
        if c.name == "rest_of_body":
            c.blood_flow_fraction = rest_flow

    return BodyModel(compartments=compartments)


def _get_normal_expression(target_name: str) -> dict[str, float]:
    """Get normal tissue expression levels for a given target.

    Values are approximate nM equivalents of surface receptor density.
    Sources: Human Protein Atlas, published literature.
    """
    expression_db: dict[str, dict[str, float]] = {
        "HER2": {
            "lungs": 1.0,
            "liver": 5.0,
            "kidneys": 2.0,
            "spleen": 1.0,
            "heart": 3.0,
            "muscle": 0.5,
            "bone_marrow": 1.0,
            "skin": 2.0,
            "gut": 5.0,
            "rest": 1.0,
        },
        "PSMA": {
            "lungs": 0.5,
            "liver": 1.0,
            "kidneys": 50.0,  # High PSMA in proximal tubule
            "spleen": 2.0,
            "heart": 0.5,
            "muscle": 0.2,
            "bone_marrow": 1.0,
            "skin": 0.5,
            "gut": 5.0,
            "rest": 0.5,
        },
        "SSTR2": {
            "lungs": 1.0,
            "liver": 2.0,
            "kidneys": 5.0,
            "spleen": 15.0,  # High SSTR2 in spleen
            "heart": 0.5,
            "muscle": 0.5,
            "bone_marrow": 1.0,
            "skin": 0.5,
            "gut": 3.0,
            "rest": 0.5,
        },
        "CD20": {
            "lungs": 1.0,
            "liver": 2.0,
            "kidneys": 0.5,
            "spleen": 30.0,  # B-cell rich
            "heart": 0.2,
            "muscle": 0.2,
            "bone_marrow": 15.0,  # B-cell precursors
            "skin": 0.5,
            "gut": 2.0,
            "rest": 0.5,
        },
    }
    return expression_db.get(target_name, {k: 1.0 for k in [
        "lungs", "liver", "kidneys", "spleen", "heart",
        "muscle", "bone_marrow", "skin", "gut", "rest"
    ]})
