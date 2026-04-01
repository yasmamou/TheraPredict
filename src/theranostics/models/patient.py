"""Patient data models."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


class TumorType(str, Enum):
    BREAST = "breast"
    PROSTATE = "prostate"
    NEUROENDOCRINE = "neuroendocrine"
    LYMPHOMA = "lymphoma"
    COLORECTAL = "colorectal"
    LUNG = "lung"
    GASTRIC = "gastric"
    THYROID = "thyroid"
    MELANOMA = "melanoma"
    OTHER = "other"


class Stage(str, Enum):
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"


class Demographics(BaseModel):
    age: int = Field(default=60, ge=18, le=100, description="Patient age in years")
    sex: Sex = Field(default=Sex.MALE)
    weight_kg: float = Field(default=73.0, ge=30, le=200, description="Body weight in kg")
    height_cm: float = Field(default=175.0, ge=120, le=220, description="Height in cm")

    @property
    def bsa(self) -> float:
        """Body surface area (Du Bois formula) in m²."""
        return 0.007184 * (self.weight_kg ** 0.425) * (self.height_cm ** 0.725)

    @property
    def bmi(self) -> float:
        height_m = self.height_cm / 100
        return self.weight_kg / (height_m ** 2)


class TumorProfile(BaseModel):
    tumor_type: TumorType = Field(default=TumorType.BREAST)
    stage: Stage = Field(default=Stage.IV)
    tumor_volume_ml: float = Field(default=50.0, ge=0.001, le=5000)
    n_metastases: int = Field(default=3, ge=0, le=100)
    target_expression_level: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Target expression level [0,1]. None = use population estimate.",
    )


class OrganFunction(BaseModel):
    egfr_ml_per_min: float = Field(
        default=90.0, ge=5, le=150, description="Estimated GFR in mL/min"
    )
    liver_function_score: float = Field(
        default=1.0, ge=0.1, le=1.0, description="1.0 = normal, <1.0 = impaired"
    )
    cardiac_output_fraction: float = Field(
        default=1.0, ge=0.3, le=1.5, description="1.0 = normal cardiac output"
    )


class PatientProfile(BaseModel):
    demographics: Demographics = Field(default_factory=Demographics)
    tumor: TumorProfile = Field(default_factory=TumorProfile)
    organ_function: OrganFunction = Field(default_factory=OrganFunction)

    @property
    def weight_scaling_factor(self) -> float:
        """Scale body model parameters by weight relative to reference."""
        return self.demographics.weight_kg / 73.0

    @property
    def renal_scaling_factor(self) -> float:
        """Scale renal clearance by eGFR relative to reference (120 mL/min)."""
        return self.organ_function.egfr_ml_per_min / 120.0
