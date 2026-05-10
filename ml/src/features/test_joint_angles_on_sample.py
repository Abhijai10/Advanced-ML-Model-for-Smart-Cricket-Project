"""Run joint angle extraction on one real processed pose sequence (Phase 5.4 smoke test)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from feature_config import JOINT_ANGLE_FEATURES
from joint_angle_features import extract_joint_angle_features


def _find_first_pose_json(pose_dir: Path) -> Path | None:
    if not pose_dir.is_dir():
        return None
    files = sorted(pose_dir.glob("*.json"))
    return files[0] if files else None


def _is_finite_number(x: object) -> bool:
    if isinstance(x, bool):
        return False
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v)


def main() -> None:
    # __file__ is ml/src/features/<script>.py → parent is features/; parents[1] is ml/.
    script_dir = Path(__file__).resolve().parent
    ml_root = script_dir.parents[1]
    pose_dir = ml_root / "data" / "processed" / "pose_sequences"

    sample_path = _find_first_pose_json(pose_dir)
    if sample_path is None:
        print(f"No .json files found under: {pose_dir}")
        sys.exit(1)

    with sample_path.open(encoding="utf-8") as f:
        sequence = json.load(f)

    frames = sequence.get("frames")
    n_frames = len(frames) if isinstance(frames, list) else 0

    out = extract_joint_angle_features(sequence, handedness="right")

    print(f"Sample file: {sample_path.name}")
    print(f"Number of frames: {n_frames}")
    print("Joint angle features:")
    for name in JOINT_ANGLE_FEATURES:
        val = out.get(name)
        print(f"  {name}: {val}")

    errors: list[str] = []

    if len(out) != 8:
        errors.append(f"expected 8 features, got {len(out)}")

    if set(out.keys()) != set(JOINT_ANGLE_FEATURES):
        errors.append("output keys do not match JOINT_ANGLE_FEATURES")

    for name, val in out.items():
        if not _is_finite_number(val):
            errors.append(f"{name} is not a finite number: {val!r}")

    elbow_knee_keys = (
        "lead_elbow_angle_mean",
        "lead_elbow_angle_min",
        "trail_elbow_angle_mean",
        "lead_knee_angle_mean",
        "lead_knee_angle_min",
        "trail_knee_angle_mean",
    )
    for key in elbow_knee_keys:
        v = float(out[key])
        if not (0.0 <= v <= 180.0):
            errors.append(f"{key}={v} not in [0, 180]")

    for key in ("shoulder_rotation_angle_mean", "hip_rotation_angle_mean"):
        v = out[key]
        if not _is_finite_number(v):
            errors.append(f"{key} is not finite: {v!r}")

    if errors:
        print("\nVerification failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("\nSuccess: joint angle features extracted from real sample.")


if __name__ == "__main__":
    main()
