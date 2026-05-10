"""Phase 5.8 verification for the feature builder pipeline."""

from __future__ import annotations

import math
import sys

from feature_config import (
    ALL_FEATURES,
    LEFT_ANKLE,
    LEFT_ELBOW,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    LEFT_WRIST,
    NOSE,
    NUM_TOTAL_FEATURES,
    RIGHT_ANKLE,
    RIGHT_ELBOW,
    RIGHT_HIP,
    RIGHT_KNEE,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)
from feature_builder import (
    extract_all_features,
    extract_feature_vector,
    features_to_vector,
)


def _lm(x: float, y: float, z: float = 0.0) -> dict[str, float]:
    return {"x": x, "y": y, "z": z}


def _mock_sequence_three_frames() -> dict:
    """Enough landmarks for joint, posture, motion, and shot extractors."""
    f1 = {
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
        LEFT_ANKLE: _lm(0.44, 0.93),
        RIGHT_ANKLE: _lm(0.56, 0.93),
    }
    f2 = {k: _lm(v["x"] + 0.012, v["y"] + 0.004, v["z"]) for k, v in f1.items()}
    f3 = {k: _lm(v["x"] + 0.008, v["y"] + 0.006, v["z"]) for k, v in f2.items()}

    return {
        "frames": [
            {"landmarks": dict(f1)},
            {"landmarks": dict(f2)},
            {"landmarks": dict(f3)},
        ]
    }


def _is_finite_number(x: object) -> bool:
    if isinstance(x, bool):
        return False
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v)


def main() -> None:
    failures: list[str] = []
    tol = 1e-9
    sequence = _mock_sequence_three_frames()

    print("extract_all_features(..., handedness=right)")
    feats_r = extract_all_features(sequence, handedness="right")

    if list(feats_r.keys()) != list(ALL_FEATURES):
        failures.append(
            "extract_all_features: keys/order must match ALL_FEATURES exactly"
        )
    else:
        print("  PASS — dict keys and order match ALL_FEATURES")

    if len(feats_r) != NUM_TOTAL_FEATURES:
        failures.append(
            f"extract_all_features: expected {NUM_TOTAL_FEATURES} keys, got {len(feats_r)}"
        )
    else:
        print(f"  PASS — exactly {NUM_TOTAL_FEATURES} features")

    dict_r_ok = True
    for name, val in feats_r.items():
        if not _is_finite_number(val):
            failures.append(f"extract_all_features: {name}={val!r} not finite numeric")
            dict_r_ok = False
    if dict_r_ok:
        print("  PASS — all dict values numeric and finite")

    print("\nfeatures_to_vector(features)")
    vec = features_to_vector(feats_r)

    if len(vec) != NUM_TOTAL_FEATURES:
        failures.append(
            f"features_to_vector: length {len(vec)} != {NUM_TOTAL_FEATURES}"
        )
    else:
        print(f"  PASS — vector length is {NUM_TOTAL_FEATURES}")

    for i, x in enumerate(vec):
        if not _is_finite_number(x):
            failures.append(f"features_to_vector: index {i} not finite numeric")

    for i, name in enumerate(ALL_FEATURES):
        a = float(vec[i])
        b = float(feats_r[name])
        if not math.isclose(a, b, rel_tol=0.0, abs_tol=tol):
            failures.append(
                f"vector order: index {i} ({name}) vec={a} dict={b}"
            )
    if not any("vector order" in f or "features_to_vector: index" in f for f in failures):
        print("  PASS — vector values align with ALL_FEATURES order")

    if not any("features_to_vector: index" in f for f in failures):
        print("  PASS — all vector entries numeric and finite")

    print("\nextract_feature_vector vs composition")
    vec_direct = extract_feature_vector(sequence, handedness="right")
    vec_compose = features_to_vector(extract_all_features(sequence, handedness="right"))
    if len(vec_direct) != len(vec_compose) or any(
        not math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tol)
        for a, b in zip(vec_direct, vec_compose)
    ):
        failures.append("extract_feature_vector != features_to_vector(extract_all_features(...))")
    else:
        print("  PASS — extract_feature_vector matches composed pipeline")

    print("\nleft-handed extraction")
    feats_l = extract_all_features(sequence, handedness="left")
    if list(feats_l.keys()) != list(ALL_FEATURES):
        failures.append("left-handed: dict keys/order must match ALL_FEATURES")
    if len(feats_l) != NUM_TOTAL_FEATURES:
        failures.append(f"left dict: expected {NUM_TOTAL_FEATURES} features, got {len(feats_l)}")
    else:
        print(f"  PASS — left-handed dict has {NUM_TOTAL_FEATURES} features (ordered)")

    for name, val in feats_l.items():
        if not _is_finite_number(val):
            failures.append(f"left dict: {name} not finite numeric")

    vec_l = extract_feature_vector(sequence, handedness="left")
    if len(vec_l) != NUM_TOTAL_FEATURES:
        failures.append(f"left vector length != {NUM_TOTAL_FEATURES}")
    else:
        print(f"  PASS — left-handed vector length {NUM_TOTAL_FEATURES}")

    for x in vec_l:
        if not _is_finite_number(x):
            failures.append("left vector has non-finite entry")
            break
    else:
        print("  PASS — left-handed 32 finite values (dict and vector)")

    print()
    if failures:
        print("FAIL results:")
        for msg in failures:
            print(f"  - {msg}")
        sys.exit(1)

    print("Success: feature builder verification passed.")


if __name__ == "__main__":
    main()
