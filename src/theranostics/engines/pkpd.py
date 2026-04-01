"""PK/PD Engine — pharmacokinetics/pharmacodynamics and dosimetry calculations."""

from __future__ import annotations

from typing import Optional

import numpy as np

from theranostics.models.agent_properties import AgentProperties, IsotopeType, ISOTOPE_LIBRARY
from theranostics.models.simulation import DosimetryResult, OrganTimeSeries


# S-values (Gy/GBq·h) for common isotopes — simplified from OLINDA/EXM
# These represent the absorbed dose rate per unit cumulated activity
# Source: Stabin MG, Sparks RB, Crowe E. OLINDA/EXM. J Nucl Med. 2005
_S_VALUES: dict[str, dict[str, float]] = {
    "Lu-177": {
        "kidneys": 1.10,
        "liver": 0.14,
        "spleen": 0.78,
        "bone_marrow": 0.11,
        "lungs": 0.11,
        "heart": 0.15,
        "tumor": 0.60,  # depends on tumor size; this is for ~10 cm³
        "muscle": 0.01,
        "gut": 0.06,
        "brain": 0.01,
        "skin": 0.01,
        "rest_of_body": 0.02,
        "plasma": 0.05,
    },
    "Y-90": {
        "kidneys": 2.20,
        "liver": 0.28,
        "spleen": 1.55,
        "bone_marrow": 0.22,
        "lungs": 0.22,
        "heart": 0.30,
        "tumor": 1.20,
        "muscle": 0.02,
        "gut": 0.12,
        "brain": 0.02,
        "skin": 0.02,
        "rest_of_body": 0.04,
        "plasma": 0.10,
    },
    "Ac-225": {
        "kidneys": 8.50,
        "liver": 1.10,
        "spleen": 6.00,
        "bone_marrow": 0.85,
        "lungs": 0.85,
        "heart": 1.20,
        "tumor": 4.80,
        "muscle": 0.08,
        "gut": 0.48,
        "brain": 0.05,
        "skin": 0.05,
        "rest_of_body": 0.15,
        "plasma": 0.40,
    },
    "I-131": {
        "kidneys": 0.85,
        "liver": 0.11,
        "spleen": 0.60,
        "bone_marrow": 0.09,
        "lungs": 0.09,
        "heart": 0.12,
        "tumor": 0.46,
        "muscle": 0.008,
        "gut": 0.05,
        "brain": 0.008,
        "skin": 0.008,
        "rest_of_body": 0.02,
        "plasma": 0.04,
    },
}

# Organ dose tolerances (Gy) — simplified from clinical guidelines
_ORGAN_TOLERANCES: dict[str, float] = {
    "kidneys": 23.0,   # EBRT equivalent; for PRRT typically 23 Gy BED
    "bone_marrow": 2.0,  # Very sensitive
    "liver": 30.0,
    "lungs": 20.0,
    "spleen": 20.0,
    "heart": 25.0,
    "gut": 45.0,
    "brain": 50.0,
    "salivary_glands": 25.0,
}


class PKPDEngine:
    """Pharmacokinetics/dynamics and dosimetry calculations."""

    def __init__(self) -> None:
        self.s_values = _S_VALUES
        self.organ_tolerances = _ORGAN_TOLERANCES

    def compute_dosimetry(
        self,
        organ_results: list[OrganTimeSeries],
        agent: AgentProperties,
        dose_gbq: float,
    ) -> Optional[DosimetryResult]:
        """Compute internal dosimetry for therapeutic radionuclides.

        Uses MIRD formalism:
        D(organ) = Ã(organ) × S(organ ← organ)

        Where Ã = cumulated activity = ∫ A(t) dt
        """
        isotope = agent.isotope_properties
        if isotope is None:
            return None

        # Only compute dosimetry for therapeutic isotopes
        if isotope.isotope_type == IsotopeType.DIAGNOSTIC:
            return None

        isotope_key = agent.isotope
        if isotope_key not in self.s_values:
            return None

        s_vals = self.s_values[isotope_key]

        # Compute residence times (time-integrated uptake) per organ
        organ_doses: dict[str, float] = {}

        for organ_ts in organ_results:
            organ_name = organ_ts.organ_name
            s_value = s_vals.get(organ_name, 0.01)

            # Compute cumulated activity (trapezoidal integration)
            # Uptake (%ID/g) × time → residence time proxy
            times = np.array(organ_ts.times_hours)
            uptake = np.array(organ_ts.uptake_percent_id_per_g)

            # Time-integrated activity (Ã) in arbitrary units
            if len(times) > 1:
                residence_time = np.trapezoid(uptake, times)
            else:
                residence_time = 0.0

            # Absorbed dose = Ã × S-value × injected activity
            # Units: Gy = (h × %ID/g) × (Gy/GBq·h) × GBq / 100
            absorbed_dose = residence_time * s_value * dose_gbq / 100.0
            organ_doses[organ_name] = round(absorbed_dose, 4)

        # Normalize to Gy/GBq
        organ_doses_per_gbq = {
            k: round(v / dose_gbq, 4) if dose_gbq > 0 else 0.0
            for k, v in organ_doses.items()
        }

        # Tumor dose
        tumor_dose = organ_doses_per_gbq.get("tumor", 0.0)

        # Find dose-limiting organ
        critical_organs = {
            k: v for k, v in organ_doses_per_gbq.items()
            if k not in ("tumor", "plasma") and v > 0
        }

        if critical_organs:
            # Dose-limiting = highest fraction of tolerance
            fractions = {
                organ: dose / self.organ_tolerances.get(organ, 50.0)
                for organ, dose in critical_organs.items()
            }
            dose_limiting_organ = max(fractions, key=fractions.get)
            dose_limiting_value = critical_organs[dose_limiting_organ]
        else:
            dose_limiting_organ = "kidneys"
            dose_limiting_value = 0.0

        # Therapeutic index
        therapeutic_index = (
            tumor_dose / dose_limiting_value if dose_limiting_value > 0 else float("inf")
        )

        # Tumor-to-kidney ratio
        kidney_dose = organ_doses_per_gbq.get("kidneys", 0.0)
        tumor_to_kidney = tumor_dose / kidney_dose if kidney_dose > 0 else float("inf")

        return DosimetryResult(
            organ_doses_gy_per_gbq=organ_doses_per_gbq,
            tumor_dose_gy_per_gbq=tumor_dose,
            dose_limiting_organ=dose_limiting_organ,
            dose_limiting_value=dose_limiting_value,
            tumor_to_kidney_ratio=round(tumor_to_kidney, 2) if tumor_to_kidney != float("inf") else None,
            therapeutic_index=round(therapeutic_index, 2) if therapeutic_index != float("inf") else None,
        )

    def compute_suv(
        self,
        concentration_nm: float,
        organ_volume_l: float,
        injected_dose_mbq: float,
        body_weight_kg: float,
    ) -> float:
        """Compute Standardized Uptake Value (SUV).

        SUV = (activity_concentration in organ) / (injected_dose / body_weight)

        This is a simplified calculation using concentration as a proxy for activity.
        """
        if injected_dose_mbq <= 0 or body_weight_kg <= 0:
            return 0.0

        # Concentration proxy → activity concentration
        # Normalize: organ_activity_fraction / organ_weight
        organ_weight_kg = organ_volume_l  # density ≈ 1 kg/L
        if organ_weight_kg <= 0:
            return 0.0

        # SUV ≈ (C_organ / C_average) where C_average = total / body_weight
        # Simplified: use concentration relative to uniform distribution
        suv = concentration_nm * organ_volume_l / (body_weight_kg * 1000)  # rough normalization
        return max(0.0, suv)

    def find_optimal_imaging_time(
        self,
        organ_results: list[OrganTimeSeries],
    ) -> float:
        """Find the time point with maximum tumor-to-background ratio."""
        tumor_ts = None
        muscle_ts = None

        for ts in organ_results:
            if ts.is_tumor:
                tumor_ts = ts
            elif ts.organ_name == "muscle":
                muscle_ts = ts

        if tumor_ts is None or muscle_ts is None:
            return 24.0  # default

        tumor = np.array(tumor_ts.concentrations_total)
        muscle = np.array(muscle_ts.concentrations_total)
        times = np.array(tumor_ts.times_hours)

        with np.errstate(divide="ignore", invalid="ignore"):
            tbr = np.where(muscle > 1e-12, tumor / muscle, 0.0)

        if len(tbr) == 0 or np.max(tbr) == 0:
            return 24.0

        optimal_idx = np.argmax(tbr)
        return float(times[optimal_idx])

    def compare_scenarios(
        self,
        results: list[tuple[str, DosimetryResult]],
    ) -> list[dict]:
        """Compare multiple dosimetry scenarios and rank them."""
        rankings = []

        for name, dosimetry in results:
            if dosimetry is None:
                continue

            # Score: higher therapeutic index = better
            ti = dosimetry.therapeutic_index or 0.0
            kidney_safety = 1.0 - min(
                1.0,
                dosimetry.organ_doses_gy_per_gbq.get("kidneys", 0) / 23.0,
            )
            marrow_safety = 1.0 - min(
                1.0,
                dosimetry.organ_doses_gy_per_gbq.get("bone_marrow", 0) / 2.0,
            )

            combined_score = 0.5 * min(ti / 10.0, 1.0) + 0.3 * kidney_safety + 0.2 * marrow_safety

            rankings.append({
                "scenario": name,
                "therapeutic_index": ti,
                "kidney_safety": round(kidney_safety, 3),
                "marrow_safety": round(marrow_safety, 3),
                "combined_score": round(combined_score, 3),
                "dose_limiting_organ": dosimetry.dose_limiting_organ,
            })

        rankings.sort(key=lambda x: x["combined_score"], reverse=True)
        return rankings
