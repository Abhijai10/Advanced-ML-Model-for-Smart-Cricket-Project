"""Motion feature extraction for Smart Cricket (Phase 5.6).

Captures how fast body parts move between frames (temporal motion), not static pose.
Shot-specific features are implemented in a later phase.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from feature_config import (
    LEFT_HIP,
    LEFT_SHOULDER,
    LEFT_WRIST,
    RIGHT_HIP,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)
from geometry_utils import (
    calculate_velocity_series,
    get_landmark,
    landmark_to_array,
    safe_max,
    safe_mean,
)


def get_body_center(frame: dict) -> np.ndarray | None:
    """Pelvis / hip midpoint between left and right hip (base of support in pose space)."""
    lm_l = get_landmark(frame, LEFT_HIP)
    lm_r = get_landmark(frame, RIGHT_HIP)
    if lm_l is None or lm_r is None:
        return None
    a = landmark_to_array(lm_l)
    b = landmark_to_array(lm_r)
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)):
        return None
    return (a.astype(float) + b.astype(float)) / 2.0


def get_shoulder_rotation_angle(frame: dict) -> float:
    """Heading of the left→right shoulder segment in the x–y plane (degrees).

    Same 2D convention as joint-angle “shoulder rotation”: ``atan2(dy, dx)`` from
    left shoulder to right shoulder. Used here only to measure how fast that line
    **spins** frame to frame (rotational speed proxy).
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


def calculate_rotation_velocity(angle_series: list[float]) -> list[float]:
    """Absolute frame-to-frame angle change (degrees per consecutive pair).

    Circular angles wrap at ±180°; we use the **shortest** angular distance between
    consecutive samples so a jump from 179° to -179° reads as a small motion, not 358°.
    Pairs with NaN in either angle are skipped.
    """
    out: list[float] = []
    for i in range(len(angle_series) - 1):
        a = angle_series[i]
        b = angle_series[i + 1]
        if not math.isfinite(a) or not math.isfinite(b):
            continue
        delta = (b - a + 180.0) % 360.0 - 180.0
        out.append(abs(delta))
    return out


def _lead_trail_wrist_indices(handedness: str) -> tuple[int, int]:
    h = (handedness or "right").lower()
    if h == "right":
        return LEFT_WRIST, RIGHT_WRIST
    if h == "left":
        return RIGHT_WRIST, LEFT_WRIST
    return LEFT_WRIST, RIGHT_WRIST


def extract_motion_features(
    sequence: dict,
    handedness: str = "right",
) -> dict[str, float]:
    """Aggregate motion features over a pose sequence (``frames`` with ``landmarks``).

    **Temporal movement:** each feature summarizes how landmarks move over time.

    **Velocity series:** for a point tracked every frame, we take consecutive 3D
    positions and use Euclidean step lengths between **valid** in-order samples
    (see ``calculate_velocity_series``). Mean/max summarize how fast that point moves.

    **Rotational velocity:** shoulder line heading changes per frame, in degrees.

    **Motion energy (this module):** sum of all step magnitudes for lead wrist,
    trail wrist, and body center — a simple scalar “total displacement” style score
    over the clip (not physics energy in joules).
    """
    lead_wrist_idx, trail_wrist_idx = _lead_trail_wrist_indices(handedness)

    frames = sequence.get("frames")
    if not isinstance(frames, list):
        frames = []

    valid_frames = [f for f in frames if isinstance(f, dict)]

    lead_pts: list[Any] = []
    trail_pts: list[Any] = []
    center_pts: list[Any] = []
    shoulder_angles: list[float] = []

    for frame in valid_frames:
        lw = get_landmark(frame, lead_wrist_idx)
        tw = get_landmark(frame, trail_wrist_idx)
        lead_pts.append(landmark_to_array(lw) if lw is not None else np.full(3, np.nan))
        trail_pts.append(landmark_to_array(tw) if tw is not None else np.full(3, np.nan))

        bc = get_body_center(frame)
        center_pts.append(bc if bc is not None else np.full(3, np.nan))

        shoulder_angles.append(get_shoulder_rotation_angle(frame))

    lead_vel = calculate_velocity_series(lead_pts)
    trail_vel = calculate_velocity_series(trail_pts)
    body_vel = calculate_velocity_series(center_pts)
    shoulder_rot_vel = calculate_rotation_velocity(shoulder_angles)

    motion_energy_total = float(sum(lead_vel) + sum(trail_vel) + sum(body_vel))

    return {
        "lead_wrist_velocity_mean": safe_mean(lead_vel),
        "lead_wrist_velocity_max": safe_max(lead_vel),
        "trail_wrist_velocity_mean": safe_mean(trail_vel),
        "trail_wrist_velocity_max": safe_max(trail_vel),
        "body_center_velocity_mean": safe_mean(body_vel),
        "body_center_velocity_max": safe_max(body_vel),
        "shoulder_rotation_velocity_mean": safe_mean(shoulder_rot_vel),
        "motion_energy_total": motion_energy_total,
    }


def _is_numeric_non_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    try:
        float(x)
    except (TypeError, ValueError):
        return False
    return True


def _smoke_test() -> None:
    """Small synthetic sequence with clear motion for each signal."""

    def _lm(x: float, y: float, z: float = 0.0) -> dict[str, float]:
        return {"x": x, "y": y, "z": z}

    # Right-handed: lead=left wrist, trail=right wrist. Move each point along +x; shoulder line yaw changes.
    f1 = {
        LEFT_WRIST: _lm(0.1, 0.5),
        RIGHT_WRIST: _lm(0.9, 0.5),
        LEFT_HIP: _lm(0.4, 0.75),
        RIGHT_HIP: _lm(0.6, 0.75),
        LEFT_SHOULDER: _lm(0.42, 0.45),
        RIGHT_SHOULDER: _lm(0.58, 0.45),
    }
    f2 = {k: _lm(v["x"] + 0.02, v["y"], v["z"]) for k, v in f1.items()}
    f2[LEFT_SHOULDER] = _lm(0.43, 0.45)  # tiny shoulder line change vs uniform shift
    f2[RIGHT_SHOULDER] = _lm(0.60, 0.46)

    mock = {"frames": [{"landmarks": dict(f1)}, {"landmarks": dict(f2)}]}

    out = extract_motion_features(mock, handedness="right")
    expected = (
        "lead_wrist_velocity_mean",
        "lead_wrist_velocity_max",
        "trail_wrist_velocity_mean",
        "trail_wrist_velocity_max",
        "body_center_velocity_mean",
        "body_center_velocity_max",
        "shoulder_rotation_velocity_mean",
        "motion_energy_total",
    )

    if set(out.keys()) != set(expected):
        raise AssertionError(f"bad keys: {out.keys()}")
    if len(out) != 8:
        raise AssertionError(f"expected 8 features, got {len(out)}")

    for k, v in out.items():
        if not _is_numeric_non_bool(v):
            raise AssertionError(f"{k} not numeric: {v!r}")
        if not math.isfinite(float(v)):
            raise AssertionError(f"{k} not finite: {v!r}")

    print("Success: motion feature smoke test passed.")


if __name__ == "__main__":
    _smoke_test()
