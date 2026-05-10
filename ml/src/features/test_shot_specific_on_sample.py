"""Run shot-specific feature extraction on one real processed pose sequence (Phase 5.7 smoke test)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from feature_config import SHOT_SPECIFIC_FEATURES
from shot_specific_features import extract_shot_specific_features


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

    out = extract_shot_specific_features(sequence, handedness="right")

    print(f"Sample file: {sample_path.name}")
    print(f"Number of frames: {n_frames}")
    print("Shot-specific features:")
    for name in SHOT_SPECIFIC_FEATURES:
        val = out.get(name)
        print(f"  {name}: {val}")

    errors: list[str] = []

    if len(out) != 8:
        errors.append(f"expected 8 features, got {len(out)}")

    if list(out.keys()) != list(SHOT_SPECIFIC_FEATURES):
        errors.append(
            "output keys or order do not match SHOT_SPECIFIC_FEATURES "
            f"(got {list(out.keys())})"
        )

    if set(out.keys()) != set(SHOT_SPECIFIC_FEATURES):
        errors.append("output key set does not match SHOT_SPECIFIC_FEATURES")

    for name, val in out.items():
        if not _is_finite_number(val):
            errors.append(f"{name} is not a finite number: {val!r}")

    # Distances / magnitudes (angle deltas may be negative)
    distance_like_keys = (
        "front_foot_commitment",
        "back_foot_loading",
        "follow_through_height",
        "follow_through_extension",
        "head_to_lead_knee_alignment",
        "weight_transfer_score",
    )
    for key in distance_like_keys:
        if float(out[key]) < 0.0:
            errors.append(f"{key} must be non-negative, got {out[key]}")

    if errors:
        print("\nVerification failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("\nSuccess: shot-specific features extracted from real sample.")


if __name__ == "__main__":
    main()
