"""Posture feature extraction for Smart Cricket (Phase 5.5).

Computes only the posture entries from the Phase 5.2 feature blueprint.
Motion and shot-specific features are implemented in later phases.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from feature_config import (
    LEFT_ANKLE,
    LEFT_HIP,
    LEFT_SHOULDER,
    NOSE,
    RIGHT_ANKLE,
    RIGHT_HIP,
    RIGHT_SHOULDER,
)
from geometry_utils import (
    euclidean_distance,
    get_landmark,
    landmark_to_array,
    safe_max,
    safe_mean,
)


def get_body_center(frame: dict) -> np.ndarray | None:
    """Midpoint of left and right hip (pelvis / base center in pose space).

    Returns ``None`` if either hip is missing or not finite.
    """
    lm_l = get_landmark(frame, LEFT_HIP)
    lm_r = get_landmark(frame, RIGHT_HIP)
    if lm_l is None or lm_r is None:
        return None
    a = landmark_to_array(lm_l)
    b = landmark_to_array(lm_r)
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)):
        return None
    return (a.astype(float) + b.astype(float)) / 2.0


def get_shoulder_center(frame: dict) -> np.ndarray | None:
    """Midpoint of left and right shoulder."""
    lm_l = get_landmark(frame, LEFT_SHOULDER)
    lm_r = get_landmark(frame, RIGHT_SHOULDER)
    if lm_l is None or lm_r is None:
        return None
    a = landmark_to_array(lm_l)
    b = landmark_to_array(lm_r)
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)):
        return None
    return (a.astype(float) + b.astype(float)) / 2.0


def _line_heading_deg_xy(p0: np.ndarray, p1: np.ndarray) -> float:
    """Heading of segment p0→p1 in the x–y plane (degrees, ``atan2(dy, dx)``)."""
    dx = float(p1[0] - p0[0])
    dy = float(p1[1] - p0[1])
    if dx == 0.0 and dy == 0.0:
        return float("nan")
    if not math.isfinite(dx) or not math.isfinite(dy):
        return float("nan")
    return float(math.degrees(math.atan2(dy, dx)))


def calculate_trunk_lean(frame: dict) -> float:
    """Approximate trunk lean in degrees (torso vs “up” in the image).

    Builds a 2D vector from **hip center → shoulder center**. In typical image
    coordinates, **y increases downward**, so “up” is direction ``(0, -1)``.
    The returned angle is in ``[0, 180]``: ``0°`` when the torso points straight
    up, larger values when the player leans more away from vertical.
    """
    hip_c = get_body_center(frame)
    sh_c = get_shoulder_center(frame)
    if hip_c is None or sh_c is None:
        return float("nan")

    v = sh_c[:2].astype(float) - hip_c[:2].astype(float)
    n = float(np.linalg.norm(v))
    if n < 1e-12 or not math.isfinite(n):
        return float("nan")

    v_unit = v / n
    # “Up” in screen space (decreasing y).
    up = np.array([0.0, -1.0], dtype=float)
    cos_t = float(np.clip(np.dot(v_unit, up), -1.0, 1.0))
    return float(math.degrees(math.acos(cos_t)))


def calculate_head_offset(frame: dict) -> float:
    """Distance from nose to hip center (how far the head sits over the base)."""
    nose = get_landmark(frame, NOSE)
    hip_c = get_body_center(frame)
    if nose is None or hip_c is None:
        return float("nan")
    return euclidean_distance(landmark_to_array(nose), hip_c)


def calculate_stance_width(frame: dict) -> float:
    """Distance between left and right ankles (feet spread)."""
    la = get_landmark(frame, LEFT_ANKLE)
    ra = get_landmark(frame, RIGHT_ANKLE)
    if la is None or ra is None:
        return float("nan")
    return euclidean_distance(landmark_to_array(la), landmark_to_array(ra))


def calculate_shoulder_hip_separation(frame: dict) -> float:
    """Difference between shoulder-line and hip-line headings in the x–y plane (degrees).

    Each line uses **left → right** landmarks, same idea as Phase 5.4 joint angles.
    Positive values mean the shoulder line is rotated more counter-clockwise than
    the hip line (in x–y).
    """
    lm_ls = get_landmark(frame, LEFT_SHOULDER)
    lm_rs = get_landmark(frame, RIGHT_SHOULDER)
    lm_lh = get_landmark(frame, LEFT_HIP)
    lm_rh = get_landmark(frame, RIGHT_HIP)
    if lm_ls is None or lm_rs is None or lm_lh is None or lm_rh is None:
        return float("nan")

    sl = landmark_to_array(lm_ls)
    sr = landmark_to_array(lm_rs)
    hl = landmark_to_array(lm_lh)
    hr = landmark_to_array(lm_rh)
    if (
        np.any(~np.isfinite(sl))
        or np.any(~np.isfinite(sr))
        or np.any(~np.isfinite(hl))
        or np.any(~np.isfinite(hr))
    ):
        return float("nan")

    shoulder_deg = _line_heading_deg_xy(sl, sr)
    hip_deg = _line_heading_deg_xy(hl, hr)
    if not math.isfinite(shoulder_deg) or not math.isfinite(hip_deg):
        return float("nan")
    return float(shoulder_deg - hip_deg)


def extract_posture_features(sequence: dict) -> dict[str, float]:
    """Aggregate posture features over a pose sequence (``frames`` with ``landmarks``)."""
    frames = sequence.get("frames")
    if not isinstance(frames, list):
        frames = []

    trunk_leans: list[float] = []
    head_offsets: list[float] = []
    shoulder_hip_seps: list[float] = []
    stance_widths: list[float] = []

    first_hip_xy: np.ndarray | None = None
    last_hip_xy: np.ndarray | None = None

    valid_dict_frames = [f for f in frames if isinstance(f, dict)]

    for frame in valid_dict_frames:
        trunk_leans.append(calculate_trunk_lean(frame))
        head_offsets.append(calculate_head_offset(frame))
        shoulder_hip_seps.append(calculate_shoulder_hip_separation(frame))
        stance_widths.append(calculate_stance_width(frame))

        hip_c = get_body_center(frame)
        if hip_c is not None and np.all(np.isfinite(hip_c)):
            xy = hip_c[:2].astype(float).copy()
            if first_hip_xy is None:
                first_hip_xy = xy
            last_hip_xy = xy

    # Head stability: mean nose movement between consecutive *timeline* frames.
    nose_movements: list[float] = []
    for i in range(len(valid_dict_frames) - 1):
        n0 = get_landmark(valid_dict_frames[i], NOSE)
        n1 = get_landmark(valid_dict_frames[i + 1], NOSE)
        if n0 is None or n1 is None:
            continue
        d = euclidean_distance(landmark_to_array(n0), landmark_to_array(n1))
        if math.isfinite(d):
            nose_movements.append(d)

    shift_x = 0.0
    shift_y = 0.0
    if first_hip_xy is not None and last_hip_xy is not None:
        shift_x = float(last_hip_xy[0] - first_hip_xy[0])
        shift_y = float(last_hip_xy[1] - first_hip_xy[1])

    return {
        "trunk_lean_mean": safe_mean(trunk_leans),
        "trunk_lean_max": safe_max(trunk_leans),
        "head_stability": safe_mean(nose_movements),
        "head_over_base_offset": safe_mean(head_offsets),
        "shoulder_hip_separation_mean": safe_mean(shoulder_hip_seps),
        "stance_width_mean": safe_mean(stance_widths),
        "body_center_shift_x": shift_x,
        "body_center_shift_y": shift_y,
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
    """Minimal mock sequence to check output shape."""

    def _pt(x: float, y: float, z: float = 0.0) -> dict[str, float]:
        return {"x": x, "y": y, "z": z}

    # Two frames: slight hip shift and nose motion; symmetric shoulders/hips for simple geometry.
    base_landmarks = {
        NOSE: _pt(0.5, 0.35),
        LEFT_SHOULDER: _pt(0.45, 0.45),
        RIGHT_SHOULDER: _pt(0.55, 0.45),
        LEFT_HIP: _pt(0.47, 0.65),
        RIGHT_HIP: _pt(0.53, 0.65),
        LEFT_ANKLE: _pt(0.46, 0.92),
        RIGHT_ANKLE: _pt(0.54, 0.92),
    }
    frame_b2 = {k: _pt(v["x"] + 0.01, v["y"] + 0.005, v["z"]) for k, v in base_landmarks.items()}
    frame_b2[LEFT_HIP] = _pt(0.48, 0.66)
    frame_b2[RIGHT_HIP] = _pt(0.54, 0.66)

    mock = {
        "frames": [
            {"landmarks": dict(base_landmarks)},
            {"landmarks": dict(frame_b2)},
        ]
    }

    out = extract_posture_features(mock)
    expected = (
        "trunk_lean_mean",
        "trunk_lean_max",
        "head_stability",
        "head_over_base_offset",
        "shoulder_hip_separation_mean",
        "stance_width_mean",
        "body_center_shift_x",
        "body_center_shift_y",
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

    print("Success: posture feature smoke test passed.")


if __name__ == "__main__":
    _smoke_test()
