"""Phase 5.5 verification for posture feature extraction."""

from __future__ import annotations

import math
import sys

from feature_config import (
    LEFT_ANKLE,
    LEFT_HIP,
    LEFT_SHOULDER,
    NOSE,
    POSTURE_FEATURES,
    RIGHT_ANKLE,
    RIGHT_HIP,
    RIGHT_SHOULDER,
)
from posture_features import extract_posture_features


def _lm(x: float, y: float, z: float = 0.0) -> dict[str, float]:
    return {"x": x, "y": y, "z": z}


def _mock_sequence_three_frames() -> dict:
    """Hips drift (non-zero pelvic shift), nose moves frame-to-frame, feet stay apart."""
    # Frame 1 — baseline
    f1 = {
        NOSE: _lm(0.5, 0.35),
        LEFT_SHOULDER: _lm(0.46, 0.45),
        RIGHT_SHOULDER: _lm(0.54, 0.45),
        LEFT_HIP: _lm(0.46, 0.64),
        RIGHT_HIP: _lm(0.54, 0.64),
        LEFT_ANKLE: _lm(0.44, 0.90),
        RIGHT_ANKLE: _lm(0.56, 0.90),
    }
    # Frame 2 — hips translate; nose moves slightly
    f2 = {
        NOSE: _lm(0.52, 0.345),
        LEFT_SHOULDER: _lm(0.47, 0.452),
        RIGHT_SHOULDER: _lm(0.55, 0.452),
        LEFT_HIP: _lm(0.48, 0.645),
        RIGHT_HIP: _lm(0.56, 0.645),
        LEFT_ANKLE: _lm(0.45, 0.901),
        RIGHT_ANKLE: _lm(0.57, 0.901),
    }
    # Frame 3 — hips translate again (shift x and y); nose moves again
    f3 = {
        NOSE: _lm(0.535, 0.34),
        LEFT_SHOULDER: _lm(0.49, 0.455),
        RIGHT_SHOULDER: _lm(0.57, 0.455),
        LEFT_HIP: _lm(0.52, 0.67),
        RIGHT_HIP: _lm(0.60, 0.67),
        LEFT_ANKLE: _lm(0.47, 0.902),
        RIGHT_ANKLE: _lm(0.59, 0.902),
    }
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


def _check_blueprint_keys(out: dict, label: str, failures: list[str]) -> None:
    if list(out.keys()) != list(POSTURE_FEATURES):
        failures.append(
            f"{label}: key order or set mismatch; got {list(out.keys())}, "
            f"expected {list(POSTURE_FEATURES)}"
        )
    if len(out) != 8:
        failures.append(f"{label}: expected 8 features, got {len(out)}")
    if set(out.keys()) != set(POSTURE_FEATURES):
        failures.append(f"{label}: key set does not match POSTURE_FEATURES")


def _check_all_numeric_finite(out: dict, label: str, failures: list[str]) -> None:
    for name, val in out.items():
        if not _is_finite_number(val):
            failures.append(f"{label}: {name}={val!r} is not a finite number")


def main() -> None:
    failures: list[str] = []
    sequence = _mock_sequence_three_frames()

    print("extract_posture_features(mock sequence, 3 frames)")
    out = extract_posture_features(sequence)
    n0 = len(failures)
    _check_blueprint_keys(out, "posture", failures)
    _check_all_numeric_finite(out, "posture", failures)
    if len(failures) == n0:
        print(
            "  PASS — keys match POSTURE_FEATURES (order + count), all values finite"
        )
    else:
        print("  FAIL — blueprint key or numeric checks (see below)")

    sx = float(out["body_center_shift_x"])
    sy = float(out["body_center_shift_y"])
    if sx == 0.0:
        failures.append("body_center_shift_x should be non-zero when hip center moves")
    else:
        print(f"  PASS — body_center_shift_x non-zero ({sx})")

    if sy == 0.0:
        failures.append("body_center_shift_y should be non-zero when hip center moves")
    else:
        print(f"  PASS — body_center_shift_y non-zero ({sy})")

    sw = float(out["stance_width_mean"])
    if sw <= 0.0:
        failures.append(f"stance_width_mean should be positive, got {sw}")
    else:
        print(f"  PASS — stance_width_mean positive ({sw})")

    hs = float(out["head_stability"])
    if hs <= 0.0:
        failures.append(f"head_stability should be positive when nose moves, got {hs}")
    else:
        print(f"  PASS — head_stability positive ({hs})")

    print()
    if failures:
        print("FAIL results:")
        for msg in failures:
            print(f"  - {msg}")
        sys.exit(1)

    print("Success: posture feature verification passed.")


if __name__ == "__main__":
    main()
