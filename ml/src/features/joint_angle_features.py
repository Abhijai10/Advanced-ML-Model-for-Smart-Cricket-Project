"""Joint angle feature extraction for Smart Cricket (Phase 5.4).

Computes only the joint-angle entries from the Phase 5.2 feature blueprint.
Posture, motion, and shot-specific features are implemented in later phases.
"""

from __future__ import annotations

import math

from feature_config import (
    LEFT_ANKLE,
    LEFT_ELBOW,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    LEFT_WRIST,
    RIGHT_ANKLE,
    RIGHT_ELBOW,
    RIGHT_HIP,
    RIGHT_KNEE,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)
from geometry_utils import (
    calculate_angle,
    get_landmark,
    landmark_to_array,
    safe_circular_mean_degrees,
    safe_mean,
    safe_min,
)


def calculate_elbow_angle(frame: dict, side: str) -> float:
    """Elbow flexion/extension angle in degrees (∠ shoulder–elbow–wrist).

    The elbow is the joint center: we measure the angle between the upper arm
    (shoulder→elbow) and forearm (elbow→wrist).
    """
    side_l = side.lower()
    if side_l == "left":
        idx_s, idx_e, idx_w = LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST
    elif side_l == "right":
        idx_s, idx_e, idx_w = RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST
    else:
        return float("nan")

    lm_s = get_landmark(frame, idx_s)
    lm_e = get_landmark(frame, idx_e)
    lm_w = get_landmark(frame, idx_w)
    if lm_s is None or lm_e is None or lm_w is None:
        return float("nan")

    return calculate_angle(
        landmark_to_array(lm_s),
        landmark_to_array(lm_e),
        landmark_to_array(lm_w),
    )


def calculate_knee_angle(frame: dict, side: str) -> float:
    """Knee angle in degrees (∠ hip–knee–ankle).

    The knee is the joint center: thigh (hip→knee) vs shank (knee→ankle).
    """
    side_l = side.lower()
    if side_l == "left":
        idx_h, idx_k, idx_a = LEFT_HIP, LEFT_KNEE, LEFT_ANKLE
    elif side_l == "right":
        idx_h, idx_k, idx_a = RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE
    else:
        return float("nan")

    lm_h = get_landmark(frame, idx_h)
    lm_k = get_landmark(frame, idx_k)
    lm_a = get_landmark(frame, idx_a)
    if lm_h is None or lm_k is None or lm_a is None:
        return float("nan")

    return calculate_angle(
        landmark_to_array(lm_h),
        landmark_to_array(lm_k),
        landmark_to_array(lm_a),
    )


def calculate_shoulder_rotation_angle(frame: dict) -> float:
    """Opening angle of the shoulder line in the x–y plane (image / ground plane).

    Uses the vector from left shoulder to right shoulder and reports its heading
    relative to the +x axis (``atan2(dy, dx)`` in degrees). This is a simple
    proxy for how “open” or “closed” the upper body is in 2D; not full 3D
    biomechanical shoulder rotation.
    """
    lm_l = get_landmark(frame, LEFT_SHOULDER)
    lm_r = get_landmark(frame, RIGHT_SHOULDER)
    if lm_l is None or lm_r is None:
        return float("nan")

    p_l = landmark_to_array(lm_l)
    p_r = landmark_to_array(lm_r)
    dx = float(p_r[0] - p_l[0])
    dy = float(p_r[1] - p_l[1])
    if not math.isfinite(dx) or not math.isfinite(dy):
        return float("nan")
    if dx == 0.0 and dy == 0.0:
        return float("nan")
    return float(math.degrees(math.atan2(dy, dx)))


def calculate_hip_rotation_angle(frame: dict) -> float:
    """Opening angle of the hip line in the x–y plane (same convention as shoulders).

    Vector from left hip to right hip, heading vs +x axis in degrees.
    """
    lm_l = get_landmark(frame, LEFT_HIP)
    lm_r = get_landmark(frame, RIGHT_HIP)
    if lm_l is None or lm_r is None:
        return float("nan")

    p_l = landmark_to_array(lm_l)
    p_r = landmark_to_array(lm_r)
    dx = float(p_r[0] - p_l[0])
    dy = float(p_r[1] - p_l[1])
    if not math.isfinite(dx) or not math.isfinite(dy):
        return float("nan")
    if dx == 0.0 and dy == 0.0:
        return float("nan")
    return float(math.degrees(math.atan2(dy, dx)))


def extract_joint_angle_features(
    sequence: dict,
    handedness: str = "right",
) -> dict[str, float]:
    """Aggregate joint-angle features over a pose sequence.

    ``sequence`` should look like pose JSON: ``{"frames": [ { "landmarks": ... }, ... ]}``.

    **Lead vs trail (cricket batting):**
    For a right-handed batter, the **lead** side is typically the **left** (front)
    side of the body and the **trail** side is the **right** (back) side.
    For a left-handed batter, lead/trail swap.

    Per-frame angles that are missing or non-finite are skipped by ``safe_mean`` /
    ``safe_min`` so summaries stay robust.
    """
    h = (handedness or "right").lower()
    if h == "right":
        lead_side, trail_side = "left", "right"
    elif h == "left":
        lead_side, trail_side = "right", "left"
    else:
        lead_side, trail_side = "left", "right"

    frames = sequence.get("frames")
    if not isinstance(frames, list):
        frames = []

    lead_elbow: list[float] = []
    trail_elbow: list[float] = []
    lead_knee: list[float] = []
    trail_knee: list[float] = []
    shoulder_line: list[float] = []
    hip_line: list[float] = []

    for frame in frames:
        if not isinstance(frame, dict):
            continue

        lead_elbow.append(calculate_elbow_angle(frame, lead_side))
        trail_elbow.append(calculate_elbow_angle(frame, trail_side))
        lead_knee.append(calculate_knee_angle(frame, lead_side))
        trail_knee.append(calculate_knee_angle(frame, trail_side))
        shoulder_line.append(calculate_shoulder_rotation_angle(frame))
        hip_line.append(calculate_hip_rotation_angle(frame))

    return {
        "lead_elbow_angle_mean": safe_mean(lead_elbow),
        "lead_elbow_angle_min": safe_min(lead_elbow),
        "trail_elbow_angle_mean": safe_mean(trail_elbow),
        "lead_knee_angle_mean": safe_mean(lead_knee),
        "lead_knee_angle_min": safe_min(lead_knee),
        "trail_knee_angle_mean": safe_mean(trail_knee),
        "shoulder_rotation_angle_mean": safe_circular_mean_degrees(shoulder_line),
        "hip_rotation_angle_mean": safe_circular_mean_degrees(hip_line),
    }


def _smoke_test() -> None:
    """Tiny mock sequence to ensure extraction returns the expected shape."""

    def _lm(x: float, y: float, z: float = 0.0) -> dict[str, float]:
        return {"x": x, "y": y, "z": z}

    # Left elbow ~90°: shoulder (0,0), elbow (1,0), wrist (1,1) in x–y.
    # Right elbow similar, shifted. Hips/knees/ankles for ~90° knee.
    landmarks_common = {
        LEFT_SHOULDER: _lm(0.0, 0.0),
        LEFT_ELBOW: _lm(1.0, 0.0),
        LEFT_WRIST: _lm(1.0, 1.0),
        RIGHT_SHOULDER: _lm(4.0, 0.0),
        RIGHT_ELBOW: _lm(3.0, 0.0),
        RIGHT_WRIST: _lm(3.0, 1.0),
        LEFT_HIP: _lm(0.0, 3.0),
        LEFT_KNEE: _lm(1.0, 3.0),
        LEFT_ANKLE: _lm(1.0, 4.0),
        RIGHT_HIP: _lm(4.0, 3.0),
        RIGHT_KNEE: _lm(3.0, 3.0),
        RIGHT_ANKLE: _lm(3.0, 4.0),
    }

    mock_sequence = {
        "frames": [
            {"landmarks": dict(landmarks_common)},
            {"landmarks": dict(landmarks_common)},
        ]
    }

    out = extract_joint_angle_features(mock_sequence, handedness="right")

    expected_keys = (
        "lead_elbow_angle_mean",
        "lead_elbow_angle_min",
        "trail_elbow_angle_mean",
        "lead_knee_angle_mean",
        "lead_knee_angle_min",
        "trail_knee_angle_mean",
        "shoulder_rotation_angle_mean",
        "hip_rotation_angle_mean",
    )

    for key in expected_keys:
        if key not in out:
            raise AssertionError(f"missing key: {key}")

    if set(out.keys()) != set(expected_keys):
        raise AssertionError(f"unexpected keys: {out.keys()}")

    for key, val in out.items():
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise AssertionError(f"{key} is not numeric: {val!r}")
        if not math.isfinite(float(val)):
            raise AssertionError(f"{key} is not finite: {val!r}")

    print("Success: joint angle feature smoke test passed.")


if __name__ == "__main__":
    _smoke_test()
