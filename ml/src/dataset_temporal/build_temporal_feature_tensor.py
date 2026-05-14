"""Phase 5.5 Step 4 — Build full rank-3 temporal feature tensor from pose sequences.

Reads metadata and fixed-length pose JSON; writes X_sequence.npy and CSV sidecars.
Does not encode labels, split data, or train models.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

_ML_SRC = Path(__file__).resolve().parents[1]
_FEATURES_DIR = _ML_SRC / "features"
if str(_FEATURES_DIR) not in sys.path:
    sys.path.insert(0, str(_FEATURES_DIR))

from temporal_frame_features import (  # noqa: E402
    compute_temporal_frame_features,
    features_to_vector,
    load_temporal_feature_columns,
)

_ML_ROOT = Path(__file__).resolve().parents[2]
POSE_SEQUENCES_DIR = _ML_ROOT / "data" / "processed" / "pose_sequences"
METADATA_CSV = _ML_ROOT / "data" / "annotations" / "metadata.csv"
SCHEMA_PATH = _ML_ROOT / "data" / "final_temporal" / "temporal_feature_schema.json"
OUTPUT_DIR = _ML_ROOT / "data" / "final_temporal"
X_SEQUENCE_PATH = OUTPUT_DIR / "X_sequence.npy"
Y_LABELS_RAW_PATH = OUTPUT_DIR / "y_labels_raw.csv"
INDEX_CSV_PATH = OUTPUT_DIR / "temporal_dataset_index.csv"

REQUIRED_FRAMES = 60
FEATURE_DIM = 32


def _normalize_video_id(raw: object) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    try:
        n = int(float(s))
        return f"{n:03d}"
    except (ValueError, TypeError):
        return s


def _use_for_v1_yes(value: object) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("yes", "y", "true", "1")


def _index_sequences_by_video_id(pose_dir: Path) -> dict[str, list[Path]]:
    by_vid: dict[str, list[Path]] = defaultdict(list)
    for p in sorted(pose_dir.glob("*.json")):
        token = p.name.split("_", 1)[0]
        if token.isdigit():
            vid = f"{int(token):03d}"
        else:
            vid = token
        by_vid[vid].append(p)
    return dict(by_vid)


def _find_sequence_json(
    row: dict[str, str],
    pose_dir: Path,
    by_vid: dict[str, list[Path]],
    all_paths: list[Path],
) -> Path:
    """Match by video_id first; disambiguate or fall back using file_name stem."""
    vid = _normalize_video_id(row.get("video_id"))
    file_name = (row.get("file_name") or "").strip()
    stem = Path(file_name).stem if file_name else ""

    candidates = list(by_vid.get(vid, []))

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1:
        if stem:
            narrowed = [p for p in candidates if stem in p.name]
            if len(narrowed) == 1:
                return narrowed[0]
        exact = pose_dir / f"{vid}_{stem}_sequence.json"
        if exact.is_file():
            return exact
        names = [p.name for p in candidates]
        raise FileNotFoundError(
            f"Ambiguous sequence for video_id={vid!r} ({len(candidates)} files): {names}"
        )

    # No file with this video_id prefix — try stem across all JSON files
    if not stem:
        raise FileNotFoundError(
            f"No sequence JSON starting with {vid!r}_ and no file_name stem for row video_id={vid!r}."
        )
    stem_hits = [p for p in all_paths if stem in p.stem]
    if len(stem_hits) == 1:
        return stem_hits[0]
    if len(stem_hits) == 0:
        raise FileNotFoundError(
            f"No sequence JSON for video_id={vid!r} and no stem match for {stem!r}."
        )
    narrowed = [p for p in stem_hits if p.name.startswith(f"{vid}_")]
    if len(narrowed) == 1:
        return narrowed[0]
    raise FileNotFoundError(
        f"Ambiguous stem={stem!r} for video_id={vid!r}: {[p.name for p in stem_hits]}"
    )


def _load_schema_columns() -> list[str]:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    cols = data.get("feature_columns")
    if not isinstance(cols, list) or len(cols) != FEATURE_DIM:
        raise ValueError("temporal_feature_schema.json must define 32 feature_columns.")
    return [str(c) for c in cols]


def _load_metadata_rows() -> list[dict[str, str]]:
    if not METADATA_CSV.is_file():
        raise FileNotFoundError(f"metadata.csv not found: {METADATA_CSV}")
    rows: list[dict[str, str]] = []
    with METADATA_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("metadata.csv has no header row.")
        for raw in reader:
            row = {k: ("" if v is None else str(v)) for k, v in raw.items()}
            rows.append(row)
    return rows


def _build_sample_tensor(
    frames: list[object],
    feature_columns: list[str],
) -> np.ndarray:
    if len(frames) != REQUIRED_FRAMES:
        raise ValueError(f"Expected {REQUIRED_FRAMES} frames, got {len(frames)}.")
    out = np.zeros((REQUIRED_FRAMES, FEATURE_DIM), dtype=np.float64)
    for t in range(REQUIRED_FRAMES):
        cur = frames[t]
        if not isinstance(cur, dict):
            raise TypeError(f"Frame {t} must be an object/dict.")
        prev = frames[t - 1] if t > 0 else None
        prev_dict = prev if isinstance(prev, dict) else None
        feats = compute_temporal_frame_features(
            cur,
            previous_frame=prev_dict,
            frame_index=t,
            sequence_length=REQUIRED_FRAMES,
        )
        vec = features_to_vector(feats, feature_columns)
        out[t, :] = vec
    return out


def _validate_tensor(X: np.ndarray, n_labels: int, n_index: int) -> list[str]:
    errs: list[str] = []
    if X.ndim != 3:
        errs.append(f"X_sequence must be rank 3, got ndim={X.ndim}")
    if X.shape[1] != REQUIRED_FRAMES:
        errs.append(f"Expected time dim {REQUIRED_FRAMES}, got {X.shape[1]}")
    if X.shape[2] != FEATURE_DIM:
        errs.append(f"Expected feature dim {FEATURE_DIM}, got {X.shape[2]}")
    if not np.isfinite(X).all():
        errs.append("X_sequence contains non-finite values")
    if X.shape[0] != n_labels:
        errs.append(f"Label count {n_labels} != X_sequence.shape[0] {X.shape[0]}")
    if X.shape[0] != n_index:
        errs.append(f"Index rows {n_index} != X_sequence.shape[0] {X.shape[0]}")
    return errs


def main() -> int:
    print("──────── build_temporal_feature_tensor (Phase 5.5 Step 4) ────────\n")

    try:
        all_rows = _load_metadata_rows()
        selected = [r for r in all_rows if _use_for_v1_yes(r.get("use_for_v1"))]
        feature_columns = _load_schema_columns()
        loaded = load_temporal_feature_columns()
        if loaded != feature_columns:
            raise ValueError("Schema file feature_columns disagree with temporal_frame_features loader.")
    except (OSError, ValueError, FileNotFoundError) as e:
        print(f"FAIL: {e}")
        return 1

    if not POSE_SEQUENCES_DIR.is_dir():
        print(f"FAIL: pose sequences directory not found: {POSE_SEQUENCES_DIR}")
        return 1

    all_paths = sorted(POSE_SEQUENCES_DIR.glob("*.json"))
    by_vid = _index_sequences_by_video_id(POSE_SEQUENCES_DIR)

    tensors: list[np.ndarray] = []
    labels: list[str] = []
    index_rows: list[dict[str, str]] = []

    for row_index, row in enumerate(selected):
        try:
            seq_path = _find_sequence_json(row, POSE_SEQUENCES_DIR, by_vid, all_paths)
        except FileNotFoundError as e:
            print(f"FAIL: row_index={row_index} video_id={row.get('video_id')!r}: {e}")
            return 1

        with seq_path.open(encoding="utf-8") as f:
            doc = json.load(f)
        frames = doc.get("frames")
        if not isinstance(frames, list) or len(frames) != REQUIRED_FRAMES:
            print(
                f"FAIL: {seq_path.name}: expected exactly {REQUIRED_FRAMES} frames, "
                f"got {len(frames) if isinstance(frames, list) else type(frames).__name__}."
            )
            return 1

        try:
            sample = _build_sample_tensor(frames, feature_columns)
        except (TypeError, ValueError) as e:
            print(f"FAIL: {seq_path.name}: {e}")
            return 1

        tensors.append(sample)
        shot = (row.get("shot_label") or "").strip()
        labels.append(shot)

        rel_seq = seq_path.resolve().relative_to(_ML_ROOT.resolve())
        index_rows.append(
            {
                "row_index": str(row_index),
                "video_id": str(row.get("video_id", "")).strip(),
                "file_name": str(row.get("file_name", "")).strip(),
                "source_file": str(row.get("relative_path", "")).strip(),
                "shot_label": shot,
                "sequence_path": rel_seq.as_posix(),
            }
        )

    X_sequence = np.stack(tensors, axis=0).astype(np.float32, copy=False)
    n_samples = X_sequence.shape[0]

    val_errs = _validate_tensor(X_sequence, len(labels), len(index_rows))
    if val_errs:
        print("FAIL: post-build validation:")
        for e in val_errs:
            print(f"  - {e}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(X_SEQUENCE_PATH, X_sequence)

    with Y_LABELS_RAW_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["row_index", "shot_label"])
        w.writeheader()
        for i, lab in enumerate(labels):
            w.writerow({"row_index": str(i), "shot_label": lab})

    idx_fields = ["row_index", "video_id", "file_name", "source_file", "shot_label", "sequence_path"]
    with INDEX_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=idx_fields)
        w.writeheader()
        for r in index_rows:
            w.writerow(r)

    dist = Counter(labels)
    print(f"metadata rows loaded : {len(all_rows)}")
    print(f"samples used (v1)    : {n_samples}")
    print(f"X_sequence shape       : {tuple(X_sequence.shape)}")
    print("class distribution     :")
    for cls_name in sorted(dist.keys()):
        print(f"  - {cls_name}: {dist[cls_name]}")
    print("output paths           :")
    print(f"  - {X_SEQUENCE_PATH}")
    print(f"  - {Y_LABELS_RAW_PATH}")
    print(f"  - {INDEX_CSV_PATH}")
    print("validation passed      : True")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
