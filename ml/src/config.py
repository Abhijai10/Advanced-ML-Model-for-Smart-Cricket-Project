from pathlib import Path


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_VIDEO_PATH = PROJECT_ROOT / "ml" / "data" / "raw"
PROCESSED_PATH = PROJECT_ROOT / "ml" / "data" / "processed"
MODELS_PATH = PROJECT_ROOT / "ml" / "models"

# Default settings
DEFAULT_SEQUENCE_LENGTH = 60

# Labels
SHOT_LABELS = [
    "cover_drive",
    "straight_drive",
    "pull_shot",
    "defensive_shot",
]

QUALITY_LABELS = [
    "good",
    "average",
    "bad",
]
