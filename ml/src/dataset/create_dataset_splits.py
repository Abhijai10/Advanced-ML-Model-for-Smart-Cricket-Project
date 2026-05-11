"""Phase 6.5 — train / validation / test splits for ``X`` and ``y``.

Uses a **manual deterministic per-class split**: for each encoded class, sample
indices are shuffled with a fixed seed, then assigned 14 / 3 / 3 rows to
train / validation / test (20 rows per class). Finally, train, val, and test
index lists are each shuffled independently with the same RNG for reproducible
row order within splits.

Loads full arrays from ``ml/data/final/`` and writes split arrays, per-split index
CSVs, and ``split_metadata.json``. Does not train models or edit the original
``X.npy`` / ``y.npy`` / ``features.csv``.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_STATE = 42
# Per-class allocation (requires exactly 20 samples per class in ``y``).
TRAIN_PER_CLASS = 14
VAL_PER_CLASS = 3
TEST_PER_CLASS = 3
SAMPLES_PER_CLASS = TRAIN_PER_CLASS + VAL_PER_CLASS + TEST_PER_CLASS


def _ml_root(script_path: Path) -> Path:
    return script_path.resolve().parents[2]


def _labels_from_y(y: np.ndarray, index_to_class: dict[str, str]) -> list[str]:
    out: list[str] = []
    for v in y:
        key = str(int(v))
        if key not in index_to_class:
            raise ValueError(f"y value {v!r} has no entry in label_mapping index_to_class")
        out.append(index_to_class[key])
    return out


def _distribution_strings(y: np.ndarray, index_to_class: dict[str, str]) -> dict[str, int]:
    names = _labels_from_y(y, index_to_class)
    return {k: int(v) for k, v in sorted(Counter(names).items())}


def _manual_per_class_split_indices(
    y: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return row indices for train, val, and test (global positions into ``X`` / ``y``)."""
    classes = np.sort(np.unique(y))
    train_parts: list[np.ndarray] = []
    val_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []

    for c in classes:
        idx = np.flatnonzero(y == c)
        if int(idx.size) != SAMPLES_PER_CLASS:
            raise ValueError(
                f"Class {c!r} has {idx.size} samples; expected exactly "
                f"{SAMPLES_PER_CLASS} for manual 14/3/3 split."
            )
        idx = idx.copy()
        rng.shuffle(idx)
        train_parts.append(idx[:TRAIN_PER_CLASS])
        val_parts.append(idx[TRAIN_PER_CLASS : TRAIN_PER_CLASS + VAL_PER_CLASS])
        test_parts.append(idx[TRAIN_PER_CLASS + VAL_PER_CLASS :])

    pos_train = np.concatenate(train_parts)
    pos_val = np.concatenate(val_parts)
    pos_test = np.concatenate(test_parts)

    rng.shuffle(pos_train)
    rng.shuffle(pos_val)
    rng.shuffle(pos_test)
    return pos_train, pos_val, pos_test


def _verify_per_class_counts(
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    classes: np.ndarray,
) -> str | None:
    """Return an error message if counts differ; otherwise None."""
    for c in classes:
        if int(np.sum(y_train == c)) != TRAIN_PER_CLASS:
            return (
                f"Train split: class {c!r} should have {TRAIN_PER_CLASS} samples, "
                f"got {int(np.sum(y_train == c))}."
            )
        if int(np.sum(y_val == c)) != VAL_PER_CLASS:
            return (
                f"Validation split: class {c!r} should have {VAL_PER_CLASS} samples, "
                f"got {int(np.sum(y_val == c))}."
            )
        if int(np.sum(y_test == c)) != TEST_PER_CLASS:
            return (
                f"Test split: class {c!r} should have {TEST_PER_CLASS} samples, "
                f"got {int(np.sum(y_test == c))}."
            )
    return None


def main() -> int:
    root = _ml_root(Path(__file__))
    base = root / "data" / "final"

    x_path = base / "X.npy"
    y_path = base / "y.npy"
    index_path = base / "dataset_index.csv"
    mapping_path = base / "label_mapping.json"

    paths_in = {
        "X.npy": x_path,
        "y.npy": y_path,
        "dataset_index.csv": index_path,
        "label_mapping.json": mapping_path,
    }
    for name, p in paths_in.items():
        if not p.is_file():
            print(f"ERROR: Missing input {name}: {p}", file=sys.stderr)
            return 1

    X = np.load(x_path)
    y = np.load(y_path)

    if X.ndim != 2:
        print(f"ERROR: X must be 2D, got shape {X.shape}", file=sys.stderr)
        return 1
    if y.ndim != 1:
        print(f"ERROR: y must be 1D, got shape {y.shape}", file=sys.stderr)
        return 1
    if X.shape[0] != y.shape[0]:
        print(
            f"ERROR: Sample count mismatch X={X.shape[0]} vs y={y.shape[0]}.",
            file=sys.stderr,
        )
        return 1

    if not np.isfinite(X).all():
        n_bad = int((~np.isfinite(X)).sum())
        print(f"ERROR: X contains {n_bad} non-finite value(s).", file=sys.stderr)
        return 1

    n_classes = int(len(np.unique(y)))
    if n_classes < 2:
        print("ERROR: y must contain at least 2 distinct classes.", file=sys.stderr)
        return 1

    df_idx = pd.read_csv(index_path)
    if len(df_idx) != X.shape[0]:
        print(
            f"ERROR: dataset_index rows ({len(df_idx)}) != X rows ({X.shape[0]}).",
            file=sys.stderr,
        )
        return 1

    with mapping_path.open(encoding="utf-8") as f:
        label_mapping = json.load(f)

    index_to_class = label_mapping.get("index_to_class") or {}
    if not index_to_class:
        print("ERROR: label_mapping.json missing index_to_class.", file=sys.stderr)
        return 1

    n = X.shape[0]
    rng = np.random.default_rng(RANDOM_STATE)

    class_ids = np.unique(y)
    try:
        pos_train, pos_val, pos_test = _manual_per_class_split_indices(y, rng)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    X_train = X[pos_train]
    X_val = X[pos_val]
    X_test = X[pos_test]
    y_train = y[pos_train]
    y_val = y[pos_val]
    y_test = y[pos_test]

    count_err = _verify_per_class_counts(y_train, y_val, y_test, class_ids)
    if count_err is not None:
        print(f"ERROR: {count_err}", file=sys.stderr)
        return 1

    out = {
        "X_train.npy": base / "X_train.npy",
        "X_val.npy": base / "X_val.npy",
        "X_test.npy": base / "X_test.npy",
        "y_train.npy": base / "y_train.npy",
        "y_val.npy": base / "y_val.npy",
        "y_test.npy": base / "y_test.npy",
        "train_index.csv": base / "train_index.csv",
        "val_index.csv": base / "val_index.csv",
        "test_index.csv": base / "test_index.csv",
        "split_metadata.json": base / "split_metadata.json",
    }

    np.save(out["X_train.npy"], X_train)
    np.save(out["X_val.npy"], X_val)
    np.save(out["X_test.npy"], X_test)
    np.save(out["y_train.npy"], y_train)
    np.save(out["y_val.npy"], y_val)
    np.save(out["y_test.npy"], y_test)

    df_idx.iloc[pos_train].to_csv(out["train_index.csv"], index=False)
    df_idx.iloc[pos_val].to_csv(out["val_index.csv"], index=False)
    df_idx.iloc[pos_test].to_csv(out["test_index.csv"], index=False)

    num_features = int(X.shape[1])
    dist_all = _distribution_strings(y, index_to_class)
    dist_train = _distribution_strings(y_train, index_to_class)
    dist_val = _distribution_strings(y_val, index_to_class)
    dist_test = _distribution_strings(y_test, index_to_class)

    train_ratio = (TRAIN_PER_CLASS * len(class_ids)) / n if n else 0.0
    val_ratio_single = (VAL_PER_CLASS * len(class_ids)) / n if n else 0.0
    test_ratio_single = (TEST_PER_CLASS * len(class_ids)) / n if n else 0.0

    metadata = {
        "split_strategy": "manual deterministic per-class stratified split",
        "random_state": RANDOM_STATE,
        "per_class_allocation": {
            "train": TRAIN_PER_CLASS,
            "validation": VAL_PER_CLASS,
            "test": TEST_PER_CLASS,
            "samples_per_class_required": SAMPLES_PER_CLASS,
        },
        "split_ratios": {
            "train": round(train_ratio, 6),
            "validation": round(val_ratio_single, 6),
            "test": round(test_ratio_single, 6),
        },
        "total_samples": n,
        "num_features": num_features,
        "num_classes": int(len(class_ids)),
        "split_sizes": {
            "train": int(len(y_train)),
            "validation": int(len(y_val)),
            "test": int(len(y_test)),
        },
        "class_distribution_overall": dist_all,
        "class_distribution_train": dist_train,
        "class_distribution_val": dist_val,
        "class_distribution_test": dist_test,
        "output_files": {k: str(v.resolve().as_posix()) for k, v in out.items()},
        "notes": (
            "manual deterministic per-class stratified split: for each class, "
            f"shuffle row indices with random_state={RANDOM_STATE}, assign "
            f"first {TRAIN_PER_CLASS} to train, next {VAL_PER_CLASS} to validation, "
            f"final {TEST_PER_CLASS} to test; then shuffle train, val, and test "
            "row order independently with the same RNG. Requires exactly "
            f"{SAMPLES_PER_CLASS} samples per class."
        ),
    }

    with out["split_metadata.json"].open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("──────── Dataset splits (Phase 6.5) ────────")
    print(f"Source X:              {x_path}")
    print(f"Source y:              {y_path}")
    print(f"Total samples:         {n}")
    print(f"Number of features:    {num_features}")
    print(
        f"Train size:            {len(y_train)} ({len(y_train)/n:.1%})"
    )
    print(
        f"Validation size:        {len(y_val)} ({len(y_val)/n:.1%})"
    )
    print(
        f"Test size:              {len(y_test)} ({len(y_test)/n:.1%})"
    )
    print(f"X_train / X_val / X_test shapes: {X_train.shape}, {X_val.shape}, {X_test.shape}")
    print(f"y_train / y_val / y_test shapes: {y_train.shape}, {y_val.shape}, {y_test.shape}")
    print("Class distribution — overall:")
    for k, v in dist_all.items():
        print(f"  {k}: {v}")
    print("Class distribution — train:")
    for k, v in dist_train.items():
        print(f"  {k}: {v}")
    print("Class distribution — validation:")
    for k, v in dist_val.items():
        print(f"  {k}: {v}")
    print("Class distribution — test:")
    for k, v in dist_test.items():
        print(f"  {k}: {v}")
    for label, p in out.items():
        print(f"{label}:  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
