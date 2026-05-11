"""Phase 6.4 — materialize full ``X`` and ``y`` arrays and a row-level index CSV.

Uses ``features.csv``, ``feature_schema.json``, and ``label_encoder.pkl``.
Does not split data, train models, or modify the source CSV.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def _ml_root(script_path: Path) -> Path:
    return script_path.resolve().parents[2]


def main() -> int:
    root = _ml_root(Path(__file__))
    csv_path = root / "data" / "processed" / "features" / "features.csv"
    schema_path = root / "data" / "final" / "feature_schema.json"
    encoder_path = root / "data" / "final" / "label_encoder.pkl"
    out_x = root / "data" / "final" / "X.npy"
    out_y = root / "data" / "final" / "y.npy"
    out_index = root / "data" / "final" / "dataset_index.csv"

    for label, path in (
        ("CSV", csv_path),
        ("Schema", schema_path),
        ("Label encoder", encoder_path),
    ):
        if not path.is_file():
            print(f"ERROR: Missing {label}: {path}", file=sys.stderr)
            return 1

    df = pd.read_csv(csv_path)

    with schema_path.open(encoding="utf-8") as sf:
        schema = json.load(sf)

    feature_columns: list[str] = list(schema.get("feature_columns") or [])
    target_column: str | None = schema.get("target_column")

    if not feature_columns:
        print("ERROR: feature_schema.json has empty feature_columns.", file=sys.stderr)
        return 1
    if not target_column:
        print("ERROR: feature_schema.json missing target_column.", file=sys.stderr)
        return 1

    missing_feats = [c for c in feature_columns if c not in df.columns]
    if missing_feats:
        print(f"ERROR: CSV missing feature columns: {missing_feats[:10]}...", file=sys.stderr)
        return 1

    if target_column not in df.columns:
        print(f"ERROR: CSV missing target column {target_column!r}.", file=sys.stderr)
        return 1

    for c in feature_columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            print(f'ERROR: Feature column {c!r} is not numeric (dtype={df[c].dtype}).', file=sys.stderr)
            return 1

    X_df = df[feature_columns].apply(pd.to_numeric, errors="coerce")
    if X_df.isna().any().any():
        n_nan = int(X_df.isna().sum().sum())
        print(f"ERROR: Feature matrix contains {n_nan} NaN value(s).", file=sys.stderr)
        return 1

    arr = X_df.to_numpy(dtype=np.float64)
    if not np.isfinite(arr).all():
        n_bad = int((~np.isfinite(arr)).sum())
        print(f"ERROR: Feature matrix contains {n_bad} non-finite value(s).", file=sys.stderr)
        return 1

    X = arr.astype(np.float32, copy=False)

    tgt_col = df[target_column]
    if tgt_col.isna().any():
        print("ERROR: Target column has missing values.", file=sys.stderr)
        return 1

    target_raw = tgt_col.astype(str).str.strip()
    if (target_raw == "").any():
        print("ERROR: Target column has empty string label(s).", file=sys.stderr)
        return 1

    labels = target_raw.tolist()
    encoder = joblib.load(encoder_path)

    known = set(str(x) for x in getattr(encoder, "classes_", []))
    seen = set(labels)
    unknown = sorted(seen - known)
    if unknown:
        print(
            f"ERROR: Target contains label(s) not seen during encoder fit: {unknown}",
            file=sys.stderr,
        )
        return 1

    y = encoder.transform(labels).astype(np.int64)

    (root / "data" / "final").mkdir(parents=True, exist_ok=True)
    np.save(out_x, X)
    np.save(out_y, y)

    n = len(df)
    index_cols: dict[str, object] = {"row_index": np.arange(n, dtype=np.int64)}
    if "sample_id" in df.columns:
        index_cols["sample_id"] = df["sample_id"].values
    if "source_file" in df.columns:
        index_cols["source_file"] = df["source_file"].values
    index_cols["shot_label"] = labels
    index_cols["encoded_label"] = y

    index_df = pd.DataFrame(index_cols)
    index_df.to_csv(out_index, index=False)

    n_samples = X.shape[0]
    n_features = X.shape[1]
    class_dist = Counter(labels)

    print("──────── Feature matrix build (Phase 6.4) ────────")
    print(f"Source CSV:            {csv_path}")
    print(f"Number of samples:     {n_samples}")
    print(f"Number of features:    {n_features}")
    print(f"X shape:               {X.shape} (dtype {X.dtype})")
    print(f"y shape:               {y.shape} (dtype {y.dtype})")
    print("Class distribution (shot_label):")
    for cls_name in sorted(class_dist):
        print(f"  {cls_name}: {class_dist[cls_name]}")
    print(f"X saved:               {out_x}")
    print(f"y saved:               {out_y}")
    print(f"Dataset index CSV:     {out_index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
