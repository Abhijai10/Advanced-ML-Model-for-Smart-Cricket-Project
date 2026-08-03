"""Configuration paths and constants for Phase 12 offline inference."""

from __future__ import annotations

from pathlib import Path


ML_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ML_ROOT.parent
DATASET_DIR = ML_ROOT / "data" / "final_temporal"
PHASE8_BEST_MODEL_DIR = ML_ROOT / "artifacts" / "phase8" / "best_model"
PHASE10_TEMPLATE_PATH = ML_ROOT / "artifacts" / "phase10" / "ideal_template_schema.json"
PHASE12_DIR = ML_ROOT / "artifacts" / "phase12"

SAMPLE_OUTPUT_PATH = PHASE12_DIR / "sample_output.json"
INFERENCE_HEALTH_PATH = PHASE12_DIR / "inference_health.json"
INFERENCE_REPORT_PATH = PHASE12_DIR / "inference_report.md"

PHASE12_VERSION = "phase_12_offline_inference_v1"
EXPECTED_SEQUENCE_LENGTH = 60
EXPECTED_FEATURE_DIM = 32
EXPECTED_NUM_CLASSES = 4


DEFAULT_SAMPLE_INDEX = 1
