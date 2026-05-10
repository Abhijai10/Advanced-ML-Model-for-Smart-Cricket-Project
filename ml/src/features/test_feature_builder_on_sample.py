"""Run the full 32-feature builder on one real processed pose sequence (Phase 5.8 smoke test)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from feature_builder import extract_all_features, extract_feature_vector
from feature_config import ALL_FEATURES, NUM_TOTAL_FEATURES


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

    feats = extract_all_features(sequence, handedness="right")
    vec = extract_feature_vector(sequence, handedness="right")

    print(f"Sample file: {sample_path.name}")
    print(f"Number of frames: {n_frames}")
    print(f"Total feature count: {len(feats)}")
    print(f"Vector length: {len(vec)}")
    print("Features (ALL_FEATURES order):")
    for name in ALL_FEATURES:
        val = feats.get(name)
        print(f"  {name}: {val}")

    errors: list[str] = []

    if len(feats) != NUM_TOTAL_FEATURES:
        errors.append(f"expected {NUM_TOTAL_FEATURES} features, got {len(feats)}")

    if list(feats.keys()) != list(ALL_FEATURES):
        errors.append(
            "feature dict keys/order do not match ALL_FEATURES "
            f"(got {list(feats.keys())[:5]}...)"
        )

    if len(vec) != NUM_TOTAL_FEATURES:
        errors.append(f"expected vector length {NUM_TOTAL_FEATURES}, got {len(vec)}")

    for name, val in feats.items():
        if not _is_finite_number(val):
            errors.append(f"dict feature {name} is not a finite number: {val!r}")

    for i, x in enumerate(vec):
        if not _is_finite_number(x):
            errors.append(f"vector[{i}] is not a finite number: {x!r}")

    if errors:
        print("\nVerification failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("\nSuccess: full 32-feature vector extracted from real sample.")


if __name__ == "__main__":
    main()
