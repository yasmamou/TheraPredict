"""Global configuration and physical constants for TheraPredict V1."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
LOGS_DIR = PROJECT_ROOT / "logs"
CURATED_DIR = PROJECT_ROOT / "data" / "curated"

# Physical constants
LN2 = 0.693147  # ln(2)

# Simulation defaults
DEFAULT_MONTE_CARLO_SAMPLES = 100
DEFAULT_SIMULATION_DURATION_HOURS = 168  # 7 days
DEFAULT_TIME_STEP_HOURS = 0.1

# Reference human parameters (ICRP 89, adult male 73 kg)
REFERENCE_BODY_WEIGHT_KG = 73.0
REFERENCE_CARDIAC_OUTPUT_L_PER_H = 390.0  # ~6.5 L/min
REFERENCE_PLASMA_VOLUME_L = 3.0
REFERENCE_BLOOD_VOLUME_L = 5.3
REFERENCE_GFR_ML_PER_MIN = 120.0

# V1 Pipeline version
V1_VERSION = "1.0.0"
V1_MODEL_VERSION = "v1.0"

# V1 Targets
V1_TARGETS = {"PSMA", "SSTR2", "HER2", "FAP", "CD20"}

# V1 Agent classes
V1_AGENT_CLASSES = {"small_molecule", "peptide", "nanobody", "Fab", "IgG"}

# V1 Isotopes
V1_ISOTOPES = {"Ga-68", "F-18", "Lu-177", "Y-90", "Ac-225", "Zr-89", "I-131"}
