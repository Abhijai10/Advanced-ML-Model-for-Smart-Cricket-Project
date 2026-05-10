"""Phase 5.6 verification for motion feature extraction."""

from __future__ import annotations

import math
import sys

from feature_config import (
    LEFT_HIP,
    LEFT_SHOULDER,
    LEFT_WRIST,
    MOTION_FEATURES,
    RIGHT_HIP,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)
from motion_features import extract_motion_features


def _lm(x: float, y: float, z: float = 0.0) -> dict[str, float]:
    return {"x": x, "y": y, "z": z}


def _mock_sequence_three_frames() -> dict:
    """Left wrist moves slowly; right wrist moves faster — differs when labeling lead/trail."""
    f1 = {
        LEFT_WRIST: _lm(0.10, 0.50),
        RIGHT_WRIST: _lm(0.90, 0.50),
        LEFT_HIP: _lm(0.40, 0.75),
        RIGHT_HIP: _lm(0.60, 0.75),
        LEFT_SHOULDER: _lm(0.42, 0.45),
        RIGHT_SHOULDER: _lm(0.58, 0.45),
    }
    # Second frame: small hip drift; wrists step with different magnitudes
    f2 = {
        LEFT_WRIST: _lm(0.15, 0.50),
        RIGHT_WRIST: _lm(1.10, 0.50),
        LEFT_HIP: _lm(0.41, 0.75),
        RIGHT_HIP: _lm(0.61, 0.75),
        LEFT_SHOULDER: _lm(0.425, 0.45),
        RIGHT_SHOULDER: _lm(0.585, 0.45),
    }
    f3 = {
        LEFT_WRIST: _lm(0.20, 0.50),
        RIGHT_WRIST: _lm(1.30, 0.50),
        LEFT_HIP: _lm(0.42, 0.75),
        RIGHT_HIP: _lm(0.62, 0.75),
        LEFT_SHOULDER: _lm(0.43, 0.45),
        RIGHT_SHOULDER: _lm(0.59, 0.46),
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


def _check_blueprint(out: dict, label: str, failures: list[str]) -> None:
    if list(out.keys()) != list(MOTION_FEATURES):
        failures.append(
            f"{label}: key order or set mismatch; got {list(out.keys())}, "
            f"expected {list(MOTION_FEATURES)}"
        )
    if len(out) != 8:
        failures.append(f"{label}: expected 8 features, got {len(out)}")
    if set(out.keys()) != set(MOTION_FEATURES):
        failures.append(f"{label}: key set does not match MOTION_FEATURES")


def _check_all_numeric_finite(out: dict, label: str, failures: list[str]) -> None:
    for name, val in out.items():
        if not _is_finite_number(val):
            failures.append(f"{label}: {name}={val!r} is not a finite number")


def main() -> None:
    failures: list[str] = []
    sequence = _mock_sequence_three_frames()

    print("extract_motion_features(mock sequence, handedness=right)")
    out_r = extract_motion_features(sequence, handedness="right")
    n0 = len(failures)
    _check_blueprint(out_r, "right", failures)
    _check_all_numeric_finite(out_r, "right", failures)
    if len(failures) == n0:
        print("  PASS — right: keys match MOTION_FEATURES, all values finite")
    else:
        print("  FAIL — right: blueprint or numeric checks")

    r = out_r
    for key, label in [
        ("lead_wrist_velocity_mean", "lead wrist mean"),
        ("trail_wrist_velocity_mean", "trail wrist mean"),
        ("lead_wrist_velocity_max", "lead wrist max"),
        ("trail_wrist_velocity_max", "trail wrist max"),
        ("body_center_velocity_mean", "body center mean"),
        ("body_center_velocity_max", "body center max"),
    ]:
        v = float(r[key])
        if v <= 0.0:
            failures.append(f"right: {label} should be positive, got {v}")
        else:
            print(f"  PASS — right {key} positive ({v})")

    if float(r["motion_energy_total"]) <= 0.0:
        failures.append(f"right: motion_energy_total should be positive, got {r['motion_energy_total']}")
    else:
        print(f"  PASS — right motion_energy_total positive ({r['motion_energy_total']})")

    print("\nextract_motion_features(mock sequence, handedness=left)")
    out_l = extract_motion_features(sequence, handedness="left")
    n1 = len(failures)
    _check_blueprint(out_l, "left", failures)
    _check_all_numeric_finite(out_l, "left", failures)
    if len(failures) == n1:
        print("  PASS — left: keys match MOTION_FEATURES, all values finite")
    else:
        print("  FAIL — left: blueprint or numeric checks")

    tol = 1e-9
    swap_pairs = [
        ("lead_wrist_velocity_mean", "trail_wrist_velocity_mean"),
        ("trail_wrist_velocity_mean", "lead_wrist_velocity_mean"),
        ("lead_wrist_velocity_max", "trail_wrist_velocity_max"),
        ("trail_wrist_velocity_max", "lead_wrist_velocity_max"),
    ]
    print("\nlead/trail wrist swap (right vs left handedness)")
    for key_r, key_l in swap_pairs:
        a = float(out_r[key_r])
        b = float(out_l[key_l])
        if not math.isclose(a, b, rel_tol=0.0, abs_tol=tol):
            failures.append(
                f"swap: right[{key_r}]={a} vs left[{key_l}]={b} (expected equal)"
            )
        else:
            print(f"  PASS — right {key_r} matches left {key_l}")

    invariant_keys = (
        "body_center_velocity_mean",
        "body_center_velocity_max",
        "shoulder_rotation_velocity_mean",
        "motion_energy_total",
    )
    print("invariants (same physical sequence)")
    for key in invariant_keys:
        a = float(out_r[key])
        b = float(out_l[key])
        if not math.isclose(a, b, rel_tol=0.0, abs_tol=tol):
            failures.append(f"invariant {key}: right={a} left={b}")
        else:
            print(f"  PASS — {key} matches")

    print()
    if failures:
        print("FAIL results:")
        for msg in failures:
            print(f"  - {msg}")
        sys.exit(1)

    print("Success: motion feature verification passed.")


if __name__ == "__main__":
    main()
