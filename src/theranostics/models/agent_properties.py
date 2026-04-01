"""Agent (therapeutic/diagnostic molecule) property models."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    IGG = "IgG"
    FAB = "Fab"
    NANOBODY = "nanobody"
    SMALL_MOLECULE = "small_molecule"
    PEPTIDE = "peptide"
    MINIBODY = "minibody"


class IsotopeType(str, Enum):
    DIAGNOSTIC = "diagnostic"
    THERAPEUTIC = "therapeutic"
    THERANOSTIC_PAIR = "theranostic_pair"


class IsotopeProperties(BaseModel):
    name: str
    symbol: str
    half_life_hours: float
    isotope_type: IsotopeType
    energy_kev: float = Field(description="Principal emission energy in keV")
    emission_type: str = Field(description="beta_minus, beta_plus, alpha, gamma, etc.")
    positron_fraction: float = Field(default=0.0, description="For PET isotopes")

    @property
    def decay_constant(self) -> float:
        """Decay constant λ = ln(2) / t½ in h⁻¹."""
        return 0.693147 / self.half_life_hours


# Pre-built isotope library
ISOTOPE_LIBRARY: dict[str, IsotopeProperties] = {
    "Zr-89": IsotopeProperties(
        name="Zirconium-89",
        symbol="89Zr",
        half_life_hours=78.4,
        isotope_type=IsotopeType.DIAGNOSTIC,
        energy_kev=909,
        emission_type="beta_plus",
        positron_fraction=0.23,
    ),
    "Ga-68": IsotopeProperties(
        name="Gallium-68",
        symbol="68Ga",
        half_life_hours=1.13,
        isotope_type=IsotopeType.DIAGNOSTIC,
        energy_kev=1899,
        emission_type="beta_plus",
        positron_fraction=0.89,
    ),
    "F-18": IsotopeProperties(
        name="Fluorine-18",
        symbol="18F",
        half_life_hours=1.83,
        isotope_type=IsotopeType.DIAGNOSTIC,
        energy_kev=634,
        emission_type="beta_plus",
        positron_fraction=0.97,
    ),
    "Lu-177": IsotopeProperties(
        name="Lutetium-177",
        symbol="177Lu",
        half_life_hours=159.5,
        isotope_type=IsotopeType.THERAPEUTIC,
        energy_kev=497,
        emission_type="beta_minus",
        positron_fraction=0.0,
    ),
    "Ac-225": IsotopeProperties(
        name="Actinium-225",
        symbol="225Ac",
        half_life_hours=240.0,
        isotope_type=IsotopeType.THERAPEUTIC,
        energy_kev=5830,
        emission_type="alpha",
        positron_fraction=0.0,
    ),
    "I-131": IsotopeProperties(
        name="Iodine-131",
        symbol="131I",
        half_life_hours=192.5,
        isotope_type=IsotopeType.THERAPEUTIC,
        energy_kev=606,
        emission_type="beta_minus",
        positron_fraction=0.0,
    ),
    "Y-90": IsotopeProperties(
        name="Yttrium-90",
        symbol="90Y",
        half_life_hours=64.1,
        isotope_type=IsotopeType.THERAPEUTIC,
        energy_kev=2280,
        emission_type="beta_minus",
        positron_fraction=0.0,
    ),
    "Cu-64": IsotopeProperties(
        name="Copper-64",
        symbol="64Cu",
        half_life_hours=12.7,
        isotope_type=IsotopeType.DIAGNOSTIC,
        energy_kev=656,
        emission_type="beta_plus",
        positron_fraction=0.18,
    ),
}


class AgentProperties(BaseModel):
    name: str = Field(description="Agent name (e.g., Trastuzumab)")
    agent_type: AgentType
    target_name: str = Field(description="Target antigen (e.g., HER2)")

    # Physical properties
    molecular_weight_kda: float = Field(description="Molecular weight in kDa")
    hydrodynamic_radius_nm: float = Field(description="Hydrodynamic radius in nm")

    # Binding properties
    kd_nm: float = Field(description="Dissociation constant in nM")
    kon_per_m_per_s: float = Field(default=1e5, description="On-rate in M⁻¹s⁻¹")
    koff_per_s: float = Field(default=1e-4, description="Off-rate in s⁻¹")

    # PK properties
    plasma_half_life_hours: float = Field(description="Plasma half-life in hours")
    volume_of_distribution_l: Optional[float] = Field(
        default=None, description="Vd in L, if known"
    )

    # Clearance
    renal_filtration_fraction: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Fraction cleared by renal filtration (size-dependent)",
    )
    hepatic_clearance_fraction: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Fraction cleared by hepatic metabolism",
    )

    # Tumor penetration
    has_fc_region: bool = Field(default=True, description="Has Fc region (FcRn recycling)")
    vascular_permeability_cm_per_s: float = Field(
        default=3e-8, description="Vascular permeability in cm/s"
    )
    interstitial_diffusivity_cm2_per_s: float = Field(
        default=1e-7, description="Interstitial diffusion coefficient"
    )

    # Isotope
    isotope: Optional[str] = Field(default=None, description="Isotope key from ISOTOPE_LIBRARY")

    @property
    def isotope_properties(self) -> Optional[IsotopeProperties]:
        if self.isotope:
            return ISOTOPE_LIBRARY.get(self.isotope)
        return None

    @property
    def kon_per_nm_per_h(self) -> float:
        """Convert on-rate to nM⁻¹ h⁻¹ for simulation."""
        return self.kon_per_m_per_s * 1e-9 * 3600

    @property
    def koff_per_h(self) -> float:
        """Convert off-rate to h⁻¹ for simulation."""
        return self.koff_per_s * 3600

    @property
    def elimination_rate_per_h(self) -> float:
        """Overall elimination rate constant from half-life."""
        return 0.693147 / self.plasma_half_life_hours


# Pre-built agent library
AGENT_LIBRARY: dict[str, AgentProperties] = {
    "trastuzumab": AgentProperties(
        name="Trastuzumab",
        agent_type=AgentType.IGG,
        target_name="HER2",
        molecular_weight_kda=148.0,
        hydrodynamic_radius_nm=5.3,
        kd_nm=0.1,
        kon_per_m_per_s=1.8e5,
        koff_per_s=1.8e-5,
        plasma_half_life_hours=480.0,
        volume_of_distribution_l=3.0,
        renal_filtration_fraction=0.0,
        hepatic_clearance_fraction=0.3,
        has_fc_region=True,
        vascular_permeability_cm_per_s=3e-8,
        interstitial_diffusivity_cm2_per_s=1e-7,
    ),
    "trastuzumab-89Zr": AgentProperties(
        name="Trastuzumab-89Zr",
        agent_type=AgentType.IGG,
        target_name="HER2",
        molecular_weight_kda=150.0,
        hydrodynamic_radius_nm=5.4,
        kd_nm=0.5,
        kon_per_m_per_s=1.5e5,
        koff_per_s=7.5e-5,
        plasma_half_life_hours=450.0,
        volume_of_distribution_l=3.2,
        renal_filtration_fraction=0.0,
        hepatic_clearance_fraction=0.3,
        has_fc_region=True,
        vascular_permeability_cm_per_s=3e-8,
        interstitial_diffusivity_cm2_per_s=1e-7,
        isotope="Zr-89",
    ),
    "pertuzumab": AgentProperties(
        name="Pertuzumab",
        agent_type=AgentType.IGG,
        target_name="HER2",
        molecular_weight_kda=148.0,
        hydrodynamic_radius_nm=5.3,
        kd_nm=1.0,
        kon_per_m_per_s=1.0e5,
        koff_per_s=1.0e-4,
        plasma_half_life_hours=420.0,
        volume_of_distribution_l=3.1,
        renal_filtration_fraction=0.0,
        hepatic_clearance_fraction=0.3,
        has_fc_region=True,
        vascular_permeability_cm_per_s=3e-8,
        interstitial_diffusivity_cm2_per_s=1e-7,
    ),
    "her2-nanobody": AgentProperties(
        name="Anti-HER2 Nanobody",
        agent_type=AgentType.NANOBODY,
        target_name="HER2",
        molecular_weight_kda=15.0,
        hydrodynamic_radius_nm=2.0,
        kd_nm=5.0,
        kon_per_m_per_s=5e5,
        koff_per_s=2.5e-3,
        plasma_half_life_hours=3.0,
        volume_of_distribution_l=10.0,
        renal_filtration_fraction=0.85,
        hepatic_clearance_fraction=0.1,
        has_fc_region=False,
        vascular_permeability_cm_per_s=5e-7,
        interstitial_diffusivity_cm2_per_s=5e-7,
    ),
    "her2-nanobody-68Ga": AgentProperties(
        name="Anti-HER2 Nanobody-68Ga",
        agent_type=AgentType.NANOBODY,
        target_name="HER2",
        molecular_weight_kda=16.0,
        hydrodynamic_radius_nm=2.1,
        kd_nm=6.0,
        kon_per_m_per_s=4.5e5,
        koff_per_s=2.7e-3,
        plasma_half_life_hours=2.5,
        volume_of_distribution_l=10.5,
        renal_filtration_fraction=0.80,
        hepatic_clearance_fraction=0.1,
        has_fc_region=False,
        vascular_permeability_cm_per_s=5e-7,
        interstitial_diffusivity_cm2_per_s=5e-7,
        isotope="Ga-68",
    ),
    "her2-fab": AgentProperties(
        name="Anti-HER2 Fab Fragment",
        agent_type=AgentType.FAB,
        target_name="HER2",
        molecular_weight_kda=50.0,
        hydrodynamic_radius_nm=3.5,
        kd_nm=1.0,
        kon_per_m_per_s=2e5,
        koff_per_s=2e-4,
        plasma_half_life_hours=15.0,
        volume_of_distribution_l=7.0,
        renal_filtration_fraction=0.4,
        hepatic_clearance_fraction=0.2,
        has_fc_region=False,
        vascular_permeability_cm_per_s=1e-7,
        interstitial_diffusivity_cm2_per_s=3e-7,
    ),
    "PSMA-617": AgentProperties(
        name="PSMA-617",
        agent_type=AgentType.SMALL_MOLECULE,
        target_name="PSMA",
        molecular_weight_kda=1.0,
        hydrodynamic_radius_nm=0.6,
        kd_nm=2.3,
        kon_per_m_per_s=1e6,
        koff_per_s=2.3e-3,
        plasma_half_life_hours=4.0,
        volume_of_distribution_l=50.0,
        renal_filtration_fraction=0.6,
        hepatic_clearance_fraction=0.2,
        has_fc_region=False,
        vascular_permeability_cm_per_s=1e-5,
        interstitial_diffusivity_cm2_per_s=1e-5,
        isotope="Lu-177",
    ),
    "PSMA-617-68Ga": AgentProperties(
        name="PSMA-617-68Ga",
        agent_type=AgentType.SMALL_MOLECULE,
        target_name="PSMA",
        molecular_weight_kda=1.1,
        hydrodynamic_radius_nm=0.6,
        kd_nm=3.0,
        kon_per_m_per_s=1e6,
        koff_per_s=3.0e-3,
        plasma_half_life_hours=3.5,
        volume_of_distribution_l=50.0,
        renal_filtration_fraction=0.6,
        hepatic_clearance_fraction=0.2,
        has_fc_region=False,
        vascular_permeability_cm_per_s=1e-5,
        interstitial_diffusivity_cm2_per_s=1e-5,
        isotope="Ga-68",
    ),
    "DOTATATE": AgentProperties(
        name="DOTATATE",
        agent_type=AgentType.PEPTIDE,
        target_name="SSTR2",
        molecular_weight_kda=1.4,
        hydrodynamic_radius_nm=0.7,
        kd_nm=1.5,
        kon_per_m_per_s=8e5,
        koff_per_s=1.2e-3,
        plasma_half_life_hours=2.0,
        volume_of_distribution_l=15.0,
        renal_filtration_fraction=0.65,
        hepatic_clearance_fraction=0.15,
        has_fc_region=False,
        vascular_permeability_cm_per_s=1e-5,
        interstitial_diffusivity_cm2_per_s=1e-5,
        isotope="Lu-177",
    ),
    "DOTATATE-68Ga": AgentProperties(
        name="DOTATATE-68Ga",
        agent_type=AgentType.PEPTIDE,
        target_name="SSTR2",
        molecular_weight_kda=1.5,
        hydrodynamic_radius_nm=0.7,
        kd_nm=2.0,
        kon_per_m_per_s=7e5,
        koff_per_s=1.4e-3,
        plasma_half_life_hours=1.8,
        volume_of_distribution_l=15.0,
        renal_filtration_fraction=0.65,
        hepatic_clearance_fraction=0.15,
        has_fc_region=False,
        vascular_permeability_cm_per_s=1e-5,
        interstitial_diffusivity_cm2_per_s=1e-5,
        isotope="Ga-68",
    ),
    "rituximab": AgentProperties(
        name="Rituximab",
        agent_type=AgentType.IGG,
        target_name="CD20",
        molecular_weight_kda=145.0,
        hydrodynamic_radius_nm=5.2,
        kd_nm=8.0,
        kon_per_m_per_s=5e4,
        koff_per_s=4e-4,
        plasma_half_life_hours=450.0,
        volume_of_distribution_l=3.1,
        renal_filtration_fraction=0.0,
        hepatic_clearance_fraction=0.3,
        has_fc_region=True,
        vascular_permeability_cm_per_s=3e-8,
        interstitial_diffusivity_cm2_per_s=1e-7,
    ),
}
