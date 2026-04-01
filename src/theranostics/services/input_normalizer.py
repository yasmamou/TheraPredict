"""Input Normalizer — Module 1 of TheraPredict V1 pipeline.

Takes user input (potentially incomplete) and converts it into a fully
normalized, validated internal request object.  All defaults are logged,
never silent.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field

from theranostics.services.logging_service import PipelineLogger, ModuleTimer, hash_dict

MODULE = "input_normalizer"


# ---------------------------------------------------------------------------
# Normalized internal request model
# ---------------------------------------------------------------------------

class AgentInput(BaseModel):
    name: str = ""
    agent_class: str = "small_molecule"  # small_molecule, peptide, nanobody, Fab, IgG
    size_kDa: float = 1.0
    kd_nM: Optional[float] = None
    kon_per_M_per_s: Optional[float] = None
    koff_per_s: Optional[float] = None
    internalization: bool = True
    isotope: Optional[str] = None
    has_fc_region: bool = False
    vascular_permeability_cm_per_s: Optional[float] = None
    interstitial_diffusivity_cm2_per_s: Optional[float] = None
    plasma_half_life_hours: Optional[float] = None
    renal_filtration_fraction: Optional[float] = None
    hepatic_clearance_fraction: Optional[float] = None


class DoseInput(BaseModel):
    activity_GBq: Optional[float] = None
    activity_MBq: Optional[float] = None
    mass_mg: Optional[float] = None


class TumorInput(BaseModel):
    tumor_type: str = "other"
    volume_ml: float = 50.0
    target_expression_override: Optional[float] = None
    n_metastases: int = 3
    stage: str = "IV"


class PatientInput(BaseModel):
    weight_kg: float = 70.0
    sex: str = "male"
    age: int = 65
    height_cm: float = 175.0
    renal_function: str = "normal"  # normal, mild_impairment, moderate_impairment, severe_impairment
    hepatic_function: str = "normal"  # normal, mild_impairment, moderate_impairment


class NormalizedRequest(BaseModel):
    """Fully normalized internal request — output of Input Normalizer."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target: str = "PSMA"
    indication: str = ""
    agent: AgentInput = Field(default_factory=AgentInput)
    dose: DoseInput = Field(default_factory=DoseInput)
    tumor: TumorInput = Field(default_factory=TumorInput)
    patient: PatientInput = Field(default_factory=PatientInput)

    # Simulation parameters
    duration_hours: float = 168.0
    n_monte_carlo: int = 100
    time_step_hours: float = 0.1

    # Metadata
    defaults_applied: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    input_hash: str = ""


# ---------------------------------------------------------------------------
# Defaults tables
# ---------------------------------------------------------------------------

VALID_TARGETS = {"PSMA", "SSTR2", "HER2", "FAP", "CD20"}
VALID_AGENT_CLASSES = {"small_molecule", "peptide", "nanobody", "Fab", "IgG"}
VALID_ISOTOPES = {"Ga-68", "F-18", "Lu-177", "Y-90", "Ac-225", "Zr-89", "I-131"}

# Default agent class properties
_CLASS_DEFAULTS: dict[str, dict[str, Any]] = {
    "small_molecule": {
        "size_kDa": 0.8,
        "kd_nM": 5.0,
        "kon_per_M_per_s": 1e6,
        "plasma_half_life_hours": 4.0,
        "renal_filtration_fraction": 0.6,
        "hepatic_clearance_fraction": 0.2,
        "has_fc_region": False,
        "vascular_permeability_cm_per_s": 1e-5,
        "interstitial_diffusivity_cm2_per_s": 1e-5,
    },
    "peptide": {
        "size_kDa": 1.5,
        "kd_nM": 2.0,
        "kon_per_M_per_s": 8e5,
        "plasma_half_life_hours": 2.0,
        "renal_filtration_fraction": 0.65,
        "hepatic_clearance_fraction": 0.15,
        "has_fc_region": False,
        "vascular_permeability_cm_per_s": 1e-5,
        "interstitial_diffusivity_cm2_per_s": 1e-5,
    },
    "nanobody": {
        "size_kDa": 15.0,
        "kd_nM": 5.0,
        "kon_per_M_per_s": 5e5,
        "plasma_half_life_hours": 3.0,
        "renal_filtration_fraction": 0.80,
        "hepatic_clearance_fraction": 0.1,
        "has_fc_region": False,
        "vascular_permeability_cm_per_s": 5e-7,
        "interstitial_diffusivity_cm2_per_s": 5e-7,
    },
    "Fab": {
        "size_kDa": 50.0,
        "kd_nM": 1.0,
        "kon_per_M_per_s": 2e5,
        "plasma_half_life_hours": 15.0,
        "renal_filtration_fraction": 0.4,
        "hepatic_clearance_fraction": 0.2,
        "has_fc_region": False,
        "vascular_permeability_cm_per_s": 1e-7,
        "interstitial_diffusivity_cm2_per_s": 3e-7,
    },
    "IgG": {
        "size_kDa": 150.0,
        "kd_nM": 1.0,
        "kon_per_M_per_s": 1.5e5,
        "plasma_half_life_hours": 450.0,
        "renal_filtration_fraction": 0.0,
        "hepatic_clearance_fraction": 0.3,
        "has_fc_region": True,
        "vascular_permeability_cm_per_s": 3e-8,
        "interstitial_diffusivity_cm2_per_s": 1e-7,
    },
}

# Target-indication mapping
_TARGET_INDICATIONS: dict[str, str] = {
    "PSMA": "prostate_cancer",
    "SSTR2": "neuroendocrine_tumor",
    "HER2": "breast_cancer",
    "FAP": "solid_tumor",
    "CD20": "lymphoma",
}

# Renal function to eGFR
_RENAL_EGFR: dict[str, float] = {
    "normal": 90.0,
    "mild_impairment": 70.0,
    "moderate_impairment": 45.0,
    "severe_impairment": 20.0,
}

# Hepatic function to score
_HEPATIC_SCORE: dict[str, float] = {
    "normal": 1.0,
    "mild_impairment": 0.7,
    "moderate_impairment": 0.4,
}


# ---------------------------------------------------------------------------
# Input Normalizer
# ---------------------------------------------------------------------------

class InputNormalizer:
    """Module 1: Normalize user input into a clean internal request."""

    def normalize(
        self,
        raw_input: dict[str, Any],
        logger: PipelineLogger,
    ) -> NormalizedRequest:
        """Normalize raw user input.

        Args:
            raw_input: Dict from user (can be incomplete).
            logger: Pipeline logger instance.

        Returns:
            Fully populated NormalizedRequest.
        """
        with ModuleTimer(logger, MODULE, "normalization"):
            return self._do_normalize(raw_input, logger)

    def _do_normalize(
        self, raw: dict[str, Any], logger: PipelineLogger
    ) -> NormalizedRequest:
        defaults_applied: list[str] = []
        warnings: list[str] = []

        # Log raw input
        input_h = hash_dict(raw)
        logger.audit(MODULE, "raw_input_received", data={"input_hash": input_h, "raw": raw})

        # -- Request ID -------------------------------------------------------
        request_id = raw.get("request_id") or str(uuid.uuid4())

        # -- Target -----------------------------------------------------------
        target = str(raw.get("target", "")).upper()
        if target not in VALID_TARGETS:
            if target:
                warnings.append(f"Unknown target '{target}', defaulting to PSMA")
            else:
                warnings.append("No target specified, defaulting to PSMA")
            target = "PSMA"
            defaults_applied.append("target=PSMA")

        # -- Indication -------------------------------------------------------
        indication = raw.get("indication", "")
        if not indication:
            indication = _TARGET_INDICATIONS.get(target, "unknown")
            defaults_applied.append(f"indication={indication}")

        # -- Agent ------------------------------------------------------------
        agent_raw = raw.get("agent", {})
        if isinstance(agent_raw, str):
            agent_raw = {"name": agent_raw}

        agent_class = agent_raw.get("class", agent_raw.get("agent_class", ""))
        if agent_class not in VALID_AGENT_CLASSES:
            if agent_class:
                warnings.append(f"Unknown agent class '{agent_class}', defaulting to small_molecule")
            agent_class = "small_molecule"
            defaults_applied.append("agent.class=small_molecule")

        class_defaults = _CLASS_DEFAULTS[agent_class]
        agent = AgentInput(
            name=agent_raw.get("name", f"custom_{agent_class}"),
            agent_class=agent_class,
            size_kDa=self._get_with_default(agent_raw, "size_kDa", class_defaults["size_kDa"], defaults_applied, "agent.size_kDa"),
            kd_nM=agent_raw.get("kd_nM") or agent_raw.get("kd_nm"),
            kon_per_M_per_s=agent_raw.get("kon_per_M_per_s") or agent_raw.get("kon"),
            koff_per_s=agent_raw.get("koff_per_s") or agent_raw.get("koff"),
            internalization=agent_raw.get("internalization", True),
            isotope=self._normalize_isotope(agent_raw.get("isotope"), warnings),
            has_fc_region=agent_raw.get("has_fc_region", class_defaults["has_fc_region"]),
            vascular_permeability_cm_per_s=agent_raw.get("vascular_permeability_cm_per_s"),
            interstitial_diffusivity_cm2_per_s=agent_raw.get("interstitial_diffusivity_cm2_per_s"),
            plasma_half_life_hours=agent_raw.get("plasma_half_life_hours"),
            renal_filtration_fraction=agent_raw.get("renal_filtration_fraction"),
            hepatic_clearance_fraction=agent_raw.get("hepatic_clearance_fraction"),
        )

        # Fill missing agent params from class defaults
        for field_name, default_val in class_defaults.items():
            if field_name in ("size_kDa", "has_fc_region"):
                continue  # Already handled
            current = getattr(agent, field_name, None)
            if current is None:
                setattr(agent, field_name, default_val)
                defaults_applied.append(f"agent.{field_name}={default_val}")

        # Derive koff from Kd and kon if needed
        if agent.kd_nM is not None and agent.kon_per_M_per_s is not None and agent.koff_per_s is None:
            agent.koff_per_s = agent.kd_nM * 1e-9 * agent.kon_per_M_per_s
            defaults_applied.append(f"agent.koff_per_s={agent.koff_per_s:.2e} (derived from Kd * kon)")

        if agent.kd_nM is None:
            agent.kd_nM = class_defaults["kd_nM"]
            defaults_applied.append(f"agent.kd_nM={agent.kd_nM}")
        if agent.koff_per_s is None and agent.kd_nM is not None and agent.kon_per_M_per_s is not None:
            agent.koff_per_s = agent.kd_nM * 1e-9 * agent.kon_per_M_per_s
            defaults_applied.append(f"agent.koff_per_s={agent.koff_per_s:.2e} (derived)")

        # -- Dose -------------------------------------------------------------
        dose_raw = raw.get("dose", {})
        dose = DoseInput(
            activity_GBq=dose_raw.get("activity_GBq"),
            activity_MBq=dose_raw.get("activity_MBq"),
            mass_mg=dose_raw.get("mass_mg"),
        )
        # Convert GBq to MBq for internal use
        if dose.activity_GBq is not None and dose.activity_MBq is None:
            dose.activity_MBq = dose.activity_GBq * 1000
        if dose.activity_MBq is None and dose.mass_mg is None:
            # Default dose depends on isotope type
            if agent.isotope in ("Lu-177", "Y-90", "Ac-225", "I-131"):
                dose.activity_GBq = 7.4
                dose.activity_MBq = 7400.0
                defaults_applied.append("dose.activity_GBq=7.4 (therapeutic default)")
            else:
                dose.activity_MBq = 185.0
                dose.activity_GBq = 0.185
                defaults_applied.append("dose.activity_MBq=185 (diagnostic default)")

        # -- Tumor ------------------------------------------------------------
        tumor_raw = raw.get("tumor", {})
        tumor = TumorInput(
            tumor_type=tumor_raw.get("type", tumor_raw.get("tumor_type", "other")),
            volume_ml=self._get_with_default(tumor_raw, "volume_ml", 50.0, defaults_applied, "tumor.volume_ml"),
            target_expression_override=tumor_raw.get("target_expression_override"),
            n_metastases=tumor_raw.get("n_metastases", 3),
            stage=tumor_raw.get("stage", "IV"),
        )

        # -- Patient ----------------------------------------------------------
        patient_raw = raw.get("patient", {})
        patient = PatientInput(
            weight_kg=self._get_with_default(patient_raw, "weight_kg", 70.0, defaults_applied, "patient.weight_kg"),
            sex=patient_raw.get("sex", "male"),
            age=self._get_with_default(patient_raw, "age", 65, defaults_applied, "patient.age"),
            height_cm=self._get_with_default(patient_raw, "height_cm", 175.0, defaults_applied, "patient.height_cm"),
            renal_function=patient_raw.get("renal_function", "normal"),
            hepatic_function=patient_raw.get("hepatic_function", "normal"),
        )

        # -- Simulation params ------------------------------------------------
        duration_hours = raw.get("duration_hours", 168.0)
        n_monte_carlo = raw.get("n_monte_carlo", 100)
        time_step_hours = raw.get("time_step_hours", 0.1)

        # -- Build result -----------------------------------------------------
        result = NormalizedRequest(
            request_id=request_id,
            target=target,
            indication=indication,
            agent=agent,
            dose=dose,
            tumor=tumor,
            patient=patient,
            duration_hours=duration_hours,
            n_monte_carlo=n_monte_carlo,
            time_step_hours=time_step_hours,
            defaults_applied=defaults_applied,
            warnings=warnings,
            input_hash=input_h,
        )

        # Log output
        output_h = hash_dict(result.model_dump())
        logger.audit(MODULE, "normalization_complete", data={
            "output_hash": output_h,
            "defaults_applied": defaults_applied,
            "warnings": warnings,
            "missing_fields_count": len(defaults_applied),
        })

        if warnings:
            logger.warning(MODULE, "normalization_warnings", warnings=warnings)

        return result

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _get_with_default(
        source: dict, key: str, default: Any,
        defaults_list: list[str], field_path: str,
    ) -> Any:
        val = source.get(key)
        if val is None:
            defaults_list.append(f"{field_path}={default}")
            return default
        return val

    @staticmethod
    def _normalize_isotope(isotope: Optional[str], warnings: list[str]) -> Optional[str]:
        if isotope is None:
            return None
        # Normalize common variants
        normalized = isotope.strip()
        aliases = {
            "68Ga": "Ga-68", "Ga68": "Ga-68",
            "18F": "F-18", "F18": "F-18",
            "177Lu": "Lu-177", "Lu177": "Lu-177",
            "90Y": "Y-90", "Y90": "Y-90",
            "225Ac": "Ac-225", "Ac225": "Ac-225",
            "89Zr": "Zr-89", "Zr89": "Zr-89",
            "131I": "I-131", "I131": "I-131",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized not in VALID_ISOTOPES:
            warnings.append(f"Unknown isotope '{isotope}', will proceed without isotope")
            return None
        return normalized

    # -- Convenience: convert to legacy SimulationRequest ---------------------

    def to_egfr(self, renal_function: str) -> float:
        return _RENAL_EGFR.get(renal_function, 90.0)

    def to_hepatic_score(self, hepatic_function: str) -> float:
        return _HEPATIC_SCORE.get(hepatic_function, 1.0)
