"""Phase 5.10 — sanity-check the engineered feature CSV before training.

Loads ``features.csv``, checks schemas and numeric cleanliness, summarizes
``shot_label`` balance and group means, and writes small reports under
``features/validation/``. Does **not** modify extraction code or train models.

Output files:
- ``feature_validation_summary.json`` — high-level QA numbers
- ``feature_statistics.csv`` — mean/std/min/max per feature column
- ``zero_variance_features.txt`` — stable or near-flat columns (std ≤ 1e-8)

Run from anywhere; paths are anchored to ``ml/data/``.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from feature_config import ALL_FEATURES, NUM_TOTAL_FEATURES


def _json_float(x: float) -> float | None:
    """JSON cannot represent nan/inf cleanly; downgrade to Python null."""
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def main() -> None:
    ml_root = Path(__file__).resolve().parent.parents[1]
    csv_path = ml_root / "data" / "processed" / "features" / "features.csv"
    out_dir = ml_root / "data" / "processed" / "features" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "feature_validation_summary.json"
    stats_path = out_dir / "feature_statistics.csv"
    zero_var_path = out_dir / "zero_variance_features.txt"

    meta_cols = ["sample_id", "source_file", "shot_label"]

    ZERO_VARIANCE_STD = 1e-8

    errors: list[str] = []
    nan_count = 0
    inf_count = 0

    if not csv_path.is_file():
        print(f"ERROR: Dataset not found: {csv_path}", file=sys.stderr)
        with summary_path.open("w", encoding="utf-8") as fj:
            json.dump(
                {
                    "dataset_shape": [0, 0],
                    "num_feature_columns": 0,
                    "class_distribution": {},
                    "nan_count": 0,
                    "inf_count": 0,
                    "zero_variance_feature_count": 0,
                    "zero_variance_features": [],
                    "validation_passed": False,
                    "validation_errors": ["features.csv missing"],
                },
                fj,
                indent=2,
            )
        sys.exit(1)

    df_raw = pd.read_csv(csv_path)
    dataframe_shape_rows, dataframe_shape_cols = int(df_raw.shape[0]), int(df_raw.shape[1])

    for c in meta_cols:
        if c not in df_raw.columns:
            errors.append(f'Missing metadata column "{c}".')

    missing_features = [f for f in ALL_FEATURES if f not in df_raw.columns]
    extra_feature_like = [
        c
        for c in df_raw.columns
        if c not in meta_cols and c not in ALL_FEATURES
    ]
    if extra_feature_like:
        errors.append(f"Unexpected extra columns: {extra_feature_like[:15]}")

    if missing_features:
        errors.append(f"Missing {len(missing_features)} expected feature columns.")

    if dataframe_shape_rows == 0:
        errors.append("Dataset has zero rows.")

    numeric_features = pd.DataFrame()
    df_work = df_raw.copy()

    if not missing_features:
        numeric_features = df_raw[list(ALL_FEATURES)].apply(pd.to_numeric, errors="coerce")

        nan_count = int(numeric_features.isna().sum().sum())
        if nan_count > 0:
            errors.append(f"{nan_count} NaN(s) detected in numeric feature columns.")

        arr_f = numeric_features.astype(float).to_numpy()
        inf_count = int(np.isinf(arr_f).sum())
        if inf_count > 0:
            errors.append(f"{inf_count} non-finite (inf) value(s) detected in numeric features.")

        df_work[list(ALL_FEATURES)] = numeric_features

    stats_rows: list[dict[str, float | str]] = []
    zero_variance_features: list[str] = []

    if numeric_features.shape[1] == NUM_TOTAL_FEATURES and dataframe_shape_rows > 0:
        for feat in ALL_FEATURES:
            series = numeric_features[feat]
            mn = series.min(skipna=True)
            mx = series.max(skipna=True)
            mu = series.mean(skipna=True)
            # Population standard deviation within the dataset (pandas default ddof=1 is sample —
            # v1 QA uses ddof=0 here for «spread of observed rows» intuition).
            sg = series.std(skipna=True, ddof=0)

            mn_f = float(mn) if pd.notna(mn) else float("nan")
            mx_f = float(mx) if pd.notna(mx) else float("nan")
            mu_f = float(mu) if pd.notna(mu) else float("nan")

            obs = int(series.notna().sum())
            if obs <= 1:
                std_f = 0.0
            else:
                std_f = float(sg) if pd.notna(sg) else float("nan")

            stats_rows.append(
                {
                    "feature_name": feat,
                    "mean": mu_f,
                    "std": std_f,
                    "min": mn_f,
                    "max": mx_f,
                }
            )

            if not math.isfinite(std_f) or std_f <= ZERO_VARIANCE_STD:
                zero_variance_features.append(feat)

    cols_stats = ["feature_name", "mean", "std", "min", "max"]
    if stats_rows:
        pd.DataFrame(stats_rows)[cols_stats].to_csv(stats_path, index=False)
    else:
        pd.DataFrame(columns=cols_stats).to_csv(stats_path, index=False)

    zero_var_path.write_text("\n".join(zero_variance_features), encoding="utf-8")

    class_distribution: dict[str, int] = {}
    if "shot_label" in df_work.columns:
        class_distribution = {
            str(k): int(v) for k, v in df_work["shot_label"].astype(str).value_counts().items()
        }

    per_class_means: dict[str, dict[str, float | None]] = {}
    if not missing_features and "shot_label" in df_work.columns:
        grp = df_work.groupby("shot_label", dropna=False)[list(ALL_FEATURES)].mean(
            numeric_only=True
        )
        for lbl, row in grp.iterrows():
            per_class_means[str(lbl)] = {
                fname: _json_float(float(val)) if pd.notna(val) else None
                for fname, val in row.items()
            }

    num_feature_cols = sum(1 for f in ALL_FEATURES if f in df_raw.columns)

    validation_passed = (
        errors == []
        and not missing_features
        and dataframe_shape_rows > 0
        and dataframe_shape_cols == len(meta_cols) + NUM_TOTAL_FEATURES
        and nan_count == 0
        and inf_count == 0
    )

    summary = {
        "dataset_shape": [dataframe_shape_rows, dataframe_shape_cols],
        "num_feature_columns": num_feature_cols,
        "class_distribution": class_distribution,
        "per_label_feature_means": per_class_means,
        "nan_count": nan_count,
        "inf_count": inf_count,
        "zero_variance_feature_count": len(zero_variance_features),
        "zero_variance_features": zero_variance_features,
        "validation_passed": validation_passed,
    }
    if errors:
        summary["validation_errors"] = errors

    with summary_path.open("w", encoding="utf-8") as fj:
        json.dump(summary, fj, indent=2)

    print("──────── Feature dataset validation ────────")
    print(f"CSV path:                 {csv_path}")
    print(f"Dataset shape (rows,cols): ({dataframe_shape_rows}, {dataframe_shape_cols})")
    print(f"Feature columns aligned: {num_feature_cols}/{NUM_TOTAL_FEATURES}")
    print(f"NaN count (features):     {nan_count}")
    print(f"Inf count (features):      {inf_count}")
    print(
        "Zero-variance feature count: {} (std ≤ {:g})".format(
            len(zero_variance_features), ZERO_VARIANCE_STD
        )
    )
    print(f"Validation passed:        {validation_passed}")
    print(f"Wrote validation reports: {out_dir}")
    if errors:
        for err in errors:
            print(f"  Issue: {err}")

    sys.exit(0 if validation_passed else 1)


if __name__ == "__main__":
    main()
