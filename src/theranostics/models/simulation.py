"""Simulation request/result models."""

from __future__ import annotations

from typing import Literal, Optional

import numpy as np
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    """User-facing simulation request."""

    # Target
    target_name: str = Field(default="HER2", description="Target antigen name")
    tumor_type: str = Field(default="breast", description="Tumor type")

    # Agent
    agent_key: str = Field(default="trastuzumab-89Zr", description="Key from agent library")

    # Isotope override
    isotope_key: Optional[str] = Field(default=None, description="Override isotope")

    # Dose
    dose_mbq: float = Field(default=37.0, ge=1, le=10000, description="Injected dose in MBq")
    dose_mg: Optional[float] = Field(
        default=None, ge=0.01, le=1000, description="Mass dose in mg (for cold antibodies)"
    )

    # Patient
    patient_age: int = Field(default=60, ge=18, le=100)
    patient_sex: str = Field(default="male")
    patient_weight_kg: float = Field(default=73.0, ge=30, le=200)
    patient_height_cm: float = Field(default=175.0, ge=120, le=220)
    patient_egfr: float = Field(default=90.0, ge=5, le=150)
    patient_liver_function: float = Field(default=1.0, ge=0.1, le=1.0)

    # Tumor
    tumor_volume_ml: float = Field(default=50.0, ge=0.001, le=5000)
    tumor_target_density: float = Field(
        default=100.0, ge=0, le=1000,
        description="Tumor target density (nM equivalent)",
    )
    n_metastases: int = Field(default=3, ge=0, le=100)

    # Simulation parameters
    duration_hours: float = Field(default=168.0, ge=1, le=720)
    n_monte_carlo: int = Field(default=200, ge=1, le=2000)
    time_step_hours: float = Field(default=0.1, ge=0.01, le=1.0)


class OrganTimeSeries(BaseModel):
    """Time series data for a single organ."""

    organ_name: str
    times_hours: list[float]
    concentrations_free: list[float] = Field(description="Free agent concentration (nM)")
    concentrations_bound: list[float] = Field(description="Bound agent concentration (nM)")
    concentrations_total: list[float] = Field(description="Total concentration (nM)")
    uptake_percent_id_per_g: list[float] = Field(description="%ID/g over time")
    is_tumor: bool = False

    model_config = {"arbitrary_types_allowed": True}


class DosimetryResult(BaseModel):
    """Radiation dosimetry output for therapeutic isotopes."""

    organ_doses_gy_per_gbq: dict[str, float] = Field(
        description="Absorbed dose per organ in Gy/GBq"
    )
    tumor_dose_gy_per_gbq: float = Field(description="Tumor absorbed dose in Gy/GBq")
    dose_limiting_organ: str
    dose_limiting_value: float
    tumor_to_kidney_ratio: Optional[float] = None
    therapeutic_index: Optional[float] = Field(
        default=None,
        description="Tumor dose / dose-limiting organ dose",
    )


class ConfidenceAssessment(BaseModel):
    level: Literal["high", "moderate", "low", "very_low"] = "moderate"
    factors: list[str] = Field(default_factory=list)
    data_support: Literal[
        "clinical_validated",
        "preclinical_supported",
        "literature_informed",
        "simulation_only",
        "extrapolated",
    ] = "literature_informed"
    recommendation: str = ""


class PredictionResult(BaseModel):
    value: float
    ci_low: float
    ci_high: float
    unit: str


class SimulationResult(BaseModel):
    """Complete simulation output."""

    # Request echo
    request_summary: dict = Field(default_factory=dict)

    # Time points
    time_points_hours: list[float]

    # Per-organ time series
    organ_results: list[OrganTimeSeries]

    # Key metrics
    tumor_uptake_percent_id_per_g: PredictionResult
    tumor_to_background_ratio: PredictionResult
    optimal_imaging_time_hours: PredictionResult
    plasma_half_life_hours: float

    # Biodistribution at optimal imaging time
    biodistribution_at_optimal: dict[str, float] = Field(
        description="Organ uptake (%ID/g) at optimal imaging time"
    )

    # Dosimetry (if therapeutic isotope)
    dosimetry: Optional[DosimetryResult] = None

    # Confidence
    confidence: ConfidenceAssessment = Field(default_factory=ConfidenceAssessment)

    # Metadata
    simulation_duration_seconds: float = 0.0
    n_monte_carlo_samples: int = 0
    model_version: str = "0.1.0"

    model_config = {"arbitrary_types_allowed": True}
