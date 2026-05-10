"""Phase 5.4 verification for joint angle feature extraction."""

from __future__ import annotations

import math
import sys

from feature_config import JOINT_ANGLE_FEATURES
from joint_angle_features import extract_joint_angle_features


def _lm(x: float, y: float, z: float = 0.0) -> dict[str, float]:
    return {"x": x, "y": y, "z": z}


def _mock_sequence_three_frames() -> dict:
    """Asymmetric left vs right limbs so lead/trail swap changes elbow/knee summaries."""
    sqrt3_2 = math.sqrt(3.0) / 2.0
    # Left elbow ~90°, left knee ~90° (same pattern as joint_angle_features smoke test).
    # Right elbow ~60°, right knee ~60° (unit forearm/shank from joint).
    base = {
        11: _lm(0.0, 0.0),  # LEFT_SHOULDER
        13: _lm(1.0, 0.0),  # LEFT_ELBOW
        15: _lm(1.0, 1.0),  # LEFT_WRIST
        12: _lm(10.0, 0.0),  # RIGHT_SHOULDER
        14: _lm(9.0, 0.0),  # RIGHT_ELBOW
        16: _lm(9.5, sqrt3_2),  # RIGHT_WRIST → ~60° at elbow
        23: _lm(0.0, 3.0),  # LEFT_HIP
        25: _lm(1.0, 3.0),  # LEFT_KNEE
        27: _lm(1.0, 4.0),  # LEFT_ANKLE
        24: _lm(10.0, 3.0),  # RIGHT_HIP
        26: _lm(9.0, 3.0),  # RIGHT_KNEE
        28: _lm(9.5, 3.0 + sqrt3_2),  # RIGHT_ANKLE → ~60° at knee
    }

    # Tiny per-frame jitter so min ≤ mean on elbows/knees still stays valid.
    f2 = {k: _lm(v["x"] + 0.01, v["y"], v["z"]) for k, v in base.items()}
    f3 = {k: _lm(v["x"] - 0.01, v["y"], v["z"]) for k, v in base.items()}

    return {
        "frames": [
            {"landmarks": dict(base)},
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


def _check_keys_match_blueprint(out: dict, label: str, failures: list[str]) -> None:
    if list(out.keys()) != list(JOINT_ANGLE_FEATURES):
        failures.append(
            f"{label}: key order or set mismatch; got {list(out.keys())}, "
            f"expected {list(JOINT_ANGLE_FEATURES)}"
        )
    if len(out) != 8:
        failures.append(f"{label}: expected 8 features, got {len(out)}")
    if set(out.keys()) != set(JOINT_ANGLE_FEATURES):
        failures.append(f"{label}: key set does not match JOINT_ANGLE_FEATURES")


def _check_all_numeric_finite(out: dict, label: str, failures: list[str]) -> None:
    for name, val in out.items():
        if not _is_finite_number(val):
            failures.append(f"{label}: {name}={val!r} is not a finite number")


def main() -> None:
    failures: list[str] = []
    sequence = _mock_sequence_three_frames()

    print("extract_joint_angle_features (handedness=right)")
    out_r = extract_joint_angle_features(sequence, handedness="right")
    n0 = len(failures)
    _check_keys_match_blueprint(out_r, "right", failures)
    _check_all_numeric_finite(out_r, "right", failures)
    if len(failures) == n0:
        print(
            "  PASS — right: keys match JOINT_ANGLE_FEATURES (order + count), "
            "all values finite"
        )
    else:
        print("  FAIL — right: blueprint key or numeric checks (see below)")

    print("extract_joint_angle_features (handedness=left)")
    out_l = extract_joint_angle_features(sequence, handedness="left")
    n1 = len(failures)
    _check_keys_match_blueprint(out_l, "left", failures)
    _check_all_numeric_finite(out_l, "left", failures)
    if len(failures) == n1:
        print(
            "  PASS — left: keys match JOINT_ANGLE_FEATURES (order + count), "
            "all values finite"
        )
    else:
        print("  FAIL — left: blueprint key or numeric checks (see below)")

    # Right: lead=left (~90° elbows/knees), trail=right (~60°).
    # Left: lead=right (~60°), trail=left (~90°). Elbow/knee lead/trail swap; shoulder/hip unchanged.
    tol = 1e-6
    # Blueprint only has min for *lead* elbow/knee; means exist for both lead and trail.
    mean_swap_pairs = [
        ("lead_elbow_angle_mean", "trail_elbow_angle_mean"),
        ("trail_elbow_angle_mean", "lead_elbow_angle_mean"),
        ("lead_knee_angle_mean", "trail_knee_angle_mean"),
        ("trail_knee_angle_mean", "lead_knee_angle_mean"),
    ]
    print("lead/trail swap (right vs left)")
    for key_r, key_l in mean_swap_pairs:
        a = float(out_r[key_r])
        b = float(out_l[key_l])
        if not math.isclose(a, b, rel_tol=0.0, abs_tol=tol):
            failures.append(
                f"swap check: right[{key_r}]={a} vs left[{key_l}]={b} (expected ~equal)"
            )
        else:
            print(f"  PASS — right {key_r} matches left {key_l}")

    # Lead-side min follows the same lead/trail swap (no trail_*_min in blueprint).
    for key in ("lead_elbow_angle_min", "lead_knee_angle_min"):
        a = float(out_r[key])
        b = float(out_l[key])
        if math.isclose(a, b, rel_tol=0.0, abs_tol=tol):
            failures.append(
                f"lead min should swap sides: right[{key}]={a} left[{key}]={b} (expected different)"
            )
        else:
            print(f"  PASS — {key} differs by handedness (lead side swapped)")

    for key in ("shoulder_rotation_angle_mean", "hip_rotation_angle_mean"):
        a = float(out_r[key])
        b = float(out_l[key])
        if not math.isclose(a, b, rel_tol=0.0, abs_tol=tol):
            failures.append(
                f"handedness invariant: {key} right={a} left={b} (should match)"
            )
        else:
            print(f"  PASS — {key} invariant under handedness")

    # Sanity: right-handed lead elbow should be ~90, trail ~60 (distinct).
    if out_r["lead_elbow_angle_mean"] <= out_r["trail_elbow_angle_mean"]:
        failures.append(
            "right-handed mapping: expected lead elbow mean > trail (left ~90°, right ~60°)"
        )
    else:
        print("  PASS — right-handed lead elbow mean > trail elbow mean (asymmetric mock)")

    print()
    if failures:
        print("FAIL results:")
        for msg in failures:
            print(f"  - {msg}")
        sys.exit(1)

    print("Success: joint angle feature verification passed.")


if __name__ == "__main__":
    main()
