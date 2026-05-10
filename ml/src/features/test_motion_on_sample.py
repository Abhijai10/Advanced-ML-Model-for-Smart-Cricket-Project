"""Run motion feature extraction on one real processed pose sequence (Phase 5.6 smoke test)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from feature_config import MOTION_FEATURES
from motion_features import extract_motion_features


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

    out = extract_motion_features(sequence, handedness="right")

    print(f"Sample file: {sample_path.name}")
    print(f"Number of frames: {n_frames}")
    print("Motion features:")
    for name in MOTION_FEATURES:
        val = out.get(name)
        print(f"  {name}: {val}")

    errors: list[str] = []

    if len(out) != 8:
        errors.append(f"expected 8 features, got {len(out)}")

    if list(out.keys()) != list(MOTION_FEATURES):
        errors.append(
            "output keys or order do not match MOTION_FEATURES "
            f"(got {list(out.keys())})"
        )

    if set(out.keys()) != set(MOTION_FEATURES):
        errors.append("output key set does not match MOTION_FEATURES")

    for name, val in out.items():
        if not _is_finite_number(val):
            errors.append(f"{name} is not a finite number: {val!r}")

    velocity_keys = (
        "lead_wrist_velocity_mean",
        "lead_wrist_velocity_max",
        "trail_wrist_velocity_mean",
        "trail_wrist_velocity_max",
        "body_center_velocity_mean",
        "body_center_velocity_max",
        "shoulder_rotation_velocity_mean",
    )
    for key in velocity_keys:
        if float(out[key]) < 0.0:
            errors.append(f"{key} must be non-negative, got {out[key]}")

    if float(out["motion_energy_total"]) < 0.0:
        errors.append(
            f"motion_energy_total must be non-negative, got {out['motion_energy_total']}"
        )

    if errors:
        print("\nVerification failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("\nSuccess: motion features extracted from real sample.")


if __name__ == "__main__":
    main()
