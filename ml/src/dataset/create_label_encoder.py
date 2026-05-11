"""Phase 6.3 — fit a stable ``LabelEncoder`` for ``shot_label`` and save artifacts.

Reads ``features.csv`` and ``feature_schema.json``. Does not alter the CSV, form X/y,
or perform train/test split.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder


def _ml_root(script_path: Path) -> Path:
    return script_path.resolve().parents[2]


def main() -> int:
    root = _ml_root(Path(__file__))
    csv_path = root / "data" / "processed" / "features" / "features.csv"
    schema_path = root / "data" / "final" / "feature_schema.json"
    out_encoder = root / "data" / "final" / "label_encoder.pkl"
    out_mapping = root / "data" / "final" / "label_mapping.json"

    if not csv_path.is_file():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        return 1
    if not schema_path.is_file():
        print(f"ERROR: Schema not found: {schema_path}", file=sys.stderr)
        return 1

    with schema_path.open(encoding="utf-8") as sf:
        schema = json.load(sf)

    target_column = schema.get("target_column")
    if not target_column or not isinstance(target_column, str):
        print("ERROR: feature_schema.json missing valid target_column.", file=sys.stderr)
        return 1
    if target_column != "shot_label":
        print(f"WARNING: target_column is {target_column!r} (expected 'shot_label').")

    df = pd.read_csv(csv_path)
    if target_column not in df.columns:
        print(
            f"ERROR: Target column {target_column!r} not in CSV. Columns: {list(df.columns)}",
            file=sys.stderr,
        )
        return 1

    y = df[target_column]

    if y.isna().any():
        n_miss = int(y.isna().sum())
        print(f"ERROR: Target has {n_miss} missing value(s).", file=sys.stderr)
        return 1

    labels_raw = y.astype(str)
    if not labels_raw.apply(lambda s: isinstance(s, str)).all():
        print("ERROR: Not all target values are string-like.", file=sys.stderr)
        return 1

    stripped = labels_raw.str.strip()
    if (stripped == "").any():
        print("ERROR: Empty string class label(s) after stripping.", file=sys.stderr)
        return 1

    if stripped.nunique() < 2:
        u = sorted(stripped.unique())
        print(
            f"ERROR: Need at least 2 unique classes, found {stripped.nunique()}: {u}",
            file=sys.stderr,
        )
        return 1

    encoder = LabelEncoder()
    encoder.fit(stripped)

    class_to_index = {
        str(cls): int(encoder.transform([cls])[0]) for cls in encoder.classes_
    }
    index_to_class = {str(i): str(cls) for i, cls in enumerate(encoder.classes_)}

    mapping = {
        "target_column": target_column,
        "num_classes": int(len(encoder.classes_)),
        "class_to_index": class_to_index,
        "index_to_class": index_to_class,
    }

    (root / "data" / "final").mkdir(parents=True, exist_ok=True)
    joblib.dump(encoder, out_encoder)
    with out_mapping.open("w", encoding="utf-8") as mj:
        json.dump(mapping, mj, indent=2)

    print("──────── Label encoder (Phase 6.3) ────────")
    print(f"Source CSV:          {csv_path}")
    print(f"Target column:       {target_column}")
    print(f"Number of classes:   {len(encoder.classes_)}")
    print(f"Class names:         {list(encoder.classes_)}")
    print(f"Encoder saved:       {out_encoder}")
    print(f"Mapping saved:       {out_mapping}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
