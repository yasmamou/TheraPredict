"""Dosimetry Engine V1 — Module 5 of TheraPredict V1 pipeline.

Transforms time-activity curves into absorbed dose using MIRD/OLINDA formalism.
Fully logged with S-values provenance and all hypotheses explicit.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from theranostics.services.pbpk_engine_v1 import PBPKResult
from theranostics.services.input_normalizer import NormalizedRequest
from theranostics.services.logging_service import PipelineLogger, ModuleTimer

MODULE = "dosimetry_engine"

# ---------------------------------------------------------------------------
# S-values (Gy/GBq·h) — simplified from OLINDA/EXM
# Source: Stabin MG, Sparks RB, Crowe E. OLINDA/EXM. J Nucl Med. 2005
# ---------------------------------------------------------------------------

_S_VALUES: dict[str, dict[str, float]] = {
    "Lu-177": {
        "kidney": 1.10, "liver": 0.14, "spleen": 0.78,
        "bone_marrow": 0.11, "lungs": 0.11, "heart": 0.15,
        "tumor": 0.60, "muscle": 0.01, "gut": 0.06,
        "brain": 0.01, "skin": 0.01, "rest_of_body": 0.02,
        "plasma": 0.05, "salivary_glands": 0.90, "bone": 0.08,
    },
    "Y-90": {
        "kidney": 2.20, "liver": 0.28, "spleen": 1.55,
        "bone_marrow": 0.22, "lungs": 0.22, "heart": 0.30,
        "tumor": 1.20, "muscle": 0.02, "gut": 0.12,
        "brain": 0.02, "skin": 0.02, "rest_of_body": 0.04,
        "plasma": 0.10, "salivary_glands": 1.80, "bone": 0.15,
    },
    "Ac-225": {
        "kidney": 8.50, "liver": 1.10, "spleen": 6.00,
        "bone_marrow": 0.85, "lungs": 0.85, "heart": 1.20,
        "tumor": 4.80, "muscle": 0.08, "gut": 0.48,
        "brain": 0.05, "skin": 0.05, "rest_of_body": 0.15,
        "plasma": 0.40, "salivary_glands": 7.00, "bone": 0.60,
    },
    "I-131": {
        "kidney": 0.85, "liver": 0.11, "spleen": 0.60,
        "bone_marrow": 0.09, "lungs": 0.09, "heart": 0.12,
        "tumor": 0.46, "muscle": 0.008, "gut": 0.05,
        "brain": 0.008, "skin": 0.008, "rest_of_body": 0.02,
        "plasma": 0.04, "salivary_glands": 0.70, "bone": 0.06,
    },
}

# Organ dose tolerances (Gy)
_ORGAN_TOLERANCES: dict[str, float] = {
    "kidney": 23.0,
    "bone_marrow": 2.0,
    "liver": 30.0,
    "lungs": 20.0,
    "spleen": 20.0,
    "heart": 25.0,
    "gut": 45.0,
    "brain": 50.0,
    "salivary_glands": 25.0,
    "bone": 40.0,
}

THERAPEUTIC_ISOTOPES = {"Lu-177", "Y-90", "Ac-225", "I-131"}


# ---------------------------------------------------------------------------
# Dosimetry result
# ---------------------------------------------------------------------------

class DosimetryResultV1:
    """Output of the Dosimetry Engine."""

    def __init__(self) -> None:
        self.organ_doses_gy_per_gbq: dict[str, float] = {}
        self.organ_doses_total_gy: dict[str, float] = {}
        self.tumor_dose_gy_per_gbq: float = 0.0
        self.tumor_dose_total_gy: float = 0.0
        self.dose_limiting_organ: str = ""
        self.dose_limiting_dose_gy: float = 0.0
        self.therapeutic_index: float = 0.0
        self.tumor_to_kidney_ratio: Optional[float] = None
        self.injected_gbq: float = 0.0
        self.s_values_used: dict[str, float] = {}
        self.residence_times: dict[str, float] = {}
        self.hypotheses: list[str] = []
        self.warnings: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "organ_doses_gy_per_gbq": {k: round(v, 4) for k, v in self.organ_doses_gy_per_gbq.items()},
            "organ_doses_total_gy": {k: round(v, 3) for k, v in self.organ_doses_total_gy.items()},
            "tumor_dose_gy_per_gbq": round(self.tumor_dose_gy_per_gbq, 4),
            "tumor_dose_total_gy": round(self.tumor_dose_total_gy, 3),
            "dose_limiting_organ": self.dose_limiting_organ,
            "dose_limiting_dose_gy": round(self.dose_limiting_dose_gy, 3),
            "therapeutic_index": round(self.therapeutic_index, 2),
            "tumor_to_kidney_ratio": round(self.tumor_to_kidney_ratio, 2) if self.tumor_to_kidney_ratio else None,
            "injected_gbq": self.injected_gbq,
            "s_values_used": self.s_values_used,
            "residence_times": {k: round(v, 4) for k, v in self.residence_times.items()},
            "hypotheses": self.hypotheses,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Dosimetry Engine
# ---------------------------------------------------------------------------

class DosimetryEngineV1:
    """Module 5: Compute radiation dosimetry from PBPK results."""

    def compute(
        self,
        request: NormalizedRequest,
        pbpk_result: PBPKResult,
        logger: PipelineLogger,
    ) -> Optional[DosimetryResultV1]:
        """Compute dosimetry for therapeutic isotopes.

        Returns None for diagnostic isotopes.
        """
        isotope = request.agent.isotope
        if not isotope or isotope not in THERAPEUTIC_ISOTOPES:
            logger.info(MODULE, "skipped_diagnostic", data={
                "isotope": isotope,
                "reason": "Not a therapeutic isotope",
            })
            return None

        with ModuleTimer(logger, MODULE, "dosimetry_computation"):
            return self._do_compute(request, pbpk_result, isotope, logger)

    def _do_compute(
        self,
        req: NormalizedRequest,
        pbpk: PBPKResult,
        isotope: str,
        logger: PipelineLogger,
    ) -> DosimetryResultV1:
        result = DosimetryResultV1()
        dose_gbq = (req.dose.activity_GBq or 7.4)
        result.injected_gbq = dose_gbq

        s_vals = _S_VALUES.get(isotope, {})
        result.s_values_used = dict(s_vals)
        if not s_vals:
            logger.error(MODULE, "no_s_values", data={"isotope": isotope})
            result.warnings.append(f"No S-values available for {isotope}")
            return result

        result.hypotheses.append(
            f"S-values from OLINDA/EXM for {isotope}, standard adult geometry"
        )
        result.hypotheses.append(
            "Tumor S-value assumes ~10 cm³ sphere; actual geometry may differ"
        )

        t = np.array(pbpk.time_points)

        # Compute residence time (time-integrated concentration) per organ
        for organ_name, ts_data in pbpk.organ_timeseries.items():
            total = np.array(ts_data["total"])
            if len(t) > 1:
                residence_time = float(np.trapezoid(total, t))
            else:
                residence_time = 0.0

            result.residence_times[organ_name] = residence_time

            s_value = s_vals.get(organ_name, 0.01)

            # D = Ã × S × A_inj / 100
            dose_per_gbq = residence_time * s_value / 100.0
            total_dose = dose_per_gbq * dose_gbq

            result.organ_doses_gy_per_gbq[organ_name] = dose_per_gbq
            result.organ_doses_total_gy[organ_name] = total_dose

        # Tumor dose
        result.tumor_dose_gy_per_gbq = result.organ_doses_gy_per_gbq.get("tumor", 0)
        result.tumor_dose_total_gy = result.organ_doses_total_gy.get("tumor", 0)

        # Find dose-limiting organ
        critical = {
            k: v for k, v in result.organ_doses_total_gy.items()
            if k not in ("tumor", "plasma") and v > 0
        }
        if critical:
            fractions = {
                organ: dose / _ORGAN_TOLERANCES.get(organ, 50.0)
                for organ, dose in critical.items()
            }
            result.dose_limiting_organ = max(fractions, key=fractions.get)
            result.dose_limiting_dose_gy = critical[result.dose_limiting_organ]
        else:
            result.dose_limiting_organ = "kidney"
            result.dose_limiting_dose_gy = 0.0

        # Therapeutic index
        if result.dose_limiting_dose_gy > 0:
            result.therapeutic_index = result.tumor_dose_total_gy / result.dose_limiting_dose_gy
        else:
            result.therapeutic_index = float("inf")

        # Tumor-to-kidney ratio
        kidney_dose = result.organ_doses_total_gy.get("kidney", 0)
        if kidney_dose > 0:
            result.tumor_to_kidney_ratio = result.tumor_dose_total_gy / kidney_dose

        # Warnings
        for organ, tol in _ORGAN_TOLERANCES.items():
            total = result.organ_doses_total_gy.get(organ, 0)
            if total > tol:
                result.warnings.append(
                    f"{organ} dose ({total:.1f} Gy) EXCEEDS tolerance ({tol} Gy)"
                )
            elif total > tol * 0.8:
                result.warnings.append(
                    f"{organ} dose ({total:.1f} Gy) approaching tolerance ({tol} Gy)"
                )

        logger.audit(MODULE, "dosimetry_complete", data={
            "isotope": isotope,
            "injected_gbq": dose_gbq,
            "tumor_dose_gy": round(result.tumor_dose_total_gy, 2),
            "dose_limiting_organ": result.dose_limiting_organ,
            "dose_limiting_gy": round(result.dose_limiting_dose_gy, 2),
            "therapeutic_index": round(result.therapeutic_index, 2),
            "warnings": result.warnings,
        })

        return result
