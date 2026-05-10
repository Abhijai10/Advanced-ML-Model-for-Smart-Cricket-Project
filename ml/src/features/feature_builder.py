"""Central feature builder: one place to turn pose sequences into the 32-D blueprint vector (Phase 5.8).

A **feature dictionary** maps each feature **name** (string) to a scalar value. A **feature vector**
is just those same numbers packed into a fixed-length **list of floats**, one slot per name.

**Why order matters:** models and saved tensors only see column 0 … column 31. They do not carry names.
``ALL_FEATURES`` in ``feature_config.py`` fixes the contract: index *i* always means the same biomechanical
quantity everywhere (training CSV, NumPy array, inference REST JSON, etc.). If training and inference
use different orders or miss a slot, silently misaligned predictions are guaranteed—this module routes
everything through one ordered path to prevent that.
"""

from __future__ import annotations

import math
from typing import Any

from feature_config import ALL_FEATURES, NUM_TOTAL_FEATURES
from joint_angle_features import extract_joint_angle_features
from motion_features import extract_motion_features
from posture_features import extract_posture_features
from shot_specific_features import extract_shot_specific_features


def extract_all_features(sequence: dict, handedness: str = "right") -> dict[str, float]:
    """Run joint, posture, motion, and shot extractors and merge into one ordered map.

    Returns one dictionary whose keys appear in **exactly** the same order as ``ALL_FEATURES``.
    Raises ``ValueError`` if any expected key is missing or if extra keys appear.
    """
    joint = extract_joint_angle_features(sequence, handedness=handedness)
    posture = extract_posture_features(sequence)
    motion = extract_motion_features(sequence, handedness=handedness)
    shot = extract_shot_specific_features(sequence, handedness=handedness)

    merged: dict[str, float] = {}
    merged.update(joint)
    merged.update(posture)
    merged.update(motion)
    merged.update(shot)

    if len(merged) != NUM_TOTAL_FEATURES:
        raise ValueError(
            f"Expected {NUM_TOTAL_FEATURES} features after merge, got {len(merged)}. "
            f"Keys: {sorted(merged.keys())}"
        )

    if set(merged.keys()) != set(ALL_FEATURES):
        missing = set(ALL_FEATURES) - set(merged.keys())
        extra = set(merged.keys()) - set(ALL_FEATURES)
        raise ValueError(
            "Merged feature keys do not match ALL_FEATURES. "
            f"Missing: {sorted(missing)}. Extra: {sorted(extra)}."
        )

    # Enforce blueprint order (dict order is guaranteed in modern Python).
    return {name: float(merged[name]) for name in ALL_FEATURES}


def features_to_vector(features: dict[str, Any]) -> list[float]:
    """Pack ``features`` into ``list[float]`` following ``ALL_FEATURES`` order."""
    if len(features) != NUM_TOTAL_FEATURES:
        raise ValueError(
            f"Expected {NUM_TOTAL_FEATURES} entries in features dict, got {len(features)}."
        )

    vec: list[float] = []
    for name in ALL_FEATURES:
        if name not in features:
            raise KeyError(
                f"Missing feature {name!r}; cannot build vector of length {NUM_TOTAL_FEATURES}."
            )
        value = features[name]
        if isinstance(value, bool):
            raise TypeError(f"Feature {name!r} is boolean (invalid numeric feature).")
        try:
            x = float(value)
        except (TypeError, ValueError) as e:
            raise TypeError(f"Feature {name!r} is not numeric: {value!r}") from e
        vec.append(x)

    if len(vec) != NUM_TOTAL_FEATURES:
        raise ValueError(
            f"Internal error: vector length {len(vec)} != {NUM_TOTAL_FEATURES}."
        )
    return vec


def extract_feature_vector(sequence: dict, handedness: str = "right") -> list[float]:
    """End-to-end: pose sequence → ordered 32-float vector for model I/O."""
    return features_to_vector(extract_all_features(sequence, handedness=handedness))


def _lm(x: float, y: float, z: float = 0.0) -> dict[str, float]:
    return {"x": x, "y": y, "z": z}


def _smoke_test() -> None:
    """Two frames with landmarks needed by all four extractors."""
    from feature_config import (
        LEFT_ANKLE,
        LEFT_ELBOW,
        LEFT_HIP,
        LEFT_KNEE,
        LEFT_SHOULDER,
        LEFT_WRIST,
        NOSE,
        RIGHT_ANKLE,
        RIGHT_ELBOW,
        RIGHT_HIP,
        RIGHT_KNEE,
        RIGHT_SHOULDER,
        RIGHT_WRIST,
    )

    base = {
        NOSE: _lm(0.5, 0.30),
        LEFT_SHOULDER: _lm(0.44, 0.42),
        RIGHT_SHOULDER: _lm(0.56, 0.42),
        LEFT_ELBOW: _lm(0.45, 0.50),
        LEFT_WRIST: _lm(0.48, 0.55),
        RIGHT_ELBOW: _lm(0.55, 0.50),
        RIGHT_WRIST: _lm(0.52, 0.54),
        LEFT_HIP: _lm(0.45, 0.64),
        RIGHT_HIP: _lm(0.55, 0.64),
        LEFT_KNEE: _lm(0.46, 0.77),
        RIGHT_KNEE: _lm(0.54, 0.77),
        LEFT_ANKLE: _lm(0.45, 0.93),
        RIGHT_ANKLE: _lm(0.55, 0.93),
    }
    f2 = {k: _lm(v["x"] + 0.01, v["y"] + 0.005, v["z"]) for k, v in base.items()}

    mock = {"frames": [{"landmarks": dict(base)}, {"landmarks": dict(f2)}]}

    feats = extract_all_features(mock, handedness="right")
    if len(feats) != NUM_TOTAL_FEATURES:
        raise AssertionError(f"expected {NUM_TOTAL_FEATURES} keys, got {len(feats)}")

    vec = features_to_vector(feats)
    if len(vec) != NUM_TOTAL_FEATURES:
        raise AssertionError(f"expected vector length {NUM_TOTAL_FEATURES}, got {len(vec)}")

    alt = extract_feature_vector(mock, handedness="right")
    if alt != vec:
        raise AssertionError("extract_feature_vector disagrees with extract_all_features path")

    for i, v in enumerate(vec):
        if isinstance(v, bool):
            raise AssertionError(f"index {i} is bool: {v!r}")
        if not math.isfinite(float(v)):
            raise AssertionError(f"index {i} not finite: {v!r}")

    print("Success: feature builder smoke test passed.")


if __name__ == "__main__":
    _smoke_test()
