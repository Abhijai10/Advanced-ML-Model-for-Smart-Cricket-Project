"""Step 3 verification: temporal_frame_features on one real pose sequence JSON.

Does not build tensors or splits. Read-only on inputs.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

_FEAT_DIR = Path(__file__).resolve().parent
if str(_FEAT_DIR) not in sys.path:
    sys.path.insert(0, str(_FEAT_DIR))

from temporal_frame_features import (  # noqa: E402
    compute_temporal_frame_features,
    features_to_vector,
    load_temporal_feature_columns,
    validate_features_dict,
)

_ML_ROOT = Path(__file__).resolve().parents[2]
POSE_SEQUENCES_DIR = _ML_ROOT / "data" / "processed" / "pose_sequences"
SCHEMA_PATH = _ML_ROOT / "data" / "final_temporal" / "temporal_feature_schema.json"

MOTION_KEYS = (
    "lead_wrist_velocity",
    "trail_wrist_velocity",
    "lead_elbow_velocity",
    "trail_elbow_velocity",
    "body_center_velocity",
    "shoulder_rotation_velocity",
    "hip_rotation_velocity",
    "frame_motion_energy",
)


def _pick_sequence_json() -> Path:
    if not POSE_SEQUENCES_DIR.is_dir():
        raise FileNotFoundError(f"Pose sequences directory not found: {POSE_SEQUENCES_DIR}")
    candidates = sorted(POSE_SEQUENCES_DIR.glob("*.json"))
    if not candidates:
        raise FileNotFoundError(f"No JSON files in {POSE_SEQUENCES_DIR}")
    return candidates[0]


def _load_schema_columns() -> list[str]:
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    cols = data.get("feature_columns")
    if not isinstance(cols, list) or len(cols) != 32:
        raise ValueError("temporal_feature_schema.json must contain feature_columns (length 32).")
    return [str(c) for c in cols]


def _all_numeric_finite(d: dict[str, float]) -> bool:
    for k, v in d.items():
        if isinstance(v, bool):
            return False
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(fv):
            return False
    return True


def _keys_match_schema(keys: list[str], schema_cols: list[str]) -> bool:
    return keys == schema_cols


def main() -> int:
    print("──────── verify_temporal_frame_features (Step 3) ────────\n")

    failures: list[str] = []

    try:
        sample_path = _pick_sequence_json()
        schema_cols = _load_schema_columns()
    except (OSError, ValueError, FileNotFoundError) as e:
        print(f"FAIL: {e}")
        return 1

    with sample_path.open(encoding="utf-8") as f:
        sequence_doc = json.load(f)

    frames = sequence_doc.get("frames")
    if not isinstance(frames, list) or len(frames) < 2:
        n = len(frames) if isinstance(frames, list) else "n/a"
        print(f"FAIL: need at least 2 frames in 'frames', got type={type(frames).__name__} len={n}")
        return 1

    seq_len = len(frames)
    frame0 = frames[0]
    frame1 = frames[1]

    if not isinstance(frame0, dict) or not isinstance(frame1, dict):
        print("FAIL: frame 0 and frame 1 must be objects.")
        return 1

    loaded_cols = load_temporal_feature_columns()
    if loaded_cols != schema_cols:
        failures.append("load_temporal_feature_columns() != schema file feature_columns")

    feats0 = compute_temporal_frame_features(frame0, None, frame_index=0, sequence_length=seq_len)
    feats1 = compute_temporal_frame_features(
        frame1, frame0, frame_index=1, sequence_length=seq_len
    )

    # --- Validation ---
    for label, feats in (("frame 0", feats0), ("frame 1", feats1)):
        try:
            validate_features_dict(feats, schema_cols)
        except (TypeError, ValueError) as e:
            failures.append(f"{label}: validate_features_dict: {e}")

    if len(feats0) != 32 or len(feats1) != 32:
        failures.append(f"expected 32 features per frame, got {len(feats0)} / {len(feats1)}")

    keys0 = list(feats0.keys())
    keys1 = list(feats1.keys())
    schema_match = _keys_match_schema(keys0, schema_cols) and _keys_match_schema(keys1, schema_cols)
    if not schema_match:
        failures.append("feature key order does not match schema")

    all_finite0 = _all_numeric_finite(feats0)
    all_finite1 = _all_numeric_finite(feats1)
    all_finite = all_finite0 and all_finite1
    if not all_finite:
        failures.append("non-finite or non-numeric feature value detected")

    try:
        vec0 = features_to_vector(feats0, schema_cols)
        vec1 = features_to_vector(feats1, schema_cols)
    except (TypeError, ValueError) as e:
        failures.append(f"features_to_vector: {e}")
        vec0 = vec1 = None

    if vec0 is not None and (vec0.shape != (32,) or vec1.shape != (32,)):  # type: ignore[union-attr]
        failures.append(f"output vector shape expected (32,), got {vec0.shape}, {vec1.shape}")  # type: ignore[union-attr]

    # --- Report ---
    print(f"sample file path : {sample_path}")
    print(f"sequence length  : {seq_len}")
    print(f"feature count    : {len(feats0)}")
    print(f"schema match     : {schema_match}")
    print(f"all finite       : {all_finite}")
    print()
    print("First 5 feature names + values (frame 0):")
    for name in schema_cols[:5]:
        print(f"  {name:<40} {feats0[name]:.6f}")
    print()
    print("Motion feature examples (frame 1, with previous_frame=frame 0):")
    for name in MOTION_KEYS:
        print(f"  {name:<40} {feats1[name]:.6f}")

    print()
    print("─" * 58)
    if failures:
        print("RESULT: FAIL")
        for msg in failures:
            print(f"  - {msg}")
        print("─" * 58)
        return 1

    print("RESULT: PASS")
    print("  All checks: 32 features, schema order, numeric finite values, vectors (32,).")
    print("─" * 58)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
