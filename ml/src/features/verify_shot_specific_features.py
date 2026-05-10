"""Phase 5.7 verification for shot-specific feature extraction."""

from __future__ import annotations

import math
import sys

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
    SHOT_SPECIFIC_FEATURES,
)
from shot_specific_features import extract_shot_specific_features


def _lm(x: float, y: float, z: float = 0.0) -> dict[str, float]:
    return {"x": x, "y": y, "z": z}


def _frame(
    left_ankle_xy: tuple[float, float],
    right_ankle_xy: tuple[float, float],
    left_wrist_y: float,
    right_wrist_y: float,
    hip_shift: float,
) -> dict[int, dict[str, float]]:
    """Full valid geometry: lead left foot moves more than trail right foot."""
    lx, ly = left_ankle_xy
    rx, ry = right_ankle_xy
    return {
        NOSE: _lm(0.50, 0.30),
        LEFT_SHOULDER: _lm(0.44 + hip_shift * 0.01, 0.41),
        RIGHT_SHOULDER: _lm(0.56 + hip_shift * 0.01, 0.41),
        LEFT_ELBOW: _lm(0.45 + hip_shift * 0.01, 0.49),
        LEFT_WRIST: _lm(0.48 + hip_shift * 0.01, left_wrist_y),
        RIGHT_ELBOW: _lm(0.55 + hip_shift * 0.01, 0.49),
        RIGHT_WRIST: _lm(0.52 + hip_shift * 0.01, right_wrist_y),
        LEFT_HIP: _lm(0.45 + hip_shift, 0.64),
        RIGHT_HIP: _lm(0.55 + hip_shift, 0.64),
        LEFT_KNEE: _lm(0.46 + hip_shift * 0.5, 0.77),
        RIGHT_KNEE: _lm(0.54 + hip_shift * 0.5, 0.77),
        LEFT_ANKLE: _lm(lx, ly),
        RIGHT_ANKLE: _lm(rx, ry),
    }


def _mock_sequence_three_frames() -> dict:
    """Left ankle (lead for RH batter) travels far; right ankle (trail) moves little."""
    f1 = _frame(
        left_ankle_xy=(0.38, 0.93),
        right_ankle_xy=(0.64, 0.93),
        left_wrist_y=0.53,
        right_wrist_y=0.52,
        hip_shift=0.0,
    )
    f2 = _frame(
        left_ankle_xy=(0.44, 0.931),
        right_ankle_xy=(0.642, 0.932),
        left_wrist_y=0.531,
        right_wrist_y=0.521,
        hip_shift=0.008,
    )
    f3 = _frame(
        left_ankle_xy=(0.52, 0.94),
        right_ankle_xy=(0.645, 0.935),
        left_wrist_y=0.52,
        right_wrist_y=0.555,
        hip_shift=0.018,
    )
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
    if list(out.keys()) != list(SHOT_SPECIFIC_FEATURES):
        failures.append(
            f"{label}: key order mismatch; got {list(out.keys())}, "
            f"expected {list(SHOT_SPECIFIC_FEATURES)}"
        )
    if len(out) != 8:
        failures.append(f"{label}: expected 8 features, got {len(out)}")
    if set(out.keys()) != set(SHOT_SPECIFIC_FEATURES):
        failures.append(f"{label}: key set does not match SHOT_SPECIFIC_FEATURES")


def _check_all_numeric_finite(out: dict, label: str, failures: list[str]) -> None:
    for name, val in out.items():
        if not _is_finite_number(val):
            failures.append(f"{label}: {name}={val!r} is not a finite number")


def main() -> None:
    failures: list[str] = []
    sequence = _mock_sequence_three_frames()

    print("extract_shot_specific_features(mock sequence, handedness=right)")
    out_r = extract_shot_specific_features(sequence, handedness="right")
    n0 = len(failures)
    _check_blueprint(out_r, "right", failures)
    _check_all_numeric_finite(out_r, "right", failures)
    if len(failures) == n0:
        print("  PASS — right: keys match SHOT_SPECIFIC_FEATURES, all finite")
    else:
        print("  FAIL — right: blueprint or finiteness")

    pos_keys = (
        "front_foot_commitment",
        "back_foot_loading",
        "follow_through_height",
        "follow_through_extension",
        "head_to_lead_knee_alignment",
    )
    for key in pos_keys:
        v = float(out_r[key])
        if v <= 0.0:
            failures.append(f"right: {key} should be positive, got {v}")
        else:
            print(f"  PASS — right {key} positive ({v})")

    wts = float(out_r["weight_transfer_score"])
    if wts < 0.0:
        failures.append(f"right: weight_transfer_score must be non-negative, got {wts}")
    else:
        print(f"  PASS — right weight_transfer_score non-negative ({wts})")

    print("\nextract_shot_specific_features(mock sequence, handedness=left)")
    out_l = extract_shot_specific_features(sequence, handedness="left")
    n1 = len(failures)
    _check_blueprint(out_l, "left", failures)
    _check_all_numeric_finite(out_l, "left", failures)
    if len(failures) == n1:
        print("  PASS — left: keys match SHOT_SPECIFIC_FEATURES, all finite")
    else:
        print("  FAIL — left: blueprint or finiteness")

    print("\nlead/trail asymmetry (expect detectable differences)")
    # Right: lead = left ankle (large displacement); Left: lead = right ankle (small displacement)
    if float(out_r["front_foot_commitment"]) <= float(out_l["front_foot_commitment"]):
        failures.append(
            "expected right-handed front_foot_commitment > left (lead left foot moves more)"
        )
    else:
        print("  PASS — front_foot_commitment differs by handedness (right > left)")

    if math.isclose(
        float(out_r["back_foot_loading"]),
        float(out_l["back_foot_loading"]),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        failures.append(
            "expected back_foot_loading to differ (trail ankle vs body center changes)"
        )
    else:
        print("  PASS — back_foot_loading differs by handedness")

    if math.isclose(
        float(out_r["head_to_lead_knee_alignment"]),
        float(out_l["head_to_lead_knee_alignment"]),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        failures.append(
            "expected head_to_lead_knee_alignment to differ (lead knee swaps)"
        )
    else:
        print("  PASS — head_to_lead_knee_alignment differs by handedness")

    # Follow-through uses lead wrist on last frame: left vs right wrist at different heights
    if math.isclose(
        float(out_r["follow_through_height"]),
        float(out_l["follow_through_height"]),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        failures.append(
            "expected follow_through_height to differ (lead wrist / mock asymmetry)"
        )
    else:
        print("  PASS — follow_through_height differs by handedness")

    if math.isclose(
        float(out_r["weight_transfer_score"]),
        float(out_l["weight_transfer_score"]),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        failures.append(
            "expected weight_transfer_score to differ (front_foot + pelvic travel mix)"
        )
    else:
        print("  PASS — weight_transfer_score differs by handedness")

    print()
    if failures:
        print("FAIL results:")
        for msg in failures:
            print(f"  - {msg}")
        sys.exit(1)

    print("Success: shot-specific feature verification passed.")


if __name__ == "__main__":
    main()
