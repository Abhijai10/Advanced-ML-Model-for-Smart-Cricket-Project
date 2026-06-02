"""Phase 6.2 — fit stable label encoding artifacts for temporal sequences.

Reads the temporal tensor and raw label/index sidecars. Writes encoded labels,
a fitted ``LabelEncoder``, and a readable mapping JSON. Does not split data,
train models, or modify ``X_sequence.npy``.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import LabelEncoder

_ML_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = _ML_ROOT / "data" / "final_temporal"

X_SEQUENCE_PATH = INPUT_DIR / "X_sequence.npy"
Y_LABELS_RAW_PATH = INPUT_DIR / "y_labels_raw.csv"
INDEX_CSV_PATH = INPUT_DIR / "temporal_dataset_index.csv"

Y_SEQUENCE_PATH = INPUT_DIR / "y_sequence.npy"
ENCODER_PATH = INPUT_DIR / "temporal_label_encoder.pkl"
MAPPING_PATH = INPUT_DIR / "temporal_label_mapping.json"

EXPECTED_SAMPLES = 80
EXPECTED_FRAMES = 60
EXPECTED_FEATURES = 32
TARGET_COLUMN = "shot_label"
EXPECTED_CLASSES = {
    "cover_drive",
    "defensive_shot",
    "pull_shot",
    "sweep_shot",
}


def _load_and_validate_x() -> np.ndarray:
    if not X_SEQUENCE_PATH.is_file():
        raise FileNotFoundError(f"Missing temporal tensor: {X_SEQUENCE_PATH}")

    X = np.load(X_SEQUENCE_PATH)
    if X.ndim != 3:
        raise ValueError(f"X_sequence.npy must be rank 3, got rank {X.ndim}.")
    if X.shape[0] != EXPECTED_SAMPLES:
        raise ValueError(
            f"X_sequence.npy sample count must be {EXPECTED_SAMPLES}, got {X.shape[0]}."
        )
    if X.shape[1] != EXPECTED_FRAMES:
        raise ValueError(
            f"X_sequence.npy time dimension must be {EXPECTED_FRAMES}, got {X.shape[1]}."
        )
    if X.shape[2] != EXPECTED_FEATURES:
        raise ValueError(
            f"X_sequence.npy feature dimension must be {EXPECTED_FEATURES}, got {X.shape[2]}."
        )
    if np.isnan(X).any():
        raise ValueError("X_sequence.npy contains NaN value(s).")
    if np.isinf(X).any():
        raise ValueError("X_sequence.npy contains infinite value(s).")
    if not np.isfinite(X).all():
        raise ValueError("X_sequence.npy contains non-finite value(s).")
    return X


def _load_and_validate_labels() -> list[str]:
    if not Y_LABELS_RAW_PATH.is_file():
        raise FileNotFoundError(f"Missing raw label CSV: {Y_LABELS_RAW_PATH}")

    labels: list[str] = []
    with Y_LABELS_RAW_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("y_labels_raw.csv has no header row.")
        missing_columns = {"row_index", TARGET_COLUMN} - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"y_labels_raw.csv missing required column(s): {sorted(missing_columns)}"
            )

        for expected_row_index, row in enumerate(reader):
            raw_index = row.get("row_index")
            try:
                row_index = int(str(raw_index).strip())
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"Invalid row_index at raw label row {expected_row_index}: {raw_index!r}"
                ) from e
            if row_index != expected_row_index:
                raise ValueError(
                    f"Expected row_index {expected_row_index}, got {row_index}."
                )

            raw_label = row.get(TARGET_COLUMN)
            if raw_label is None:
                raise ValueError(f"Missing {TARGET_COLUMN!r} at row_index {row_index}.")
            label = str(raw_label).strip()
            if label == "":
                raise ValueError(f"Empty {TARGET_COLUMN!r} after stripping at row_index {row_index}.")
            labels.append(label)

    unique = set(labels)
    if len(unique) < 2:
        raise ValueError(f"Need at least 2 unique classes, found {sorted(unique)}.")

    missing_expected = sorted(EXPECTED_CLASSES - unique)
    if missing_expected:
        raise ValueError(f"Missing expected temporal class(es): {missing_expected}")

    return labels


def _count_index_rows() -> int:
    if not INDEX_CSV_PATH.is_file():
        raise FileNotFoundError(f"Missing temporal dataset index: {INDEX_CSV_PATH}")

    with INDEX_CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("temporal_dataset_index.csv has no header row.")
        return sum(1 for _ in reader)


def _build_mapping(encoder: LabelEncoder) -> dict[str, object]:
    class_to_index = {
        str(cls): int(encoder.transform([cls])[0]) for cls in encoder.classes_
    }
    index_to_class = {str(i): str(cls) for i, cls in enumerate(encoder.classes_)}
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "target_column": TARGET_COLUMN,
        "num_classes": int(len(encoder.classes_)),
        "class_to_index": class_to_index,
        "index_to_class": index_to_class,
        "created_at": created_at,
        "notes": (
            "Stable temporal sequence label encoding for Phase 6.2. "
            "Classes are sorted by sklearn.preprocessing.LabelEncoder and y_sequence.npy "
            "stores int64 class indices aligned row-for-row with X_sequence.npy."
        ),
    }


def main() -> int:
    print("──────── Temporal label encoder (Phase 6.2) ────────\n")

    try:
        X = _load_and_validate_x()
        labels = _load_and_validate_labels()

        if len(labels) != X.shape[0]:
            raise ValueError(
                f"Raw label count {len(labels)} != X_sequence sample count {X.shape[0]}."
            )

        index_row_count = _count_index_rows()
        if index_row_count != len(labels):
            raise ValueError(
                f"temporal_dataset_index.csv row count {index_row_count} != label count {len(labels)}."
            )

        encoder = LabelEncoder()
        encoder.fit(labels)
        y_sequence = encoder.transform(labels).astype(np.int64)

        expected_y = encoder.transform(labels).astype(np.int64)
        if y_sequence.shape != (EXPECTED_SAMPLES,):
            raise ValueError(
                f"y_sequence shape must be ({EXPECTED_SAMPLES},), got {y_sequence.shape}."
            )
        if len(y_sequence) != X.shape[0]:
            raise ValueError(
                f"y_sequence length {len(y_sequence)} != X_sequence sample count {X.shape[0]}."
            )
        if not np.array_equal(y_sequence, expected_y):
            raise ValueError("Encoded labels do not exactly match encoder class indices.")
        if y_sequence.dtype != np.int64:
            raise ValueError(f"y_sequence dtype must be int64, got {y_sequence.dtype}.")

        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        np.save(Y_SEQUENCE_PATH, y_sequence)
        joblib.dump(encoder, ENCODER_PATH)

        mapping = _build_mapping(encoder)
        with MAPPING_PATH.open("w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2)

    except (OSError, ValueError, FileNotFoundError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    class_dist = Counter(labels)
    print(f"X_sequence shape:      {tuple(X.shape)}")
    print(f"Number of labels:      {len(labels)}")
    print(f"Number of classes:     {len(encoder.classes_)}")
    print(f"Class names:           {[str(cls) for cls in encoder.classes_]}")
    print("Class distribution:")
    for cls_name in sorted(class_dist):
        print(f"  - {cls_name}: {class_dist[cls_name]}")
    print("Output paths:")
    print(f"  - {Y_SEQUENCE_PATH}")
    print(f"  - {ENCODER_PATH}")
    print(f"  - {MAPPING_PATH}")
    print("validation passed:     True")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
