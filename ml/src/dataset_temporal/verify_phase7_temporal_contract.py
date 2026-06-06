"""Phase 7.1 — read-only temporal dataset contract verification.

Checks that the finalized Phase 6 temporal artifacts are compatible with Phase 7
GRU/BiLSTM model building. Does not write files, train models, or modify data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ML_ROOT = Path(__file__).resolve().parents[2]
FINAL_TEMPORAL_DIR = ML_ROOT / "data" / "final_temporal"

EXPECTED_ARRAY_SHAPES = {
    "X_sequence.npy": (80, 60, 32),
    "X_train_sequence.npy": (56, 60, 32),
    "X_val_sequence.npy": (12, 60, 32),
    "X_test_sequence.npy": (12, 60, 32),
    "y_sequence.npy": (80,),
    "y_train_sequence.npy": (56,),
    "y_val_sequence.npy": (12,),
    "y_test_sequence.npy": (12,),
}

REQUIRED_JSON_FILES = (
    "temporal_feature_schema.json",
    "temporal_label_mapping.json",
    "temporal_dataset_manifest.json",
)


def required_paths() -> dict[str, Path]:
    names = list(EXPECTED_ARRAY_SHAPES) + list(REQUIRED_JSON_FILES)
    return {name: FINAL_TEMPORAL_DIR / name for name in names}


def check_required_files(paths: dict[str, Path]) -> list[str]:
    errors: list[str] = []
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"Missing required artifact: {name} ({path})")
    return errors


def load_arrays(paths: dict[str, Path], errors: list[str]) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for name in EXPECTED_ARRAY_SHAPES:
        path = paths[name]
        if not path.is_file():
            continue
        try:
            arrays[name] = np.load(path)
        except OSError as exc:
            errors.append(f"Could not load {name}: {exc}")
    return arrays


def load_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Could not load {label}: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{label} must contain a JSON object.")
        return {}
    return data


def print_array_summary(arrays: dict[str, np.ndarray]) -> None:
    print("Array contract:")
    for name in EXPECTED_ARRAY_SHAPES:
        arr = arrays.get(name)
        if arr is None:
            print(f"  - {name}: not loaded")
        else:
            print(f"  - {name}: shape={arr.shape}, rank={arr.ndim}, dtype={arr.dtype}")


def validate_array_contract(arrays: dict[str, np.ndarray]) -> list[str]:
    errors: list[str] = []
    for name, expected_shape in EXPECTED_ARRAY_SHAPES.items():
        arr = arrays.get(name)
        if arr is None:
            continue
        if arr.shape != expected_shape:
            errors.append(f"{name}: expected shape {expected_shape}, got {arr.shape}")

        if name.startswith("X_") or name == "X_sequence.npy":
            if arr.ndim != 3:
                errors.append(f"{name}: expected rank 3, got rank {arr.ndim}")
        else:
            if arr.ndim != 1:
                errors.append(f"{name}: expected rank 1, got rank {arr.ndim}")
    return errors


def print_schema_summary(schema: dict[str, Any]) -> None:
    sequence_length = schema.get("sequence_length", "missing")
    num_features = schema.get("num_features", "missing")
    feature_columns = schema.get("feature_columns")
    feature_count = len(feature_columns) if isinstance(feature_columns, list) else "missing"
    print("Feature schema:")
    print(f"  - sequence_length: {sequence_length}")
    print(f"  - num_features: {num_features}")
    print(f"  - feature_count: {feature_count}")


def print_label_summary(mapping: dict[str, Any]) -> None:
    index_to_class = mapping.get("index_to_class")
    if isinstance(index_to_class, dict):
        class_names = [str(index_to_class[str(i)]) for i in sorted(int(k) for k in index_to_class)]
    else:
        class_names = []
    print("Label mapping:")
    print(f"  - num_classes: {mapping.get('num_classes', 'missing')}")
    print(f"  - class_names: {class_names if class_names else 'missing'}")


def print_manifest_summary(manifest: dict[str, Any]) -> None:
    print("Dataset manifest:")
    print(f"  - dataset_name: {manifest.get('dataset_name', 'missing')}")
    print(f"  - dataset_version: {manifest.get('dataset_version', 'missing')}")


def main() -> int:
    print("──────── Phase 7.1 Temporal Contract Verification ────────\n")

    errors: list[str] = []
    paths = required_paths()
    errors.extend(check_required_files(paths))

    arrays = load_arrays(paths, errors)
    print_array_summary(arrays)
    errors.extend(validate_array_contract(arrays))

    schema = load_json(paths["temporal_feature_schema.json"], errors, "temporal_feature_schema.json")
    mapping = load_json(paths["temporal_label_mapping.json"], errors, "temporal_label_mapping.json")
    manifest = load_json(paths["temporal_dataset_manifest.json"], errors, "temporal_dataset_manifest.json")

    print()
    print_schema_summary(schema)
    print()
    print_label_summary(mapping)
    print()
    print_manifest_summary(manifest)
    print()

    if errors:
        print("FAIL: Dataset is not compatible with Phase 7 GRU/BiLSTM model building.")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Dataset is compatible with Phase 7 GRU/BiLSTM model building.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
