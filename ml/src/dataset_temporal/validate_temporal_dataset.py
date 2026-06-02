"""Phase 6.4 — complete integrity audit for the temporal ML dataset.

Read-only except for writing ``temporal_dataset_report.md``. Does not modify
arrays, create new splits, or train models.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_ML_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = _ML_ROOT / "data" / "final_temporal"
REPORT_PATH = BASE_DIR / "temporal_dataset_report.md"

EXPECTED_SAMPLES = 80
EXPECTED_SEQUENCE_LENGTH = 60
EXPECTED_FEATURE_DIM = 32
EXPECTED_NUM_CLASSES = 4
EXPECTED_SPLIT_SIZES = {"train": 56, "validation": 12, "test": 12}
EXPECTED_CLASS_COUNTS = {"train": 14, "validation": 3, "test": 3}

PATHS = {
    "X_sequence": BASE_DIR / "X_sequence.npy",
    "y_sequence": BASE_DIR / "y_sequence.npy",
    "X_train_sequence": BASE_DIR / "X_train_sequence.npy",
    "X_val_sequence": BASE_DIR / "X_val_sequence.npy",
    "X_test_sequence": BASE_DIR / "X_test_sequence.npy",
    "y_train_sequence": BASE_DIR / "y_train_sequence.npy",
    "y_val_sequence": BASE_DIR / "y_val_sequence.npy",
    "y_test_sequence": BASE_DIR / "y_test_sequence.npy",
    "temporal_feature_schema": BASE_DIR / "temporal_feature_schema.json",
    "temporal_label_mapping": BASE_DIR / "temporal_label_mapping.json",
    "temporal_split_metadata": BASE_DIR / "temporal_split_metadata.json",
    "temporal_dataset_index": BASE_DIR / "temporal_dataset_index.csv",
    "train_temporal_index": BASE_DIR / "train_temporal_index.csv",
    "val_temporal_index": BASE_DIR / "val_temporal_index.csv",
    "test_temporal_index": BASE_DIR / "test_temporal_index.csv",
}


def _load_json(path: Path, errors: list[str], context: str) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"{context}: missing file {path}")
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        errors.append(f"{context}: could not load JSON {path}: {e}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{context}: {path.name} must contain a JSON object.")
        return {}
    return data


def _load_array(path: Path, errors: list[str], context: str) -> np.ndarray | None:
    if not path.is_file():
        errors.append(f"{context}: missing file {path}")
        return None
    try:
        return np.load(path)
    except OSError as e:
        errors.append(f"{context}: could not load array {path}: {e}")
        return None


def _load_csv(path: Path, errors: list[str], context: str) -> pd.DataFrame:
    if not path.is_file():
        errors.append(f"{context}: missing file {path}")
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as e:
        errors.append(f"{context}: could not load CSV {path}: {e}")
        return pd.DataFrame()


def _status(errors: list[str]) -> str:
    return "PASS" if not errors else "FAIL"


def _fmt_dist(dist: dict[str, int]) -> str:
    if not dist:
        return "- None"
    return "\n".join(f"- **{key}**: {value}" for key, value in dist.items())


def _labels_from_y(
    y: np.ndarray,
    index_to_class: dict[str, str],
    errors: list[str],
    context: str,
) -> list[str]:
    labels: list[str] = []
    for raw in np.asarray(y).flat:
        try:
            key = str(int(raw))
        except (TypeError, ValueError) as e:
            errors.append(f"{context}: non-integer encoded label {raw!r}: {e}")
            continue
        if key not in index_to_class:
            errors.append(f"{context}: encoded label {key} missing from label mapping.")
            continue
        labels.append(index_to_class[key])
    return labels


def _distribution(
    y: np.ndarray | None,
    index_to_class: dict[str, str],
    errors: list[str],
    context: str,
) -> dict[str, int]:
    if y is None:
        return {}
    return dict(sorted(Counter(_labels_from_y(y, index_to_class, errors, context)).items()))


def _validate_tensor(
    X: np.ndarray | None,
    y: np.ndarray | None,
    *,
    expected_samples: int | None,
    context: str,
    errors: list[str],
    full_x_dtype: np.dtype | None = None,
    full_y_dtype: np.dtype | None = None,
) -> None:
    if X is None or y is None:
        return

    if X.ndim != 3:
        errors.append(f"{context}: X must be rank 3, got shape {X.shape}.")
    if y.ndim != 1:
        errors.append(f"{context}: y must be rank 1, got shape {y.shape}.")

    if X.ndim == 3:
        if X.shape[1] != EXPECTED_SEQUENCE_LENGTH:
            errors.append(
                f"{context}: sequence length {X.shape[1]} != {EXPECTED_SEQUENCE_LENGTH}."
            )
        if X.shape[2] != EXPECTED_FEATURE_DIM:
            errors.append(f"{context}: feature dim {X.shape[2]} != {EXPECTED_FEATURE_DIM}.")
        if expected_samples is not None and X.shape[0] != expected_samples:
            errors.append(f"{context}: sample count {X.shape[0]} != {expected_samples}.")

    if X.ndim >= 1 and y.ndim == 1 and X.shape[0] != y.shape[0]:
        errors.append(f"{context}: X samples {X.shape[0]} != y length {y.shape[0]}.")

    if np.isnan(X).any():
        errors.append(f"{context}: X contains NaN value(s).")
    if np.isinf(X).any():
        errors.append(f"{context}: X contains infinite value(s).")
    if not np.isfinite(X).all():
        errors.append(f"{context}: X contains non-finite value(s).")

    if full_x_dtype is not None and X.dtype != full_x_dtype:
        errors.append(f"{context}: X dtype {X.dtype} != full X dtype {full_x_dtype}.")
    if full_y_dtype is not None and y.dtype != full_y_dtype:
        errors.append(f"{context}: y dtype {y.dtype} != full y dtype {full_y_dtype}.")
    if not np.issubdtype(y.dtype, np.integer):
        errors.append(f"{context}: y dtype must be integer, got {y.dtype}.")


def _validate_class_balance(
    dist: dict[str, int],
    expected_per_class: int,
    class_names: list[str],
    context: str,
    errors: list[str],
) -> None:
    for class_name in class_names:
        actual = dist.get(class_name)
        if actual != expected_per_class:
            errors.append(
                f"{context}: class {class_name!r} expected {expected_per_class}, got {actual}."
            )


def _validate_schema(
    schema: dict[str, Any],
    X: np.ndarray | None,
    errors: list[str],
) -> None:
    if not schema:
        return
    if int(schema.get("num_features", -1)) != EXPECTED_FEATURE_DIM:
        errors.append("schema: num_features must be 32.")
    if int(schema.get("sequence_length", -1)) != EXPECTED_SEQUENCE_LENGTH:
        errors.append("schema: sequence_length must be 60.")
    if int(schema.get("expected_tensor_rank", -1)) != 3:
        errors.append("schema: expected_tensor_rank must be 3.")

    feature_columns = schema.get("feature_columns")
    if not isinstance(feature_columns, list) or len(feature_columns) != EXPECTED_FEATURE_DIM:
        errors.append("schema: feature_columns must contain 32 entries.")
    if X is not None and X.ndim == 3 and isinstance(feature_columns, list):
        if len(feature_columns) != X.shape[2]:
            errors.append(
                f"schema: feature column count {len(feature_columns)} != X feature dim {X.shape[2]}."
            )

    groups = schema.get("feature_groups")
    if not isinstance(groups, dict):
        errors.append("schema: feature_groups must be an object.")
        return
    grouped: list[str] = []
    for group_name, names in groups.items():
        if not isinstance(names, list):
            errors.append(f"schema: group {group_name!r} must be a list.")
            continue
        grouped.extend(str(name) for name in names)
    if len(grouped) != EXPECTED_FEATURE_DIM:
        errors.append(f"schema: feature groups sum to {len(grouped)}, expected 32.")
    if len(set(grouped)) != len(grouped):
        errors.append("schema: duplicate feature name(s) across feature groups.")
    if isinstance(feature_columns, list) and grouped != [str(name) for name in feature_columns]:
        errors.append("schema: grouped feature order does not match feature_columns.")


def _validate_metadata(
    metadata: dict[str, Any],
    X_train: np.ndarray | None,
    X_val: np.ndarray | None,
    X_test: np.ndarray | None,
    errors: list[str],
) -> None:
    if not metadata:
        return
    if "random_state" not in metadata:
        errors.append("metadata: random_state missing.")
    if "split_strategy" not in metadata:
        errors.append("metadata: split_strategy missing.")
    if int(metadata.get("tensor_rank", -1)) != 3:
        errors.append("metadata: tensor_rank must be 3.")
    if int(metadata.get("sequence_length", -1)) != EXPECTED_SEQUENCE_LENGTH:
        errors.append("metadata: sequence_length must be 60.")
    if int(metadata.get("feature_dim", -1)) != EXPECTED_FEATURE_DIM:
        errors.append("metadata: feature_dim must be 32.")

    split_sizes = metadata.get("split_sizes")
    if not isinstance(split_sizes, dict):
        errors.append("metadata: split_sizes missing or invalid.")
        return

    actual_sizes = {
        "train": int(X_train.shape[0]) if X_train is not None and X_train.ndim >= 1 else None,
        "validation": int(X_val.shape[0]) if X_val is not None and X_val.ndim >= 1 else None,
        "test": int(X_test.shape[0]) if X_test is not None and X_test.ndim >= 1 else None,
    }
    for key, expected_size in EXPECTED_SPLIT_SIZES.items():
        meta_value = split_sizes.get(key)
        if int(meta_value) != expected_size:
            errors.append(f"metadata: split_sizes.{key} {meta_value} != {expected_size}.")
        if actual_sizes[key] is not None and int(meta_value) != actual_sizes[key]:
            errors.append(
                f"metadata: split_sizes.{key} {meta_value} != actual {actual_sizes[key]}."
            )


def _row_index_set(df: pd.DataFrame, context: str, errors: list[str]) -> set[int]:
    if "row_index" not in df.columns:
        errors.append(f"{context}: missing row_index column.")
        return set()
    try:
        values = pd.to_numeric(df["row_index"], errors="raise").astype(int).tolist()
    except (ValueError, TypeError) as e:
        errors.append(f"{context}: row_index must be integer-like: {e}")
        return set()
    if len(values) != len(set(values)):
        errors.append(f"{context}: duplicate row_index values within file.")
    return set(values)


def _validate_indices(
    df_full: pd.DataFrame,
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
    X: np.ndarray | None,
    X_train: np.ndarray | None,
    X_val: np.ndarray | None,
    X_test: np.ndarray | None,
    errors: list[str],
) -> None:
    expected_counts = {
        "full": int(X.shape[0]) if X is not None and X.ndim >= 1 else EXPECTED_SAMPLES,
        "train": int(X_train.shape[0]) if X_train is not None and X_train.ndim >= 1 else 56,
        "validation": int(X_val.shape[0]) if X_val is not None and X_val.ndim >= 1 else 12,
        "test": int(X_test.shape[0]) if X_test is not None and X_test.ndim >= 1 else 12,
    }
    frames = {
        "full": df_full,
        "train": df_train,
        "validation": df_val,
        "test": df_test,
    }
    for name, df in frames.items():
        if len(df) != expected_counts[name]:
            errors.append(
                f"index: {name} row count {len(df)} != expected {expected_counts[name]}."
            )

    full_set = _row_index_set(df_full, "index: full", errors)
    train_set = _row_index_set(df_train, "index: train", errors)
    val_set = _row_index_set(df_val, "index: validation", errors)
    test_set = _row_index_set(df_test, "index: test", errors)

    if full_set and full_set != set(range(expected_counts["full"])):
        errors.append("index: full row_index values must be exactly 0..n-1.")

    overlaps = {
        "train/validation": train_set & val_set,
        "train/test": train_set & test_set,
        "validation/test": val_set & test_set,
    }
    for name, overlap in overlaps.items():
        if overlap:
            errors.append(f"index: duplicate row_index values across {name}: {sorted(overlap)}")

    combined = train_set | val_set | test_set
    missing = full_set - combined
    extra = combined - full_set
    if missing:
        errors.append(f"index: missing row_index values from splits: {sorted(missing)}")
    if extra:
        errors.append(f"index: split row_index values not present in full index: {sorted(extra)}")


def _write_report(
    *,
    errors_by_group: dict[str, list[str]],
    X: np.ndarray | None,
    y: np.ndarray | None,
    X_train: np.ndarray | None,
    X_val: np.ndarray | None,
    X_test: np.ndarray | None,
    y_train: np.ndarray | None,
    y_val: np.ndarray | None,
    y_test: np.ndarray | None,
    class_names: list[str],
    dist_full: dict[str, int],
    dist_train: dict[str, int],
    dist_val: dict[str, int],
    dist_test: dict[str, int],
) -> None:
    generated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def shape_or_na(arr: np.ndarray | None) -> str:
        return str(tuple(arr.shape)) if arr is not None else "n/a"

    checks = {
        "tensor integrity": errors_by_group["tensor"],
        "split integrity": errors_by_group["split"],
        "metadata integrity": errors_by_group["metadata"],
        "schema integrity": errors_by_group["schema"],
        "index traceability": errors_by_group["index"],
        "class balance": errors_by_group["class_balance"],
    }

    lines = [
        "# Temporal Dataset Report",
        "",
        f"Generated: `{generated}`",
        "",
        "# Dataset Summary",
        "",
        f"- X_sequence shape: `{shape_or_na(X)}`",
        f"- y_sequence shape: `{shape_or_na(y)}`",
        f"- Sequence length: `{EXPECTED_SEQUENCE_LENGTH}`",
        f"- Feature dimension: `{EXPECTED_FEATURE_DIM}`",
        f"- Number of classes: `{len(class_names)}`",
        f"- Class names: {', '.join(f'`{name}`' for name in class_names)}",
        "",
        "# Split Summary",
        "",
        f"- X_train_sequence shape: `{shape_or_na(X_train)}`",
        f"- y_train_sequence shape: `{shape_or_na(y_train)}`",
        f"- X_val_sequence shape: `{shape_or_na(X_val)}`",
        f"- y_val_sequence shape: `{shape_or_na(y_val)}`",
        f"- X_test_sequence shape: `{shape_or_na(X_test)}`",
        f"- y_test_sequence shape: `{shape_or_na(y_test)}`",
        "",
        "## Class Distribution - Full",
        "",
        _fmt_dist(dist_full),
        "",
        "## Class Distribution - Train",
        "",
        _fmt_dist(dist_train),
        "",
        "## Class Distribution - Validation",
        "",
        _fmt_dist(dist_val),
        "",
        "## Class Distribution - Test",
        "",
        _fmt_dist(dist_test),
        "",
        "# Validation Checks",
        "",
        "| Check | Status |",
        "|---|---|",
    ]

    for name, group_errors in checks.items():
        lines.append(f"| {name} | {_status(group_errors)} |")

    all_errors = [err for group_errors in errors_by_group.values() for err in group_errors]
    lines.extend(["", f"Overall validation: **{_status(all_errors)}**", ""])

    if all_errors:
        lines.extend(["## Errors", ""])
        for group_name, group_errors in errors_by_group.items():
            for err in group_errors:
                lines.append(f"- **{group_name}**: {err}")
        lines.append("")

    lines.extend(
        [
            "# Engineering Notes",
            "",
            "- Rank-3 tensors preserve the temporal contract expected by sequence models: `[samples, time_steps, features]`.",
            "- Full-sequence splitting prevents frames from the same batting clip leaking across train, validation, and test.",
            "- Deterministic splitting makes model comparisons reproducible across Phase 7 experiments.",
            "- Index traceability keeps every split row tied back to the original video metadata and pose sequence path.",
            "",
            "# Future Dependency Notes",
            "",
            "- Phase 7 temporal training should load these split tensors directly and treat this report as the dataset integrity gate.",
            "- The inference pipeline depends on the same schema, label mapping, sequence length, and feature order validated here.",
            "",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print("──────── Temporal dataset validation (Phase 6.4) ────────\n")

    errors_by_group: dict[str, list[str]] = {
        "tensor": [],
        "split": [],
        "metadata": [],
        "schema": [],
        "index": [],
        "class_balance": [],
    }

    for name, path in PATHS.items():
        if not path.is_file():
            errors_by_group["tensor"].append(f"missing required artifact {name}: {path}")

    schema = _load_json(PATHS["temporal_feature_schema"], errors_by_group["schema"], "schema")
    mapping = _load_json(PATHS["temporal_label_mapping"], errors_by_group["class_balance"], "label mapping")
    metadata = _load_json(PATHS["temporal_split_metadata"], errors_by_group["metadata"], "metadata")

    index_to_class_raw = mapping.get("index_to_class") if isinstance(mapping, dict) else {}
    index_to_class = {
        str(key): str(value)
        for key, value in index_to_class_raw.items()
    } if isinstance(index_to_class_raw, dict) else {}
    class_names = [index_to_class[str(i)] for i in sorted(int(k) for k in index_to_class)] if index_to_class else []
    if len(class_names) != EXPECTED_NUM_CLASSES:
        errors_by_group["class_balance"].append(
            f"label mapping must define {EXPECTED_NUM_CLASSES} classes, got {len(class_names)}."
        )

    X = _load_array(PATHS["X_sequence"], errors_by_group["tensor"], "full tensor")
    y = _load_array(PATHS["y_sequence"], errors_by_group["tensor"], "full labels")
    _validate_tensor(
        X,
        y,
        expected_samples=EXPECTED_SAMPLES,
        context="full",
        errors=errors_by_group["tensor"],
    )

    X_train = _load_array(PATHS["X_train_sequence"], errors_by_group["split"], "train tensor")
    X_val = _load_array(PATHS["X_val_sequence"], errors_by_group["split"], "validation tensor")
    X_test = _load_array(PATHS["X_test_sequence"], errors_by_group["split"], "test tensor")
    y_train = _load_array(PATHS["y_train_sequence"], errors_by_group["split"], "train labels")
    y_val = _load_array(PATHS["y_val_sequence"], errors_by_group["split"], "validation labels")
    y_test = _load_array(PATHS["y_test_sequence"], errors_by_group["split"], "test labels")

    full_x_dtype = X.dtype if X is not None else None
    full_y_dtype = y.dtype if y is not None else None
    _validate_tensor(
        X_train,
        y_train,
        expected_samples=EXPECTED_SPLIT_SIZES["train"],
        context="train",
        errors=errors_by_group["split"],
        full_x_dtype=full_x_dtype,
        full_y_dtype=full_y_dtype,
    )
    _validate_tensor(
        X_val,
        y_val,
        expected_samples=EXPECTED_SPLIT_SIZES["validation"],
        context="validation",
        errors=errors_by_group["split"],
        full_x_dtype=full_x_dtype,
        full_y_dtype=full_y_dtype,
    )
    _validate_tensor(
        X_test,
        y_test,
        expected_samples=EXPECTED_SPLIT_SIZES["test"],
        context="test",
        errors=errors_by_group["split"],
        full_x_dtype=full_x_dtype,
        full_y_dtype=full_y_dtype,
    )

    if y is not None and len(np.unique(y)) != EXPECTED_NUM_CLASSES:
        errors_by_group["tensor"].append(
            f"full y must contain exactly {EXPECTED_NUM_CLASSES} classes."
        )

    _validate_schema(schema, X, errors_by_group["schema"])
    _validate_metadata(metadata, X_train, X_val, X_test, errors_by_group["metadata"])

    dist_full = _distribution(y, index_to_class, errors_by_group["class_balance"], "full y")
    dist_train = _distribution(
        y_train, index_to_class, errors_by_group["class_balance"], "train y"
    )
    dist_val = _distribution(
        y_val, index_to_class, errors_by_group["class_balance"], "validation y"
    )
    dist_test = _distribution(
        y_test, index_to_class, errors_by_group["class_balance"], "test y"
    )

    if class_names:
        _validate_class_balance(
            dist_train,
            EXPECTED_CLASS_COUNTS["train"],
            class_names,
            "train",
            errors_by_group["class_balance"],
        )
        _validate_class_balance(
            dist_val,
            EXPECTED_CLASS_COUNTS["validation"],
            class_names,
            "validation",
            errors_by_group["class_balance"],
        )
        _validate_class_balance(
            dist_test,
            EXPECTED_CLASS_COUNTS["test"],
            class_names,
            "test",
            errors_by_group["class_balance"],
        )

    df_full = _load_csv(PATHS["temporal_dataset_index"], errors_by_group["index"], "full index")
    df_train = _load_csv(PATHS["train_temporal_index"], errors_by_group["index"], "train index")
    df_val = _load_csv(PATHS["val_temporal_index"], errors_by_group["index"], "validation index")
    df_test = _load_csv(PATHS["test_temporal_index"], errors_by_group["index"], "test index")
    _validate_indices(
        df_full,
        df_train,
        df_val,
        df_test,
        X,
        X_train,
        X_val,
        X_test,
        errors_by_group["index"],
    )

    _write_report(
        errors_by_group=errors_by_group,
        X=X,
        y=y,
        X_train=X_train,
        X_val=X_val,
        X_test=X_test,
        y_train=y_train,
        y_val=y_val,
        y_test=y_test,
        class_names=class_names,
        dist_full=dist_full,
        dist_train=dist_train,
        dist_val=dist_val,
        dist_test=dist_test,
    )

    all_errors = [err for group_errors in errors_by_group.values() for err in group_errors]
    passed = len(all_errors) == 0
    split_sizes = {
        "train": int(X_train.shape[0]) if X_train is not None and X_train.ndim >= 1 else "n/a",
        "validation": int(X_val.shape[0]) if X_val is not None and X_val.ndim >= 1 else "n/a",
        "test": int(X_test.shape[0]) if X_test is not None and X_test.ndim >= 1 else "n/a",
    }

    total_samples = int(X.shape[0]) if X is not None and X.ndim >= 1 else "n/a"
    x_shape = tuple(X.shape) if X is not None else "n/a"
    print(f"total samples:      {total_samples}")
    print(f"X shape:            {x_shape}")
    print(
        "split sizes:        "
        f"train={split_sizes['train']}  "
        f"validation={split_sizes['validation']}  "
        f"test={split_sizes['test']}"
    )
    print(f"validation passed:  {passed}")
    print(f"report path:        {REPORT_PATH}")
    if all_errors:
        for err in all_errors:
            print(f"  ERROR: {err}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
