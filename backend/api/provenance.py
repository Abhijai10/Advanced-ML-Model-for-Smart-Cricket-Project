"""Stable model and pipeline provenance for trusted analysis records."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ml.src.feedback.feedback_engine import PHASE11_VERSION
from ml.src.inference.inference_config import (
    DATASET_DIR,
    PHASE10_TEMPLATE_PATH,
    PHASE12_VERSION,
    PHASE8_BEST_MODEL_DIR,
)

from .services_version import PHASE13_VERSION


FEATURE_CONTRACT_VERSION = "smart_cricket_temporal_features_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_hash(path: Path) -> str | None:
    return _sha256(path) if path.is_file() else None


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@lru_cache(maxsize=1)
def build_provenance() -> dict[str, Any]:
    """Return deterministic artifact identifiers for analysis and feedback."""
    checkpoint = PHASE8_BEST_MODEL_DIR / "checkpoint.pt"
    feature_schema = DATASET_DIR / "temporal_feature_schema.json"
    label_mapping = DATASET_DIR / "temporal_label_mapping.json"
    scaler_mean = PHASE8_BEST_MODEL_DIR / "scaler" / "feature_mean.npy"
    scaler_std = PHASE8_BEST_MODEL_DIR / "scaler" / "feature_std.npy"
    schema_payload = _safe_json(feature_schema)
    checkpoint_hash = _safe_hash(checkpoint)
    feature_schema_hash = _safe_hash(feature_schema)
    label_mapping_hash = _safe_hash(label_mapping)
    scaler_mean_hash = _safe_hash(scaler_mean)
    scaler_std_hash = _safe_hash(scaler_std)
    scoring_template_hash = _safe_hash(PHASE10_TEMPLATE_PATH)
    model_identity = checkpoint_hash[:16] if checkpoint_hash else "missing-checkpoint"

    return {
        "model_version": f"phase8-best-{model_identity}",
        "checkpoint_sha256": checkpoint_hash,
        "feature_contract_version": schema_payload.get("feature_contract_version") or FEATURE_CONTRACT_VERSION,
        "feature_schema_sha256": feature_schema_hash,
        "scaler_mean_sha256": scaler_mean_hash,
        "scaler_std_sha256": scaler_std_hash,
        "label_mapping_sha256": label_mapping_hash,
        "dataset_run_id": schema_payload.get("created_at") or "unknown",
        "scoring_template_sha256": scoring_template_hash,
        "feedback_engine_version": PHASE11_VERSION,
        "pipeline_version": PHASE12_VERSION,
        "api_version": PHASE13_VERSION,
    }
