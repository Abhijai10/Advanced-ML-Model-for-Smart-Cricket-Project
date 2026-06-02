"""Phase 6.3 — train / validation / test splits for temporal sequence tensors.

Uses a manual deterministic per-class split: for each encoded class, sample
indices are shuffled with a fixed seed, then assigned 14 / 3 / 3 complete
sequences to train / validation / test. Frames are never split across splits.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_STATE = 42
TRAIN_PER_CLASS = 14
VAL_PER_CLASS = 3
TEST_PER_CLASS = 3
SAMPLES_PER_CLASS = TRAIN_PER_CLASS + VAL_PER_CLASS + TEST_PER_CLASS

EXPECTED_SAMPLES = 80
EXPECTED_SEQUENCE_LENGTH = 60
EXPECTED_FEATURE_DIM = 32
EXPECTED_NUM_CLASSES = 4

_ML_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = _ML_ROOT / "data" / "final_temporal"

X_PATH = BASE_DIR / "X_sequence.npy"
Y_PATH = BASE_DIR / "y_sequence.npy"
INDEX_PATH = BASE_DIR / "temporal_dataset_index.csv"
MAPPING_PATH = BASE_DIR / "temporal_label_mapping.json"
SCHEMA_PATH = BASE_DIR / "temporal_feature_schema.json"


def _load_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing input: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return data


def _validate_schema() -> None:
    schema = _load_json(SCHEMA_PATH)
    if int(schema.get("expected_tensor_rank", 0)) != 3:
        raise ValueError("temporal_feature_schema.json expected_tensor_rank must be 3.")
    if int(schema.get("sequence_length", 0)) != EXPECTED_SEQUENCE_LENGTH:
        raise ValueError(
            "temporal_feature_schema.json sequence_length must be "
            f"{EXPECTED_SEQUENCE_LENGTH}."
        )
    if int(schema.get("num_features", 0)) != EXPECTED_FEATURE_DIM:
        raise ValueError(
            f"temporal_feature_schema.json num_features must be {EXPECTED_FEATURE_DIM}."
        )
    feature_columns = schema.get("feature_columns")
    if not isinstance(feature_columns, list) or len(feature_columns) != EXPECTED_FEATURE_DIM:
        raise ValueError(
            "temporal_feature_schema.json must contain 32 feature_columns."
        )


def _load_mapping() -> dict[str, str]:
    mapping = _load_json(MAPPING_PATH)
    index_to_class = mapping.get("index_to_class")
    if not isinstance(index_to_class, dict) or len(index_to_class) != EXPECTED_NUM_CLASSES:
        raise ValueError(
            "temporal_label_mapping.json index_to_class must contain exactly 4 classes."
        )

    out: dict[str, str] = {}
    for key, value in index_to_class.items():
        try:
            int(key)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid label index in mapping: {key!r}") from e
        label = str(value).strip()
        if label == "":
            raise ValueError(f"Empty class name in mapping for index {key!r}.")
        out[str(key)] = label
    return out


def _labels_from_y(y: np.ndarray, index_to_class: dict[str, str]) -> list[str]:
    labels: list[str] = []
    for value in y:
        key = str(int(value))
        if key not in index_to_class:
            raise ValueError(f"y value {value!r} has no class in temporal label mapping.")
        labels.append(index_to_class[key])
    return labels


def _distribution(y: np.ndarray, index_to_class: dict[str, str]) -> dict[str, int]:
    labels = _labels_from_y(y, index_to_class)
    return {key: int(value) for key, value in sorted(Counter(labels).items())}


def _load_and_validate_arrays() -> tuple[np.ndarray, np.ndarray]:
    if not X_PATH.is_file():
        raise FileNotFoundError(f"Missing X_sequence.npy: {X_PATH}")
    if not Y_PATH.is_file():
        raise FileNotFoundError(f"Missing y_sequence.npy: {Y_PATH}")

    X = np.load(X_PATH)
    y = np.load(Y_PATH)

    if X.ndim != 3:
        raise ValueError(f"X_sequence.npy must be rank 3, got shape {X.shape}.")
    if y.ndim != 1:
        raise ValueError(f"y_sequence.npy must be rank 1, got shape {y.shape}.")
    if X.shape[0] != y.shape[0]:
        raise ValueError(
            f"Sample count mismatch: X has {X.shape[0]}, y has {y.shape[0]}."
        )
    if X.shape[0] != EXPECTED_SAMPLES:
        raise ValueError(f"Expected {EXPECTED_SAMPLES} samples, got {X.shape[0]}.")
    if X.shape[1] != EXPECTED_SEQUENCE_LENGTH:
        raise ValueError(
            f"Expected sequence length {EXPECTED_SEQUENCE_LENGTH}, got {X.shape[1]}."
        )
    if X.shape[2] != EXPECTED_FEATURE_DIM:
        raise ValueError(
            f"Expected feature dim {EXPECTED_FEATURE_DIM}, got {X.shape[2]}."
        )
    if np.isnan(X).any():
        raise ValueError("X_sequence.npy contains NaN value(s).")
    if np.isinf(X).any():
        raise ValueError("X_sequence.npy contains infinite value(s).")
    if not np.isfinite(X).all():
        raise ValueError("X_sequence.npy contains non-finite value(s).")

    unique_classes = np.unique(y)
    if len(unique_classes) != EXPECTED_NUM_CLASSES:
        raise ValueError(
            f"y_sequence.npy must contain exactly {EXPECTED_NUM_CLASSES} classes, "
            f"got {len(unique_classes)}."
        )
    return X, y


def _load_index() -> pd.DataFrame:
    if not INDEX_PATH.is_file():
        raise FileNotFoundError(f"Missing temporal_dataset_index.csv: {INDEX_PATH}")
    df = pd.read_csv(INDEX_PATH)
    if len(df) != EXPECTED_SAMPLES:
        raise ValueError(
            f"temporal_dataset_index.csv must have {EXPECTED_SAMPLES} rows, got {len(df)}."
        )
    if "row_index" not in df.columns:
        raise ValueError("temporal_dataset_index.csv missing row_index column.")
    expected = np.arange(len(df), dtype=np.int64)
    actual = pd.to_numeric(df["row_index"], errors="raise").to_numpy(dtype=np.int64)
    if not np.array_equal(actual, expected):
        raise ValueError("temporal_dataset_index.csv row_index must be 0..n-1.")
    return df


def _manual_per_class_split_indices(
    y: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    classes = np.sort(np.unique(y))
    train_parts: list[np.ndarray] = []
    val_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []

    for class_id in classes:
        idx = np.flatnonzero(y == class_id)
        if int(idx.size) != SAMPLES_PER_CLASS:
            raise ValueError(
                f"Class {class_id!r} has {idx.size} samples; expected exactly "
                f"{SAMPLES_PER_CLASS} for 14/3/3 splitting."
            )
        idx = idx.copy()
        rng.shuffle(idx)
        train_parts.append(idx[:TRAIN_PER_CLASS])
        val_parts.append(idx[TRAIN_PER_CLASS : TRAIN_PER_CLASS + VAL_PER_CLASS])
        test_parts.append(idx[TRAIN_PER_CLASS + VAL_PER_CLASS :])

    train_idx = np.concatenate(train_parts)
    val_idx = np.concatenate(val_parts)
    test_idx = np.concatenate(test_parts)

    rng.shuffle(train_idx)
    rng.shuffle(val_idx)
    rng.shuffle(test_idx)
    return train_idx, val_idx, test_idx


def _verify_split_counts(
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    classes: np.ndarray,
) -> None:
    for class_id in classes:
        train_count = int(np.sum(y_train == class_id))
        val_count = int(np.sum(y_val == class_id))
        test_count = int(np.sum(y_test == class_id))
        if train_count != TRAIN_PER_CLASS:
            raise ValueError(
                f"Train split class {class_id!r}: expected {TRAIN_PER_CLASS}, got {train_count}."
            )
        if val_count != VAL_PER_CLASS:
            raise ValueError(
                f"Validation split class {class_id!r}: expected {VAL_PER_CLASS}, got {val_count}."
            )
        if test_count != TEST_PER_CLASS:
            raise ValueError(
                f"Test split class {class_id!r}: expected {TEST_PER_CLASS}, got {test_count}."
            )


def _validate_outputs(
    X_train: np.ndarray,
    X_val: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
) -> None:
    expected_x_shapes = {
        "X_train_sequence": (56, EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM),
        "X_val_sequence": (12, EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM),
        "X_test_sequence": (12, EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM),
    }
    actual_x_shapes = {
        "X_train_sequence": X_train.shape,
        "X_val_sequence": X_val.shape,
        "X_test_sequence": X_test.shape,
    }
    for name, expected in expected_x_shapes.items():
        if actual_x_shapes[name] != expected:
            raise ValueError(f"{name} shape expected {expected}, got {actual_x_shapes[name]}.")

    expected_y_shapes = {
        "y_train_sequence": (56,),
        "y_val_sequence": (12,),
        "y_test_sequence": (12,),
    }
    actual_y_shapes = {
        "y_train_sequence": y_train.shape,
        "y_val_sequence": y_val.shape,
        "y_test_sequence": y_test.shape,
    }
    for name, expected in expected_y_shapes.items():
        if actual_y_shapes[name] != expected:
            raise ValueError(f"{name} shape expected {expected}, got {actual_y_shapes[name]}.")


def main() -> int:
    print("──────── Temporal dataset splits (Phase 6.3) ────────\n")

    try:
        _validate_schema()
        index_to_class = _load_mapping()
        X, y = _load_and_validate_arrays()
        df_index = _load_index()
        if len(df_index) != X.shape[0]:
            raise ValueError(
                f"temporal_dataset_index rows ({len(df_index)}) != X samples ({X.shape[0]})."
            )

        rng = np.random.default_rng(RANDOM_STATE)
        train_idx, val_idx, test_idx = _manual_per_class_split_indices(y, rng)

        X_train = X[train_idx]
        X_val = X[val_idx]
        X_test = X[test_idx]
        y_train = y[train_idx]
        y_val = y[val_idx]
        y_test = y[test_idx]

        classes = np.sort(np.unique(y))
        _verify_split_counts(y_train, y_val, y_test, classes)
        _validate_outputs(X_train, X_val, X_test, y_train, y_val, y_test)

        output_files = {
            "X_train_sequence": BASE_DIR / "X_train_sequence.npy",
            "X_val_sequence": BASE_DIR / "X_val_sequence.npy",
            "X_test_sequence": BASE_DIR / "X_test_sequence.npy",
            "y_train_sequence": BASE_DIR / "y_train_sequence.npy",
            "y_val_sequence": BASE_DIR / "y_val_sequence.npy",
            "y_test_sequence": BASE_DIR / "y_test_sequence.npy",
            "train_temporal_index": BASE_DIR / "train_temporal_index.csv",
            "val_temporal_index": BASE_DIR / "val_temporal_index.csv",
            "test_temporal_index": BASE_DIR / "test_temporal_index.csv",
            "temporal_split_metadata": BASE_DIR / "temporal_split_metadata.json",
        }

        np.save(output_files["X_train_sequence"], X_train)
        np.save(output_files["X_val_sequence"], X_val)
        np.save(output_files["X_test_sequence"], X_test)
        np.save(output_files["y_train_sequence"], y_train.astype(np.int64, copy=False))
        np.save(output_files["y_val_sequence"], y_val.astype(np.int64, copy=False))
        np.save(output_files["y_test_sequence"], y_test.astype(np.int64, copy=False))

        df_index.iloc[train_idx].to_csv(output_files["train_temporal_index"], index=False)
        df_index.iloc[val_idx].to_csv(output_files["val_temporal_index"], index=False)
        df_index.iloc[test_idx].to_csv(output_files["test_temporal_index"], index=False)

        dist_all = _distribution(y, index_to_class)
        dist_train = _distribution(y_train, index_to_class)
        dist_val = _distribution(y_val, index_to_class)
        dist_test = _distribution(y_test, index_to_class)

        metadata = {
            "random_state": RANDOM_STATE,
            "split_strategy": "manual deterministic per-class stratified split",
            "tensor_rank": 3,
            "sequence_length": EXPECTED_SEQUENCE_LENGTH,
            "feature_dim": EXPECTED_FEATURE_DIM,
            "per_class_allocation": {
                "train": TRAIN_PER_CLASS,
                "validation": VAL_PER_CLASS,
                "test": TEST_PER_CLASS,
            },
            "split_sizes": {
                "train": int(len(y_train)),
                "validation": int(len(y_val)),
                "test": int(len(y_test)),
            },
            "class_distribution_overall": dist_all,
            "class_distribution_train": dist_train,
            "class_distribution_val": dist_val,
            "class_distribution_test": dist_test,
            "output_files": {
                key: value.resolve().as_posix() for key, value in output_files.items()
            },
            "notes": (
                "Full temporal sequences are split by sample index; frames inside a "
                "sequence are never split across train, validation, or test. For each "
                f"class, {TRAIN_PER_CLASS} complete sequences go to train, "
                f"{VAL_PER_CLASS} to validation, and {TEST_PER_CLASS} to test, then "
                "each split index list is shuffled deterministically."
            ),
        }

        with output_files["temporal_split_metadata"].open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    except (OSError, ValueError, FileNotFoundError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(f"X_sequence shape:       {tuple(X.shape)}")
    print(f"y_sequence shape:       {tuple(y.shape)}")
    print(f"X_train_sequence shape: {tuple(X_train.shape)}")
    print(f"X_val_sequence shape:   {tuple(X_val.shape)}")
    print(f"X_test_sequence shape:  {tuple(X_test.shape)}")
    print(f"y_train_sequence shape: {tuple(y_train.shape)}")
    print(f"y_val_sequence shape:   {tuple(y_val.shape)}")
    print(f"y_test_sequence shape:  {tuple(y_test.shape)}")
    print("Class distribution — train:")
    for key, value in dist_train.items():
        print(f"  - {key}: {value}")
    print("Class distribution — validation:")
    for key, value in dist_val.items():
        print(f"  - {key}: {value}")
    print("Class distribution — test:")
    for key, value in dist_test.items():
        print(f"  - {key}: {value}")
    print("Output paths:")
    for value in output_files.values():
        print(f"  - {value}")
    print("validation passed:      True")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
