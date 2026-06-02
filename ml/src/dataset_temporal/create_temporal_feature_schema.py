"""Phase 5.5 — Write temporal per-frame feature contract (schema only).

Does not build tensors, read pose sequences, or split data.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ML_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = _ML_ROOT / "data" / "final_temporal"
OUTPUT_PATH = OUTPUT_DIR / "temporal_feature_schema.json"

SEQUENCE_LENGTH = 60
EXPECTED_RANK = 3
NUM_FEATURES = 32

FEATURE_GROUPS: dict[str, list[str]] = {
    "JOINT_ANGLE_FEATURES": [
        "lead_elbow_angle",
        "trail_elbow_angle",
        "lead_knee_angle",
        "trail_knee_angle",
        "lead_shoulder_angle",
        "trail_shoulder_angle",
        "lead_wrist_relative_x",
        "hip_rotation_angle",
    ],
    "POSTURE_ALIGNMENT_FEATURES": [
        "trunk_lean",
        "head_over_base_offset",
        "head_to_lead_knee_alignment",
        "shoulder_hip_separation",
        "stance_width",
        "body_center_offset_x",
        "body_center_offset_y",
        "upper_body_balance_offset",
    ],
    "MOTION_DYNAMICS_FEATURES": [
        "lead_wrist_velocity",
        "trail_wrist_velocity",
        "lead_elbow_velocity",
        "trail_elbow_velocity",
        "body_center_velocity",
        "lead_wrist_acceleration",
        "hip_rotation_velocity",
        "frame_motion_energy",
    ],
    "CRICKET_SPECIFIC_TEMPORAL_SIGNALS": [
        "front_foot_commitment_signal",
        "back_foot_loading_signal",
        "weight_transfer_signal",
        "follow_through_height_signal",
        "follow_through_extension_signal",
        "lead_elbow_extension_signal",
        "bat_side_wrist_height_signal",
        "stance_to_swing_progress_signal",
    ],
}


def _build_feature_columns() -> list[str]:
    cols: list[str] = []
    for _group_name, names in FEATURE_GROUPS.items():
        cols.extend(names)
    return cols


def _validate(feature_columns: list[str]) -> None:
    if len(feature_columns) != NUM_FEATURES:
        raise ValueError(
            f"Expected {NUM_FEATURES} features, got {len(feature_columns)}."
        )
    if len(set(feature_columns)) != len(feature_columns):
        dupes = [n for n in feature_columns if feature_columns.count(n) > 1]
        raise ValueError(f"Duplicate feature names: {sorted(set(dupes))}")

    grouped_order: list[str] = []
    for names in FEATURE_GROUPS.values():
        grouped_order.extend(names)
    if feature_columns != grouped_order:
        raise ValueError(
            "feature_columns order does not match concatenated group order."
        )

    if SEQUENCE_LENGTH != 60:
        raise ValueError("sequence_length must be 60.")
    if EXPECTED_RANK != 3:
        raise ValueError("expected_tensor_rank must be 3.")


def main() -> int:
    feature_columns = _build_feature_columns()
    _validate(feature_columns)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    payload = {
        "dataset_type": "temporal_sequence",
        "target_column": "shot_label",
        "expected_tensor_rank": EXPECTED_RANK,
        "expected_shape_format": "[samples, time_steps, feature_dim]",
        "sequence_length": SEQUENCE_LENGTH,
        "num_features": NUM_FEATURES,
        "feature_columns": feature_columns,
        "feature_groups": FEATURE_GROUPS,
        "created_at": created_at,
        "notes": (
            "Version 1 temporal contract: one scalar per feature per frame, "
            f"T={SEQUENCE_LENGTH}, F={NUM_FEATURES}. Rank-3 tensors align with "
            "Phase 7 GRU/BiLSTM inputs [batch, time_steps, feature_dim]. "
            "Implementation of per-frame extractors is a separate step."
        ),
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("──────── Temporal feature schema (Phase 5.5) ────────")
    print(f"output path:        {OUTPUT_PATH}")
    print(f"sequence length:    {SEQUENCE_LENGTH}")
    print(f"number of features: {NUM_FEATURES}")
    print("feature groups:")
    for gname, names in FEATURE_GROUPS.items():
        print(f"  - {gname}: {len(names)} features")
    print("validation passed:  True")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as e:
        print(f"validation failed: {e}", file=sys.stderr)
        raise SystemExit(1)
