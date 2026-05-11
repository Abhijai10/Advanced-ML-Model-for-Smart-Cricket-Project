"""Phase 6 — derive a stable feature schema from engineered ``features.csv``.

Reads ``ml/data/processed/features/features.csv`` and writes ``ml/data/final/feature_schema.json``.
No train/test split, no label encoding, and the source CSV is never modified.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

TARGET_COLUMN = "shot_label"

METADATA_CANDIDATES = [
    "video_id",
    "file_name",
    "relative_path",
    "quality",
    "person_id",
    "use_for_v1",
]

SCHEMA_KEYS = (
    "dataset_source",
    "target_column",
    "metadata_columns",
    "feature_columns",
    "num_features",
    "created_at",
    "notes",
)


def _ml_root(script_path: Path) -> Path:
    # ml/src/dataset/create_feature_schema.py → parents[2] is ml/.
    return script_path.resolve().parents[2]


def main() -> int:
    root = _ml_root(Path(__file__))
    csv_path = root / "data" / "processed" / "features" / "features.csv"
    out_dir = root / "data" / "final"
    schema_path = out_dir / "feature_schema.json"

    if not csv_path.is_file():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        return 1

    df = pd.read_csv(csv_path)
    cols = list(df.columns)

    if TARGET_COLUMN not in cols:
        print(f"ERROR: Missing target column '{TARGET_COLUMN}'. Columns: {cols}", file=sys.stderr)
        return 1

    metadata_present = sorted(c for c in METADATA_CANDIDATES if c in cols)

    non_feature_excluded = set(metadata_present) | {TARGET_COLUMN}

    # Numeric dtype only; boolean flags are not treated as model features in v1.
    feature_columns: list[str] = []
    bool_skipped: list[str] = []
    for c in cols:
        if c in non_feature_excluded:
            continue
        s = df[c]
        if pd.api.types.is_bool_dtype(s):
            bool_skipped.append(c)
            continue
        if pd.api.types.is_numeric_dtype(s):
            feature_columns.append(c)

    dangling = []
    for c in cols:
        if c in non_feature_excluded | set(feature_columns):
            continue
        dangling.append(c)

    if not feature_columns:
        print(
            "ERROR: No numeric feature columns inferred after exclusions.",
            file=sys.stderr,
        )
        return 1

    bad_meta_in_features = sorted(set(metadata_present).intersection(feature_columns))
    if bad_meta_in_features:
        print(
            f"ERROR: Metadata columns wrongly listed as features: {bad_meta_in_features}",
            file=sys.stderr,
        )
        return 1

    if TARGET_COLUMN in feature_columns:
        print("ERROR: Target column wrongly included among features.", file=sys.stderr)
        return 1

    for fc in feature_columns:
        try:
            col = pd.to_numeric(df[fc], errors="coerce")
        except Exception as exc:
            print(f"ERROR: Column {fc!r}: {exc}", file=sys.stderr)
            return 1
        nn = col.notna().sum()
        failed = nn < len(df)
        if failed:
            print(
                f"ERROR: Feature column {fc!r} has non-coercible or missing values.",
                file=sys.stderr,
            )
            return 1

    notes_parts = [
        "Feature columns are all columns that pandas reads as numeric dtype, excluding "
        f"{TARGET_COLUMN!r} and any present metadata candidate fields.",
        "This schema is for Phase 6 dataset finalization; encoding and splitting come later.",
    ]
    if dangling:
        notes_parts.append(
            f"Non-feature, non-metadata columns ignored (typically IDs/paths): {dangling}"
        )
    if bool_skipped:
        notes_parts.append(f"Boolean columns skipped (not numeric features in v1): {bool_skipped}")

    schema = {
        "dataset_source": str(csv_path.resolve().as_posix()),
        "target_column": TARGET_COLUMN,
        "metadata_columns": metadata_present,
        "feature_columns": feature_columns,
        "num_features": len(feature_columns),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "notes": " ".join(notes_parts),
    }

    missing_keys = set(SCHEMA_KEYS) - set(schema)
    extra_keys = set(schema) - set(SCHEMA_KEYS)
    if missing_keys:
        print(f"ERROR: Missing schema keys: {missing_keys}", file=sys.stderr)
        return 1
    if extra_keys:
        print(f"ERROR: Unexpected schema keys: {extra_keys}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    with schema_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print("──────── Feature schema ────────")
    print(f"Source CSV:            {csv_path}")
    print(f"Target column:         {TARGET_COLUMN}")
    print(f"Metadata cols found:   {len(metadata_present)} ({metadata_present or 'none'})")
    print(f"Feature columns:       {len(feature_columns)}")
    print(f"Schema written to:      {schema_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
