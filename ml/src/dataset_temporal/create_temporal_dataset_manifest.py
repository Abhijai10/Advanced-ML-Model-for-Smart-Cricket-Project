"""Phase 6.5 — create a manifest for the finalized temporal ML dataset.

Read-only except for writing ``temporal_dataset_manifest.json``. Validates the
temporal tensor contract, split shapes, labels, metadata, and feature health
before writing the manifest.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

DATASET_NAME = "smart_cricket_temporal_sequence_dataset"
DATASET_VERSION = "phase_6_temporal_v1"
DATASET_TYPE = "temporal_sequence_classification"

EXPECTED_FULL_SHAPE = [80, 60, 32]
EXPECTED_LABEL_SHAPE = [80]
EXPECTED_SPLIT_SHAPES = {
    "train": [56, 60, 32],
    "validation": [12, 60, 32],
    "test": [12, 60, 32],
}

_ML_ROOT = Path(__file__).resolve().parents[2]
FINAL_TEMPORAL_DIR = _ML_ROOT / "data" / "final_temporal"
MANIFEST_PATH = FINAL_TEMPORAL_DIR / "temporal_dataset_manifest.json"


def _file_type(path: Path) -> str:
    return {
        ".npy": "numpy_array",
        ".json": "json",
        ".csv": "csv",
        ".md": "markdown",
        ".pkl": "joblib_pickle",
    }.get(path.suffix.lower(), "unknown")


REQUIRED_ARTIFACTS: dict[str, str] = {
    "X_sequence.npy": "Full rank-3 temporal feature tensor.",
    "y_sequence.npy": "Encoded labels aligned row-for-row with X_sequence.npy.",
    "X_train_sequence.npy": "Training split temporal tensor.",
    "X_val_sequence.npy": "Validation split temporal tensor.",
    "X_test_sequence.npy": "Test split temporal tensor.",
    "y_train_sequence.npy": "Training split encoded labels.",
    "y_val_sequence.npy": "Validation split encoded labels.",
    "y_test_sequence.npy": "Test split encoded labels.",
    "temporal_feature_schema.json": "Temporal feature order, groups, and tensor contract.",
    "temporal_label_mapping.json": "Encoded label index to shot class mapping.",
    "temporal_label_encoder.pkl": "Fitted sklearn LabelEncoder for temporal shot labels.",
    "temporal_split_metadata.json": "Split strategy, sizes, and reproducibility metadata.",
    "temporal_feature_validation_report.md": "Human-readable temporal feature validation report.",
    "temporal_feature_statistics.csv": "Per-feature temporal statistics and health status.",
    "temporal_feature_health.json": "Machine-readable feature health summary.",
    "temporal_dataset_report.md": "Phase 6.4 temporal dataset integrity report.",
    "temporal_dataset_index.csv": "Full temporal dataset traceability index.",
    "train_temporal_index.csv": "Training split traceability index.",
    "val_temporal_index.csv": "Validation split traceability index.",
    "test_temporal_index.csv": "Test split traceability index.",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return data


def _load_array(path: Path) -> np.ndarray:
    return np.load(path)


def _rel(path: Path) -> str:
    return path.resolve().relative_to(_ML_ROOT.resolve()).as_posix()


def _artifact_registry() -> list[dict[str, str]]:
    registry: list[dict[str, str]] = []
    for fname, purpose in sorted(REQUIRED_ARTIFACTS.items()):
        path = FINAL_TEMPORAL_DIR / fname
        registry.append(
            {
                "relative_path": _rel(path),
                "purpose": purpose,
                "file_type": _file_type(path),
            }
        )

    registry.append(
        {
            "relative_path": _rel(MANIFEST_PATH),
            "purpose": "Complete manifest for the finalized temporal ML dataset.",
            "file_type": _file_type(MANIFEST_PATH),
        }
    )
    return sorted(registry, key=lambda item: item["relative_path"])


def _validate_required_files() -> None:
    missing = [
        _rel(FINAL_TEMPORAL_DIR / fname)
        for fname in sorted(REQUIRED_ARTIFACTS)
        if not (FINAL_TEMPORAL_DIR / fname).is_file()
    ]
    if missing:
        raise FileNotFoundError("Missing required temporal artifact(s): " + ", ".join(missing))


def _validate_shapes(
    X: np.ndarray,
    y: np.ndarray,
    splits: dict[str, tuple[np.ndarray, np.ndarray]],
) -> None:
    if list(X.shape) != EXPECTED_FULL_SHAPE:
        raise ValueError(f"full_shape expected {EXPECTED_FULL_SHAPE}, got {list(X.shape)}.")
    if list(y.shape) != EXPECTED_LABEL_SHAPE:
        raise ValueError(f"label_shape expected {EXPECTED_LABEL_SHAPE}, got {list(y.shape)}.")
    if X.ndim != 3:
        raise ValueError(f"X_sequence rank must be 3, got {X.ndim}.")
    if y.ndim != 1:
        raise ValueError(f"y_sequence rank must be 1, got {y.ndim}.")
    if X.shape[0] != y.shape[0]:
        raise ValueError(f"X sample count {X.shape[0]} != y length {y.shape[0]}.")
    if np.isnan(X).any() or np.isinf(X).any() or not np.isfinite(X).all():
        raise ValueError("X_sequence.npy contains non-finite values.")

    for split_name, (Xs, ys) in splits.items():
        expected_shape = EXPECTED_SPLIT_SHAPES[split_name]
        if list(Xs.shape) != expected_shape:
            raise ValueError(
                f"{split_name} X shape expected {expected_shape}, got {list(Xs.shape)}."
            )
        if ys.ndim != 1 or ys.shape[0] != Xs.shape[0]:
            raise ValueError(
                f"{split_name} y shape {list(ys.shape)} does not match X samples {Xs.shape[0]}."
            )
        if np.isnan(Xs).any() or np.isinf(Xs).any() or not np.isfinite(Xs).all():
            raise ValueError(f"{split_name} X split contains non-finite values.")


def _class_names_from_mapping(label_mapping: dict[str, Any]) -> list[str]:
    index_to_class = label_mapping.get("index_to_class")
    if not isinstance(index_to_class, dict):
        raise ValueError("temporal_label_mapping.json missing index_to_class.")
    classes = [str(index_to_class[str(i)]) for i in sorted(int(k) for k in index_to_class)]
    if len(classes) != int(label_mapping.get("num_classes", -1)):
        raise ValueError("label mapping num_classes does not match index_to_class length.")
    return classes


def _validate_schema(schema: dict[str, Any], X: np.ndarray) -> tuple[int, int]:
    sequence_length = int(schema.get("sequence_length", -1))
    feature_dim = int(schema.get("num_features", -1))
    feature_columns = schema.get("feature_columns")
    groups = schema.get("feature_groups")

    if sequence_length != X.shape[1]:
        raise ValueError(f"schema sequence_length {sequence_length} != X time dim {X.shape[1]}.")
    if feature_dim != X.shape[2]:
        raise ValueError(f"schema num_features {feature_dim} != X feature dim {X.shape[2]}.")
    if not isinstance(feature_columns, list) or len(feature_columns) != X.shape[2]:
        raise ValueError("schema feature_columns must match tensor feature dimension.")
    if not isinstance(groups, dict):
        raise ValueError("schema feature_groups must be an object.")
    group_total = 0
    for group_name, names in groups.items():
        if not isinstance(names, list):
            raise ValueError(f"schema group {group_name!r} must be a list.")
        group_total += len(names)
    if group_total != X.shape[2]:
        raise ValueError(f"schema feature groups sum to {group_total}, expected {X.shape[2]}.")
    return sequence_length, feature_dim


def _validate_split_metadata(
    split_metadata: dict[str, Any],
    splits: dict[str, tuple[np.ndarray, np.ndarray]],
) -> tuple[dict[str, int], str]:
    split_sizes_raw = split_metadata.get("split_sizes")
    if not isinstance(split_sizes_raw, dict):
        raise ValueError("temporal_split_metadata.json missing split_sizes.")
    split_sizes = {
        "train": int(split_sizes_raw.get("train", -1)),
        "validation": int(split_sizes_raw.get("validation", -1)),
        "test": int(split_sizes_raw.get("test", -1)),
    }
    for split_name, (Xs, _ys) in splits.items():
        if split_sizes[split_name] != Xs.shape[0]:
            raise ValueError(
                f"metadata split size {split_name}={split_sizes[split_name]} "
                f"!= actual {Xs.shape[0]}."
            )

    split_strategy = str(split_metadata.get("split_strategy", "")).strip()
    if split_strategy == "":
        raise ValueError("temporal_split_metadata.json missing split_strategy.")
    if "random_state" not in split_metadata:
        raise ValueError("temporal_split_metadata.json missing random_state.")
    return split_sizes, split_strategy


def _feature_health_summary(feature_health: dict[str, Any]) -> dict[str, Any]:
    total_features = int(feature_health.get("total_features", -1))
    healthy_features = int(feature_health.get("healthy_features", -1))
    dead_features = feature_health.get("dead_features")
    near_dead_features = feature_health.get("near_dead_features")
    noisy_features = feature_health.get("noisy_features")
    correlated_pairs = feature_health.get("highly_correlated_pairs")

    if not isinstance(dead_features, list):
        raise ValueError("temporal_feature_health.json dead_features must be a list.")
    if not isinstance(near_dead_features, list):
        raise ValueError("temporal_feature_health.json near_dead_features must be a list.")
    if not isinstance(noisy_features, list):
        raise ValueError("temporal_feature_health.json noisy_features must be a list.")
    if not isinstance(correlated_pairs, list):
        raise ValueError("temporal_feature_health.json highly_correlated_pairs must be a list.")
    if total_features != 32:
        raise ValueError(f"feature health total_features expected 32, got {total_features}.")
    if healthy_features != 32:
        raise ValueError(f"healthy_features expected 32, got {healthy_features}.")
    if len(dead_features) != 0:
        raise ValueError(f"dead_features expected 0, got {len(dead_features)}.")

    return {
        "total_features": total_features,
        "healthy_features": healthy_features,
        "dead_features": len(dead_features),
        "near_dead_features": len(near_dead_features),
        "noisy_features": len(noisy_features),
        "highly_correlated_pair_count": len(correlated_pairs),
    }


def main() -> int:
    print("──────── Temporal dataset manifest (Phase 6.5) ────────\n")

    try:
        _validate_required_files()

        X = _load_array(FINAL_TEMPORAL_DIR / "X_sequence.npy")
        y = _load_array(FINAL_TEMPORAL_DIR / "y_sequence.npy")
        splits = {
            "train": (
                _load_array(FINAL_TEMPORAL_DIR / "X_train_sequence.npy"),
                _load_array(FINAL_TEMPORAL_DIR / "y_train_sequence.npy"),
            ),
            "validation": (
                _load_array(FINAL_TEMPORAL_DIR / "X_val_sequence.npy"),
                _load_array(FINAL_TEMPORAL_DIR / "y_val_sequence.npy"),
            ),
            "test": (
                _load_array(FINAL_TEMPORAL_DIR / "X_test_sequence.npy"),
                _load_array(FINAL_TEMPORAL_DIR / "y_test_sequence.npy"),
            ),
        }

        _validate_shapes(X, y, splits)

        schema = _load_json(FINAL_TEMPORAL_DIR / "temporal_feature_schema.json")
        label_mapping = _load_json(FINAL_TEMPORAL_DIR / "temporal_label_mapping.json")
        split_metadata = _load_json(FINAL_TEMPORAL_DIR / "temporal_split_metadata.json")
        feature_health = _load_json(FINAL_TEMPORAL_DIR / "temporal_feature_health.json")

        sequence_length, feature_dim = _validate_schema(schema, X)
        class_names = _class_names_from_mapping(label_mapping)
        if len(class_names) != int(label_mapping.get("num_classes", -1)):
            raise ValueError("class names do not match temporal_label_mapping.json.")

        split_sizes, split_strategy = _validate_split_metadata(split_metadata, splits)
        feature_health_summary = _feature_health_summary(feature_health)
        artifact_registry = _artifact_registry()

        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        manifest = {
            "dataset_name": DATASET_NAME,
            "dataset_version": DATASET_VERSION,
            "dataset_type": DATASET_TYPE,
            "created_at": created_at,
            "tensor_contract": {
                "rank": 3,
                "shape_format": "[samples, time_steps, feature_dim]",
                "full_shape": [int(v) for v in X.shape],
                "sequence_length": sequence_length,
                "feature_dim": feature_dim,
                "label_shape": [int(v) for v in y.shape],
            },
            "split_shapes": {
                "train": [int(v) for v in splits["train"][0].shape],
                "validation": [int(v) for v in splits["validation"][0].shape],
                "test": [int(v) for v in splits["test"][0].shape],
            },
            "total_samples": int(X.shape[0]),
            "num_classes": int(label_mapping.get("num_classes", len(class_names))),
            "class_names": class_names,
            "split_sizes": split_sizes,
            "split_strategy": split_strategy,
            "temporal_feature_health_summary": feature_health_summary,
            "artifact_registry": artifact_registry,
            "source_directories": {
                "pose_sequences": "data/processed/pose_sequences",
                "final_temporal": "data/final_temporal",
            },
            "upstream_dependencies": [
                "pose extraction",
                "pose cleaning",
                "normalization",
                "alignment",
                "fixed-length sequence generation",
                "temporal per-frame feature extraction",
            ],
            "future_phase_dependencies": [
                "GRU model training",
                "BiLSTM model training",
                "temporal evaluation",
                "temporal inference pipeline",
                "shot segmentation",
                "coaching feedback engine",
            ],
            "notes": (
                "This is the roadmap-aligned rank-3 temporal dataset for sequence "
                "classification. The older ml/data/final/ rank-2 artifacts remain "
                "tabular baseline artifacts. Phase 7 temporal models should use "
                "data/final_temporal artifacts, schema, splits, and label mapping."
            ),
        }

        if manifest["tensor_contract"]["full_shape"] != EXPECTED_FULL_SHAPE:
            raise ValueError("manifest full_shape validation failed.")
        if manifest["tensor_contract"]["label_shape"] != EXPECTED_LABEL_SHAPE:
            raise ValueError("manifest label_shape validation failed.")
        if feature_health_summary["healthy_features"] != 32:
            raise ValueError("manifest feature health validation failed.")
        if feature_health_summary["dead_features"] != 0:
            raise ValueError("manifest dead feature validation failed.")

        with MANIFEST_PATH.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    except (OSError, ValueError, FileNotFoundError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(f"dataset name:              {DATASET_NAME}")
    print(f"dataset version:           {DATASET_VERSION}")
    print(f"full tensor shape:         {tuple(X.shape)}")
    print("split shapes:")
    for split_name in ("train", "validation", "test"):
        print(f"  - {split_name}: {tuple(splits[split_name][0].shape)}")
    print("feature health summary:")
    for key, value in feature_health_summary.items():
        print(f"  - {key}: {value}")
    print(f"artifacts registered:      {len(artifact_registry)}")
    print("validation passed:         True")
    print(f"manifest path:             {MANIFEST_PATH}")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
