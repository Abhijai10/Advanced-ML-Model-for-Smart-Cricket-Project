"""Read-only audit for player identity overlap across temporal dataset splits.

The deterministic 56/12/12 split is sample-stratified. This script checks exact
sample leakage separately from person-identity overlap so Phase 8 reports do not
overclaim unseen-player generalization.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

_ML_ROOT = Path(__file__).resolve().parents[2]
METADATA_CSV = _ML_ROOT / "data" / "annotations" / "metadata.csv"
FINAL_TEMPORAL_DIR = _ML_ROOT / "data" / "final_temporal"
SPLIT_PATHS = {
    "train": FINAL_TEMPORAL_DIR / "train_temporal_index.csv",
    "validation": FINAL_TEMPORAL_DIR / "val_temporal_index.csv",
    "test": FINAL_TEMPORAL_DIR / "test_temporal_index.csv",
}


def _normalize_video_id(value: object) -> str:
    raw = str(value).strip()
    if raw == "":
        return ""
    try:
        return f"{int(float(raw)):03d}"
    except ValueError:
        return raw


def _load_metadata() -> pd.DataFrame:
    if not METADATA_CSV.is_file():
        raise FileNotFoundError(f"metadata.csv not found: {METADATA_CSV}")
    df = pd.read_csv(METADATA_CSV, dtype=str).fillna("")
    required = {"video_id", "file_name", "shot_label", "person_id"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"metadata.csv missing required columns: {sorted(missing)}")
    df = df.copy()
    df["join_video_id"] = df["video_id"].map(_normalize_video_id)
    df["join_file_name"] = df["file_name"].astype(str).str.strip()
    join_cols = ["join_video_id", "join_file_name"]
    dupes = df[df.duplicated(join_cols, keep=False)]
    if not dupes.empty:
        raise ValueError(
            "metadata.csv has ambiguous video_id/file_name keys: "
            f"{dupes[join_cols].drop_duplicates().to_dict('records')}"
        )
    return df


def _load_split(name: str, path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"{name} split index not found: {path}")
    df = pd.read_csv(path, dtype=str).fillna("")
    required = {"row_index", "video_id", "file_name", "shot_label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} missing required columns: {sorted(missing)}")
    df = df.copy()
    df["split"] = name
    df["join_video_id"] = df["video_id"].map(_normalize_video_id)
    df["join_file_name"] = df["file_name"].astype(str).str.strip()
    join_cols = ["join_video_id", "join_file_name"]
    dupes = df[df.duplicated(join_cols, keep=False)]
    if not dupes.empty:
        raise ValueError(
            f"{path.name} has duplicate video_id/file_name keys: "
            f"{dupes[join_cols].drop_duplicates().to_dict('records')}"
        )
    return df


def _join_split(split_df: pd.DataFrame, metadata_df: pd.DataFrame) -> pd.DataFrame:
    joined = split_df.merge(
        metadata_df[
            [
                "join_video_id",
                "join_file_name",
                "person_id",
                "shot_label",
                "relative_path",
                "use_for_v1",
            ]
        ],
        on=["join_video_id", "join_file_name"],
        how="left",
        suffixes=("_split", "_metadata"),
        validate="one_to_one",
    )
    if joined["person_id"].isna().any() or (joined["person_id"].astype(str).str.strip() == "").any():
        missing = joined[joined["person_id"].isna() | (joined["person_id"].astype(str).str.strip() == "")]
        raise ValueError(
            "Split rows failed metadata join: "
            f"{missing[['split', 'video_id', 'file_name']].to_dict('records')}"
        )
    mismatched_labels = joined[
        joined["shot_label_split"].astype(str).str.strip()
        != joined["shot_label_metadata"].astype(str).str.strip()
    ]
    if not mismatched_labels.empty:
        raise ValueError(
            "Split shot_label does not match metadata: "
            f"{mismatched_labels[['split', 'video_id', 'file_name']].to_dict('records')}"
        )
    return joined


def _print_person_sets(joined_by_split: dict[str, pd.DataFrame]) -> dict[str, set[str]]:
    person_sets: dict[str, set[str]] = {}
    print("Person IDs per split:")
    for split_name, df in joined_by_split.items():
        persons = set(str(v).strip() for v in df["person_id"].tolist())
        person_sets[split_name] = persons
        print(f"  - {split_name}: {sorted(persons)}")
    print()
    return person_sets


def _print_pairwise_overlap(person_sets: dict[str, set[str]]) -> bool:
    pairs = [
        ("train", "validation"),
        ("train", "test"),
        ("validation", "test"),
    ]
    has_overlap = False
    print("Pairwise person-identity overlap:")
    for left, right in pairs:
        overlap = sorted(person_sets[left] & person_sets[right])
        if overlap:
            has_overlap = True
        print(f"  - {left} vs {right}: {overlap if overlap else 'none'}")
    print()
    return has_overlap


def _print_sample_leakage(joined_by_split: dict[str, pd.DataFrame]) -> bool:
    row_sets = {
        split_name: set(df["row_index"].astype(str).str.strip().tolist())
        for split_name, df in joined_by_split.items()
    }
    pairs = [
        ("train", "validation"),
        ("train", "test"),
        ("validation", "test"),
    ]
    has_leakage = False
    print("Exact sample leakage by row_index:")
    for left, right in pairs:
        overlap = sorted(row_sets[left] & row_sets[right], key=lambda x: int(x))
        if overlap:
            has_leakage = True
        print(f"  - {left} vs {right}: {overlap if overlap else 'none'}")
    print()
    return has_leakage


def _print_counts(joined_by_split: dict[str, pd.DataFrame]) -> None:
    print("Per-person sample counts:")
    for split_name, df in joined_by_split.items():
        counts = Counter(df["person_id"].astype(str).str.strip().tolist())
        print(f"  - {split_name}: {dict(sorted(counts.items()))}")
    print()

    print("Per-person, per-class counts:")
    for split_name, df in joined_by_split.items():
        print(f"  - {split_name}:")
        grouped = (
            df.groupby(["person_id", "shot_label_split"])
            .size()
            .reset_index(name="count")
            .sort_values(["person_id", "shot_label_split"])
        )
        for row in grouped.to_dict("records"):
            print(
                "    "
                f"{row['person_id']} / {row['shot_label_split']}: {int(row['count'])}"
            )
    print()


def main() -> int:
    print("──────── Temporal Player Split Overlap Audit ────────\n")
    try:
        metadata_df = _load_metadata()
        joined_by_split = {
            name: _join_split(_load_split(name, path), metadata_df)
            for name, path in SPLIT_PATHS.items()
        }
    except (OSError, ValueError, FileNotFoundError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    has_sample_leakage = _print_sample_leakage(joined_by_split)
    person_sets = _print_person_sets(joined_by_split)
    has_person_overlap = _print_pairwise_overlap(person_sets)
    _print_counts(joined_by_split)

    if has_sample_leakage:
        print("VERDICT: FAIL — exact sample leakage detected across splits.")
        return 1

    if has_person_overlap:
        print("VERDICT: DEVELOPMENT SPLIT VALID, BUT NOT PERSON-DISJOINT")
        print(
            "Interpretation: exact sample leakage is absent, but at least one "
            "player appears in multiple splits. This is acceptable for "
            "in-distribution development, not proof of unseen-player generalization."
        )
    else:
        print("VERDICT: DEVELOPMENT SPLIT VALID AND PERSON-DISJOINT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
