"""Agent Simulation Engine — model agent properties and in-vivo behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from theranostics.models.agent_properties import (
    AGENT_LIBRARY,
    AgentProperties,
    AgentType,
    ISOTOPE_LIBRARY,
)


@dataclass
class TumorPenetrationResult:
    penetration_depth_um: float
    uniformity_score: float  # [0, 1] — 1 = uniform
    binding_site_barrier_risk: bool
    thiele_modulus: float
    recommendation: str


@dataclass
class ClearanceProfile:
    total_clearance_ml_per_h: float
    renal_fraction: float
    hepatic_fraction: float
    target_mediated_fraction: float
    predicted_half_life_hours: float
    dominant_route: str


@dataclass
class AgentAssessment:
    agent: AgentProperties
    penetration: TumorPenetrationResult
    clearance: ClearanceProfile
    off_target_risk: dict[str, float]  # organ -> risk score [0,1]
    optimal_imaging_window_hours: Optional[tuple[float, float]]
    notes: list[str]


class AgentEngine:
    """Evaluate and characterize theranostic agents."""

    def __init__(self) -> None:
        self.agent_library = AGENT_LIBRARY
        self.isotope_library = ISOTOPE_LIBRARY

    def list_agents(self) -> list[str]:
        return list(self.agent_library.keys())

    def get_agent(self, agent_key: str) -> Optional[AgentProperties]:
        return self.agent_library.get(agent_key)

    def assess(
        self,
        agent: AgentProperties,
        tumor_antigen_density_nm: float = 100.0,
        tumor_vascular_density: float = 100.0,  # vessels/mm²
    ) -> AgentAssessment:
        """Full assessment of an agent's predicted in-vivo behavior."""
        penetration = self._predict_penetration(
            agent, tumor_antigen_density_nm, tumor_vascular_density
        )
        clearance = self._predict_clearance(agent)
        off_target = self._predict_off_target(agent)
        imaging_window = self._predict_imaging_window(agent)
        notes = self._generate_notes(agent, penetration, clearance)

        return AgentAssessment(
            agent=agent,
            penetration=penetration,
            clearance=clearance,
            off_target_risk=off_target,
            optimal_imaging_window_hours=imaging_window,
            notes=notes,
        )

    def _predict_penetration(
        self,
        agent: AgentProperties,
        antigen_density_nm: float,
        vascular_density: float,
    ) -> TumorPenetrationResult:
        """Predict tumor penetration using Thurber-Schmidt-Wittrup model.

        Key insight: higher affinity can REDUCE penetration (binding site barrier).
        """
        # Krogh cylinder radius from vascular density
        # R_krogh ≈ 1/sqrt(π * vessel_density)
        R_krogh_cm = 1.0 / np.sqrt(np.pi * vascular_density) * 0.1  # convert to cm

        # Diffusivity scales inversely with hydrodynamic radius
        D = agent.interstitial_diffusivity_cm2_per_s

        # Binding rate in appropriate units
        kon = agent.kon_per_m_per_s  # M⁻¹ s⁻¹
        Ag = antigen_density_nm * 1e-9  # convert nM to M

        # Thiele modulus: ratio of reaction to diffusion
        phi_squared = (R_krogh_cm ** 2) * kon * Ag / D
        phi = np.sqrt(phi_squared) if phi_squared > 0 else 0.0

        # Penetration depth
        if phi > 0.1:
            penetration_depth_cm = R_krogh_cm / phi
        else:
            penetration_depth_cm = R_krogh_cm  # Diffusion-limited, full penetration

        penetration_depth_um = penetration_depth_cm * 1e4

        # Uniformity score
        uniformity = 1.0 / (1.0 + phi)

        # Binding site barrier risk
        barrier_risk = phi > 3.0

        # Recommendation
        if barrier_risk:
            if agent.agent_type == AgentType.IGG:
                rec = (
                    "High binding site barrier risk. Consider using a smaller format "
                    "(Fab, nanobody) or pre-dosing with cold antibody to saturate "
                    "peripheral binding sites."
                )
            else:
                rec = (
                    "Moderate binding site barrier. Consider dose optimization to "
                    "improve penetration uniformity."
                )
        elif uniformity > 0.7:
            rec = "Good predicted tumor penetration with uniform distribution."
        else:
            rec = "Moderate tumor penetration. Distribution may be heterogeneous."

        return TumorPenetrationResult(
            penetration_depth_um=round(penetration_depth_um, 1),
            uniformity_score=round(uniformity, 3),
            binding_site_barrier_risk=barrier_risk,
            thiele_modulus=round(phi, 2),
            recommendation=rec,
        )

    def _predict_clearance(self, agent: AgentProperties) -> ClearanceProfile:
        """Predict clearance profile based on agent properties."""
        # Size-based renal filtration
        if agent.molecular_weight_kda < 60:
            # Below renal filtration cutoff
            sieving = 1.0 - (agent.molecular_weight_kda / 60.0) ** 0.5
            renal_fraction = max(0.0, sieving * agent.renal_filtration_fraction)
        else:
            renal_fraction = 0.0

        # Hepatic clearance
        hepatic_fraction = agent.hepatic_clearance_fraction

        # FcRn recycling effect (extends half-life for IgG)
        if agent.has_fc_region:
            hepatic_fraction *= 0.3  # FcRn rescues ~70% from degradation

        # Target-mediated disposition
        tmdd_fraction = 0.1 if agent.kd_nm < 10.0 else 0.05

        # Total
        total_fraction = renal_fraction + hepatic_fraction + tmdd_fraction
        if total_fraction > 0:
            renal_fraction /= total_fraction
            hepatic_fraction /= total_fraction
            tmdd_fraction /= total_fraction
        else:
            renal_fraction = 0.5
            hepatic_fraction = 0.5
            tmdd_fraction = 0.0

        # Dominant route
        fracs = {
            "renal": renal_fraction,
            "hepatic": hepatic_fraction,
            "target_mediated": tmdd_fraction,
        }
        dominant = max(fracs, key=fracs.get)

        # Total clearance from half-life
        vd = agent.volume_of_distribution_l or (agent.molecular_weight_kda * 0.05)
        total_cl = 0.693147 / agent.plasma_half_life_hours * vd

        return ClearanceProfile(
            total_clearance_ml_per_h=round(total_cl * 1000, 2),
            renal_fraction=round(renal_fraction, 3),
            hepatic_fraction=round(hepatic_fraction, 3),
            target_mediated_fraction=round(tmdd_fraction, 3),
            predicted_half_life_hours=round(agent.plasma_half_life_hours, 1),
            dominant_route=dominant,
        )

    def _predict_off_target(self, agent: AgentProperties) -> dict[str, float]:
        """Predict off-target accumulation risk per organ."""
        risks: dict[str, float] = {}

        # Liver: always some uptake (Kupffer cells, FcγR for IgG)
        risks["liver"] = 0.6 if agent.has_fc_region else 0.3

        # Kidneys: high for small molecules
        if agent.molecular_weight_kda < 60:
            risks["kidneys"] = 0.7 * agent.renal_filtration_fraction
        else:
            risks["kidneys"] = 0.1

        # Spleen: for IgG (FcγR)
        risks["spleen"] = 0.5 if agent.has_fc_region else 0.1

        # Bone marrow: for CD20-targeting agents
        if agent.target_name == "CD20":
            risks["bone_marrow"] = 0.7

        # Salivary glands: for PSMA agents
        if agent.target_name == "PSMA":
            risks["salivary_glands"] = 0.8

        return risks

    def _predict_imaging_window(
        self, agent: AgentProperties
    ) -> Optional[tuple[float, float]]:
        """Predict optimal imaging window (hours post-injection)."""
        isotope = agent.isotope_properties
        if isotope is None:
            return None

        # For PET imaging: need good tumor-to-background
        # Larger molecules need more time to clear background
        t_half_bio = agent.plasma_half_life_hours

        if agent.agent_type in (AgentType.IGG, AgentType.MINIBODY):
            # Large molecules: image at 3-7 days
            start = max(48, t_half_bio * 0.5)
            end = min(t_half_bio * 2, isotope.half_life_hours * 3)
        elif agent.agent_type == AgentType.FAB:
            # Medium: image at 4-24h
            start = max(4, t_half_bio * 0.5)
            end = min(t_half_bio * 3, isotope.half_life_hours * 3)
        else:
            # Small molecules/peptides: image at 0.5-3h
            start = max(0.5, t_half_bio * 0.3)
            end = min(t_half_bio * 3, isotope.half_life_hours * 2)

        return (round(start, 1), round(end, 1))

    def _generate_notes(
        self,
        agent: AgentProperties,
        penetration: TumorPenetrationResult,
        clearance: ClearanceProfile,
    ) -> list[str]:
        notes = []
        if penetration.binding_site_barrier_risk:
            notes.append(
                "WARNING: Binding site barrier detected. High affinity may limit "
                "tumor penetration depth."
            )
        if clearance.renal_fraction > 0.5:
            notes.append(
                "Predominantly renal clearance — monitor kidney function. "
                "Consider kidney-protective strategies (amino acid infusion)."
            )
        if agent.has_fc_region:
            notes.append(
                "FcRn-mediated recycling extends plasma half-life. "
                "Pre-dosing with cold antibody may be needed for imaging."
            )
        isotope = agent.isotope_properties
        if isotope and isotope.emission_type == "alpha":
            notes.append(
                "Alpha emitter: high LET radiation. Very effective per decay but "
                "redistribution of daughter isotopes is a concern."
            )
        return notes
