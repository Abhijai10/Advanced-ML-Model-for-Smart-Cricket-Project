"""Build a tabular CSV of 32 biomechanical features for every pose sequence JSON (Phase 5.9).

Reads pose clips from ``ml/data/processed/pose_sequences/`` and writes
``features.csv`` plus a small summary JSON beside it. Uses the same extractor as
training will use later (**right-handed mapping for every clip in v1**).
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

from feature_config import ALL_FEATURES, NUM_TOTAL_FEATURES
from feature_builder import extract_all_features


def infer_shot_label(filename: str) -> str:
    """Guess shot type from the filename stem (underscore-separated tokens)."""
    name = Path(filename).name.lower()
    if "defensive_shot" in name:
        return "defensive_shot"
    if "cover_drive" in name:
        return "cover_drive"
    if "pull_shot" in name:
        return "pull_shot"
    if "sweep_shot" in name:
        return "sweep_shot"
    return "unknown"


def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    try:
        x = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(x)


def _validate_features(feats: dict[str, float], source_hint: str) -> None:
    """Raise ValueError if the dict does not contain 32 finite values."""
    if len(feats) != NUM_TOTAL_FEATURES:
        raise ValueError(
            f"{source_hint}: expected {NUM_TOTAL_FEATURES} features, got {len(feats)}"
        )

    missing = [n for n in ALL_FEATURES if n not in feats]
    if missing:
        raise ValueError(f"{source_hint}: missing features: {missing[:5]}...")

    for name in ALL_FEATURES:
        val = feats[name]
        if not _is_finite_number(val):
            raise ValueError(
                f"{source_hint}: feature {name!r} is not a finite float: {val!r}"
            )


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    ml_root = script_dir.parents[1]
    pose_dir = ml_root / "data" / "processed" / "pose_sequences"
    out_dir = ml_root / "data" / "processed" / "features"
    csv_path = out_dir / "features.csv"
    summary_path = out_dir / "feature_dataset_summary.json"

    json_files = sorted(pose_dir.glob("*.json"))
    total_found = len(json_files)

    if total_found == 0:
        print(f"No .json files under {pose_dir}")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    header = ["sample_id", "source_file", "shot_label", *ALL_FEATURES]

    rows: list[list[float | str]] = []
    failed: list[dict[str, str]] = []

    print(f"Found {total_found} JSON file(s). Extracting features...")
    for i, path in enumerate(json_files, start=1):
        rel_src = path.relative_to(ml_root).as_posix()
        sample_id = path.stem
        shot_label = infer_shot_label(path.name)

        try:
            with path.open(encoding="utf-8") as f:
                sequence = json.load(f)
            feats = extract_all_features(sequence, handedness="right")
            _validate_features(feats, rel_src)

            row: list[float | str] = [
                sample_id,
                rel_src,
                shot_label,
                *[float(feats[name]) for name in ALL_FEATURES],
            ]
            if len(row) != 3 + NUM_TOTAL_FEATURES:
                raise RuntimeError(f"Bad row length: {len(row)}")
            rows.append(row)

            print(f"  [{i}/{total_found}] OK  {path.name}")

        except Exception as e:
            msg = str(e)
            failed.append({"file": rel_src, "error": msg})
            print(f"  [{i}/{total_found}] FAIL {path.name}: {msg}")

    success_count = len(rows)
    fail_count = len(failed)

    with csv_path.open("w", encoding="utf-8", newline="") as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow(header)
        writer.writerows(rows)

    summary = {
        "total_files_found": total_found,
        "successfully_processed": success_count,
        "failed_files": failed,
        "output_csv_path": csv_path.resolve().as_posix(),
        "num_features": NUM_TOTAL_FEATURES,
        "feature_columns": list(ALL_FEATURES),
    }

    with summary_path.open("w", encoding="utf-8") as fj:
        json.dump(summary, fj, indent=2)

    # Validation: every written row parses back with 35 fields and finite feature cells
    with csv_path.open(encoding="utf-8", newline="") as fchk:
        reader = csv.reader(fchk)
        table = list(reader)
    if len(table) != success_count + 1:
        print(
            f"ERROR: expected {success_count + 1} CSV lines (header + rows), "
            f"got {len(table)}",
            file=sys.stderr,
        )
        sys.exit(1)
    hdr, *data_rows = table
    expected_hdr = header
    if hdr != expected_hdr:
        print("ERROR: CSV header does not match expected columns.", file=sys.stderr)
        sys.exit(1)
    for ri, cols in enumerate(data_rows):
        if len(cols) != 3 + NUM_TOTAL_FEATURES:
            print(f"ERROR: row {ri} wrong column count: {len(cols)}", file=sys.stderr)
            sys.exit(1)
        for j, raw in enumerate(cols[3:], start=0):
            if not _is_finite_number(float(raw)):
                print(
                    f"ERROR: row {ri} column {ALL_FEATURES[j]} not finite: {raw!r}",
                    file=sys.stderr,
                )
                sys.exit(1)

    assert success_count + fail_count == total_found

    print("")
    print("──── Feature dataset build finished ────")
    print(f"  Total files found:     {total_found}")
    print(f"  Successfully processed: {success_count}")
    print(f"  Failed:                {fail_count}")
    print(f"  CSV path:               {csv_path}")
    print(f"  Summary path:           {summary_path}")


if __name__ == "__main__":
    main()
