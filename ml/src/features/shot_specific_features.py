"""Shot-specific feature extraction for Smart Cricket (Phase 5.7).

These are **v1 cricket-facing proxy features**: they summarize simple geometric
relationships useful for batting clips, not a full biomechanics lab model yet.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

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
from geometry_utils import (
    calculate_angle,
    euclidean_distance,
    get_landmark,
    landmark_to_array,
    safe_mean,
)


def _lead_trail_sides(handedness: str) -> tuple[str, str]:
    """Return (lead_side, trail_side) as 'left' or 'right'."""
    h = (handedness or "right").lower()
    if h == "left":
        return "right", "left"
    return "left", "right"


def get_body_center(frame: dict) -> np.ndarray | None:
    """Midpoint between left and right hip (pelvis)."""
    lm_l = get_landmark(frame, LEFT_HIP)
    lm_r = get_landmark(frame, RIGHT_HIP)
    if lm_l is None or lm_r is None:
        return None
    a = landmark_to_array(lm_l)
    b = landmark_to_array(lm_r)
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)):
        return None
    return (a.astype(float) + b.astype(float)) / 2.0


def get_landmark_point(frame: dict, index: int) -> np.ndarray | None:
    """Return a finite ``(x, y, z)`` array for the landmark, or ``None`` if missing."""
    lm = get_landmark(frame, index)
    if lm is None:
        return None
    arr = landmark_to_array(lm)
    if np.any(~np.isfinite(arr)):
        return None
    return arr


def get_shoulder_center(frame: dict) -> np.ndarray | None:
    """Midpoint of left and right shoulder."""
    a = get_landmark_point(frame, LEFT_SHOULDER)
    b = get_landmark_point(frame, RIGHT_SHOULDER)
    if a is None or b is None:
        return None
    return (a.astype(float) + b.astype(float)) / 2.0


def calculate_lead_elbow_angle(frame: dict, handedness: str) -> float:
    """Elbow angle (∠ shoulder–elbow–wrist) on the **lead** side."""
    lead, _trail = _lead_trail_sides(handedness)
    if lead == "left":
        s, e, w = LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST
    else:
        s, e, w = RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST
    lm_s = get_landmark(frame, s)
    lm_e = get_landmark(frame, e)
    lm_w = get_landmark(frame, w)
    if lm_s is None or lm_e is None or lm_w is None:
        return float("nan")
    return calculate_angle(
        landmark_to_array(lm_s),
        landmark_to_array(lm_e),
        landmark_to_array(lm_w),
    )


def calculate_lead_knee_angle(frame: dict, handedness: str) -> float:
    """Knee angle (∠ hip–knee–ankle) on the **lead** side."""
    lead, _trail = _lead_trail_sides(handedness)
    if lead == "left":
        h, k, a = LEFT_HIP, LEFT_KNEE, LEFT_ANKLE
    else:
        h, k, a = RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE
    lm_h = get_landmark(frame, h)
    lm_k = get_landmark(frame, k)
    lm_a = get_landmark(frame, a)
    if lm_h is None or lm_k is None or lm_a is None:
        return float("nan")
    return calculate_angle(
        landmark_to_array(lm_h),
        landmark_to_array(lm_k),
        landmark_to_array(lm_a),
    )


def extract_shot_specific_features(
    sequence: dict,
    handedness: str = "right",
) -> dict[str, float]:
    """Aggregate shot-style proxies over a pose sequence.

    For **empty** or unusable clips, every value is **0.0** (see requirement).
    """
    lead_side, trail_side = _lead_trail_sides(handedness)

    lead_ankle_idx = LEFT_ANKLE if lead_side == "left" else RIGHT_ANKLE
    trail_ankle_idx = RIGHT_ANKLE if trail_side == "right" else LEFT_ANKLE
    lead_wrist_idx = LEFT_WRIST if lead_side == "left" else RIGHT_WRIST
    lead_knee_idx = LEFT_KNEE if lead_side == "left" else RIGHT_KNEE

    frames = sequence.get("frames")
    if not isinstance(frames, list):
        frames = []
    valid_frames = [f for f in frames if isinstance(f, dict)]

    # --- front_foot_commitment: lead ankle travel from first to last valid frame ---
    first_ank: np.ndarray | None = None
    last_ank: np.ndarray | None = None
    for frame in valid_frames:
        p = get_landmark_point(frame, lead_ankle_idx)
        if p is not None:
            if first_ank is None:
                first_ank = p
            last_ank = p
    if first_ank is None or last_ank is None:
        front_foot_commitment = 0.0
    else:
        d = euclidean_distance(first_ank, last_ank)
        front_foot_commitment = float(d) if math.isfinite(d) else 0.0

    # --- back_foot_loading: mean distance trail ankle ↔ body center ---
    trail_body_dists: list[float] = []
    for frame in valid_frames:
        ta = get_landmark_point(frame, trail_ankle_idx)
        bc = get_body_center(frame)
        if ta is None or bc is None:
            continue
        dist = euclidean_distance(ta, bc)
        if math.isfinite(dist):
            trail_body_dists.append(float(dist))
    back_foot_loading = safe_mean(trail_body_dists)

    # --- follow-through: last frame (in time) that has a valid lead wrist ---
    follow_through_height = 0.0
    follow_through_extension = 0.0
    for frame in reversed(valid_frames):
        w = get_landmark_point(frame, lead_wrist_idx)
        if w is None:
            continue
        sh = get_shoulder_center(frame)
        bc = get_body_center(frame)
        if sh is not None:
            follow_through_height = abs(float(w[1] - sh[1]))
        if bc is not None:
            ext = euclidean_distance(w, bc)
            follow_through_extension = float(ext) if math.isfinite(ext) else 0.0
        break

    # --- lead elbow / knee change: last valid minus first valid angle ---
    elbow_angles: list[float] = []
    knee_angles: list[float] = []
    for frame in valid_frames:
        ea = calculate_lead_elbow_angle(frame, handedness)
        ka = calculate_lead_knee_angle(frame, handedness)
        elbow_angles.append(ea)
        knee_angles.append(ka)

    elbow_valid = [a for a in elbow_angles if math.isfinite(a)]
    knee_valid = [a for a in knee_angles if math.isfinite(a)]
    if len(elbow_valid) >= 1:
        lead_elbow_extension_change = float(elbow_valid[-1] - elbow_valid[0])
    else:
        lead_elbow_extension_change = 0.0
    if len(knee_valid) >= 1:
        lead_knee_flexion_change = float(knee_valid[-1] - knee_valid[0])
    else:
        lead_knee_flexion_change = 0.0

    # --- head_to_lead_knee_alignment ---
    nose_knee_dists: list[float] = []
    for frame in valid_frames:
        n = get_landmark_point(frame, NOSE)
        k = get_landmark_point(frame, lead_knee_idx)
        if n is None or k is None:
            continue
        dist = euclidean_distance(n, k)
        if math.isfinite(dist):
            nose_knee_dists.append(float(dist))
    head_to_lead_knee_alignment = safe_mean(nose_knee_dists)

    # --- body center travel for weight transfer ---
    bc_first: np.ndarray | None = None
    bc_last: np.ndarray | None = None
    for frame in valid_frames:
        bc = get_body_center(frame)
        if bc is not None:
            if bc_first is None:
                bc_first = bc
            bc_last = bc
    if bc_first is None or bc_last is None:
        body_travel = 0.0
    else:
        bt = euclidean_distance(bc_first, bc_last)
        body_travel = float(bt) if math.isfinite(bt) else 0.0

    # v1: how far the front foot and pelvis both displaced (simple interpretable sum)
    weight_transfer_score = front_foot_commitment + body_travel

    return {
        "front_foot_commitment": front_foot_commitment,
        "back_foot_loading": back_foot_loading,
        "follow_through_height": follow_through_height,
        "follow_through_extension": follow_through_extension,
        "lead_elbow_extension_change": lead_elbow_extension_change,
        "lead_knee_flexion_change": lead_knee_flexion_change,
        "head_to_lead_knee_alignment": head_to_lead_knee_alignment,
        "weight_transfer_score": weight_transfer_score,
    }


def _is_numeric_finite(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v)


def _smoke_test() -> None:
    def _pt(x: float, y: float, z: float = 0.0) -> dict[str, float]:
        return {"x": x, "y": y, "z": z}

    # Right-handed: lead = left. Two frames with foot and hip movement.
    f1 = {
        NOSE: _pt(0.5, 0.3),
        LEFT_SHOULDER: _pt(0.45, 0.42),
        RIGHT_SHOULDER: _pt(0.55, 0.42),
        LEFT_ELBOW: _pt(0.46, 0.5),
        LEFT_WRIST: _pt(0.5, 0.55),
        RIGHT_ELBOW: _pt(0.54, 0.5),
        RIGHT_WRIST: _pt(0.52, 0.54),
        LEFT_HIP: _pt(0.46, 0.65),
        RIGHT_HIP: _pt(0.54, 0.65),
        LEFT_KNEE: _pt(0.47, 0.78),
        LEFT_ANKLE: _pt(0.47, 0.93),
        RIGHT_KNEE: _pt(0.53, 0.78),
        RIGHT_ANKLE: _pt(0.53, 0.93),
    }
    f2 = {k: _pt(v["x"] + 0.02, v["y"] + 0.01, v["z"]) for k, v in f1.items()}
    f2[LEFT_ANKLE] = _pt(0.50, 0.94)
    f2[LEFT_HIP] = _pt(0.48, 0.66)
    f2[RIGHT_HIP] = _pt(0.56, 0.66)

    mock = {"frames": [{"landmarks": dict(f1)}, {"landmarks": dict(f2)}]}
    out = extract_shot_specific_features(mock, handedness="right")

    expected_keys = (
        "front_foot_commitment",
        "back_foot_loading",
        "follow_through_height",
        "follow_through_extension",
        "lead_elbow_extension_change",
        "lead_knee_flexion_change",
        "head_to_lead_knee_alignment",
        "weight_transfer_score",
    )
    if set(out.keys()) != set(expected_keys) or len(out) != 8:
        raise AssertionError(f"bad keys: {out.keys()}")

    for k, v in out.items():
        if not _is_numeric_finite(v):
            raise AssertionError(f"{k} not finite numeric: {v!r}")

    print("Success: shot-specific feature smoke test passed.")


if __name__ == "__main__":
    _smoke_test()
