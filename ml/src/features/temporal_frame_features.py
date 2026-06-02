"""Phase 5.5 — Per-frame temporal features (32-D) from aligned MediaPipe pose.

Computes one scalar per schema column per frame. Does not aggregate over time,
save tensors, or split data.

Right-handed batter assumption: lead = left body side, trail = right.
Handedness-aware mirroring can be added later without changing schema names.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

# MediaPipe pose landmark indices (33-landmark topology)
NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

_ML_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SCHEMA_PATH = _ML_ROOT / "data" / "final_temporal" / "temporal_feature_schema.json"

# Fallback: must match temporal_feature_schema.json feature_columns order.
_ORDERED_FEATURES_FALLBACK: list[str] = [
    "lead_elbow_angle",
    "trail_elbow_angle",
    "lead_knee_angle",
    "trail_knee_angle",
    "lead_shoulder_angle",
    "trail_shoulder_angle",
    "lead_wrist_relative_x",
    "hip_rotation_angle",
    "trunk_lean",
    "head_over_base_offset",
    "head_to_lead_knee_alignment",
    "shoulder_hip_separation",
    "stance_width",
    "body_center_offset_x",
    "body_center_offset_y",
    "upper_body_balance_offset",
    "lead_wrist_velocity",
    "trail_wrist_velocity",
    "lead_elbow_velocity",
    "trail_elbow_velocity",
    "body_center_velocity",
    "lead_wrist_acceleration",
    "hip_rotation_velocity",
    "frame_motion_energy",
    "front_foot_commitment_signal",
    "back_foot_loading_signal",
    "weight_transfer_signal",
    "follow_through_height_signal",
    "follow_through_extension_signal",
    "lead_elbow_extension_signal",
    "bat_side_wrist_height_signal",
    "stance_to_swing_progress_signal",
]


def _schema_path() -> Path:
    return _DEFAULT_SCHEMA_PATH


def load_temporal_feature_columns(schema_path: Path | None = None) -> list[str]:
    """Load ordered feature names from temporal_feature_schema.json."""
    path = schema_path or _schema_path()
    if not path.is_file():
        return list(_ORDERED_FEATURES_FALLBACK)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    cols = data.get("feature_columns")
    if not isinstance(cols, list) or not cols:
        return list(_ORDERED_FEATURES_FALLBACK)
    return [str(c) for c in cols]


def validate_feature_columns_loaded(columns: Sequence[str]) -> None:
    """Ensure loaded columns match the canonical 32-name contract."""
    if list(columns) != _ORDERED_FEATURES_FALLBACK:
        raise ValueError(
            "temporal_feature_schema.json feature_columns do not match "
            "the built-in Version 1 ordering. Regenerate the schema or fix the file."
        )


def get_landmark(frame: Mapping[str, Any] | None, landmark_index: int) -> dict | None:
    """Return the landmark dict for ``landmark_index`` in ``frame``, or None if missing."""
    if not isinstance(frame, Mapping):
        return None
    if not isinstance(landmark_index, int) or landmark_index < 0:
        return None

    landmarks = frame.get("landmarks")
    if landmarks is None:
        return None

    if isinstance(landmarks, (list, tuple)):
        if landmark_index >= len(landmarks):
            return None
        item = landmarks[landmark_index]
        return item if isinstance(item, dict) else None

    if isinstance(landmarks, dict):
        item = landmarks.get(landmark_index)
        if item is None:
            item = landmarks.get(str(landmark_index))
        return item if isinstance(item, dict) else None

    return None


def point_to_array(landmark: Any) -> np.ndarray:
    """Landmark dict → ``(3,)`` float array [x, y, z]. Missing z defaults to 0.0."""
    if not isinstance(landmark, dict):
        return np.full(3, np.nan, dtype=float)
    x = landmark.get("x")
    y = landmark.get("y")
    z = landmark.get("z") if "z" in landmark else 0.0
    try:
        out = np.array([float(x), float(y), float(z)], dtype=float)
    except (TypeError, ValueError):
        return np.full(3, np.nan, dtype=float)
    return out


def euclidean_distance_2d(a: Any, b: Any) -> float:
    """Distance in the XY plane using first two components."""
    pa = np.asarray(a, dtype=float).reshape(-1)
    pb = np.asarray(b, dtype=float).reshape(-1)
    if pa.size < 2 or pb.size < 2:
        return float("nan")
    dx = float(pa[0] - pb[0])
    dy = float(pa[1] - pb[1])
    d = math.hypot(dx, dy)
    return d if math.isfinite(d) else float("nan")


def _as_vec3(a: Any) -> np.ndarray:
    if isinstance(a, dict):
        return point_to_array(a)
    arr = np.asarray(a, dtype=float).reshape(-1)
    if arr.size >= 3:
        return arr[:3].astype(float, copy=False)
    out = np.full(3, np.nan, dtype=float)
    out[: arr.size] = arr
    if arr.size == 2:
        out[2] = 0.0
    return out


def euclidean_distance_3d(a: Any, b: Any) -> float:
    """3D Euclidean distance between landmarks or length-3 vectors."""
    pa, pb = _as_vec3(a), _as_vec3(b)
    if np.any(~np.isfinite(pa)) or np.any(~np.isfinite(pb)):
        return float("nan")
    d = float(np.linalg.norm(pa - pb))
    return d if math.isfinite(d) else float("nan")


def vector_angle_degrees(u: np.ndarray, v: np.ndarray) -> float:
    """Angle between two vectors in degrees; returns NaN if degenerate."""
    u = np.asarray(u, dtype=float).reshape(-1)
    v = np.asarray(v, dtype=float).reshape(-1)
    if u.size < 2 or v.size < 2:
        return float("nan")
    nu = float(np.linalg.norm(u[: min(3, u.size)]))
    nv = float(np.linalg.norm(v[: min(3, v.size)]))
    if nu == 0.0 or nv == 0.0 or not (math.isfinite(nu) and math.isfinite(nv)):
        return float("nan")
    # Use up to 3D for dot product
    uu = u[:3] if u.size >= 3 else np.pad(u, (0, 3 - u.size))
    vv = v[:3] if v.size >= 3 else np.pad(v, (0, 3 - v.size))
    c = float(np.dot(uu, vv) / (nu * nv))
    c = max(-1.0, min(1.0, c))
    ang = math.degrees(math.acos(c))
    return ang if math.isfinite(ang) else float("nan")


def safe_float(x: Any, default: float = 0.0) -> float:
    """Finite float or ``default``."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def safe_velocity(
    current_lm: dict | None,
    previous_lm: dict | None,
    *,
    use_3d: bool = True,
) -> float:
    """Magnitude of frame-to-frame landmark displacement; 0.0 if previous is missing."""
    if previous_lm is None:
        return 0.0
    a = point_to_array(current_lm) if current_lm is not None else np.full(3, np.nan)
    b = point_to_array(previous_lm) if previous_lm is not None else np.full(3, np.nan)
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)):
        return 0.0
    if use_3d:
        d = float(np.linalg.norm(a - b))
    else:
        d = math.hypot(float(a[0] - b[0]), float(a[1] - b[1]))
    return d if math.isfinite(d) else 0.0


def _angle_at_vertex_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle ∠ABC in degrees (vertex at ``b``)."""
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)) or np.any(~np.isfinite(c)):
        return float("nan")
    ba = a - b
    bc = c - b
    la = float(np.linalg.norm(ba))
    lb = float(np.linalg.norm(bc))
    if la == 0.0 or lb == 0.0:
        return float("nan")
    cos_t = float(np.dot(ba, bc) / (la * lb))
    cos_t = max(-1.0, min(1.0, cos_t))
    ang = math.degrees(math.acos(cos_t))
    return ang if math.isfinite(ang) else float("nan")


def _line_angle_xy_deg(p1: np.ndarray, p2: np.ndarray) -> float:
    """Angle of vector p1→p2 in the XY plane from +x axis, degrees (-180, 180]."""
    if np.any(~np.isfinite(p1[:2])) or np.any(~np.isfinite(p2[:2])):
        return float("nan")
    dx = float(p2[0] - p1[0])
    dy = float(p2[1] - p1[1])
    return math.degrees(math.atan2(dy, dx))


def _mid(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return 0.5 * (a + b)


def compute_temporal_frame_features(
    current_frame: Mapping[str, Any],
    previous_frame: Mapping[str, Any] | None = None,
    frame_index: int = 0,
    sequence_length: int = 60,
) -> dict[str, float]:
    """Compute the 32 official per-frame features for ``current_frame``.

    Lead = left, trail = right (right-handed batter). See module docstring.
    """
    # --- Landmarks (current) ---
    def cur(idx: int) -> dict | None:
        return get_landmark(current_frame, idx)

    def pos(idx: int) -> np.ndarray:
        lm = cur(idx)
        return point_to_array(lm) if lm is not None else np.full(3, np.nan, dtype=float)

    def prev_lm(idx: int) -> dict | None:
        if previous_frame is None:
            return None
        return get_landmark(previous_frame, idx)

    ls, rs = pos(LEFT_SHOULDER), pos(RIGHT_SHOULDER)
    le, re = pos(LEFT_ELBOW), pos(RIGHT_ELBOW)
    lw, rw = pos(LEFT_WRIST), pos(RIGHT_WRIST)
    lh, rh = pos(LEFT_HIP), pos(RIGHT_HIP)
    lk, rk = pos(LEFT_KNEE), pos(RIGHT_KNEE)
    la, ra = pos(LEFT_ANKLE), pos(RIGHT_ANKLE)
    nose = pos(NOSE)

    # Aliases: lead = left, trail = right
    lead_shoulder, trail_shoulder = ls, rs
    lead_elbow, trail_elbow = le, re
    lead_wrist, trail_wrist = lw, rw
    lead_hip, trail_hip = lh, rh
    lead_knee, trail_knee = lk, rk
    lead_ankle, trail_ankle = la, ra

    hip_c = _mid(lead_hip, trail_hip)
    shoulder_c = _mid(lead_shoulder, trail_shoulder)
    body_c = _mid(hip_c, shoulder_c)

    # --- Joint angles ---
    lead_elbow_angle = _angle_at_vertex_deg(lead_shoulder, lead_elbow, lead_wrist)
    trail_elbow_angle = _angle_at_vertex_deg(trail_shoulder, trail_elbow, trail_wrist)
    lead_knee_angle = _angle_at_vertex_deg(lead_hip, lead_knee, lead_ankle)
    trail_knee_angle = _angle_at_vertex_deg(trail_hip, trail_knee, trail_ankle)
    lead_shoulder_angle = _angle_at_vertex_deg(lead_elbow, lead_shoulder, lead_hip)
    trail_shoulder_angle = _angle_at_vertex_deg(trail_elbow, trail_shoulder, trail_hip)
    shoulder_rotation_angle = _line_angle_xy_deg(lead_shoulder, trail_shoulder)
    lead_wrist_relative_x = safe_float(lead_wrist[0] - hip_c[0])
    hip_rotation_angle = _line_angle_xy_deg(lead_hip, trail_hip)

    # --- Posture ---
    v_trunk = shoulder_c - hip_c
    # Vertical reference: negative Y as "up" in typical image coordinates (y increases downward).
    up = np.array([0.0, -1.0, 0.0], dtype=float)
    trunk_lean = vector_angle_degrees(v_trunk, up)

    head_over_base_offset = float(nose[0] - hip_c[0]) if np.all(np.isfinite(nose)) else float("nan")
    head_to_lead_knee_alignment = (
        float(nose[0] - lead_knee[0]) if np.all(np.isfinite(nose)) and np.all(np.isfinite(lead_knee)) else float("nan")
    )
    shoulder_hip_separation = (
        shoulder_rotation_angle - hip_rotation_angle
        if math.isfinite(shoulder_rotation_angle) and math.isfinite(hip_rotation_angle)
        else float("nan")
    )
    stance_width = euclidean_distance_2d(lead_ankle, trail_ankle)
    body_center_offset_x = float(body_c[0] - hip_c[0])
    body_center_offset_y = float(body_c[1] - hip_c[1])
    upper_body_balance_offset = float(shoulder_c[0] - hip_c[0])

    # --- Motion (need previous positions) ---
    def vel_idx(idx: int) -> float:
        return safe_velocity(cur(idx), prev_lm(idx), use_3d=True)

    lead_wrist_velocity = vel_idx(LEFT_WRIST)
    trail_wrist_velocity = vel_idx(RIGHT_WRIST)
    lead_elbow_velocity = vel_idx(LEFT_ELBOW)
    trail_elbow_velocity = vel_idx(RIGHT_ELBOW)
    # v1 acceleration-like proxy: true acceleration requires t-2, t-1, and t.
    # A future extractor can support second-order temporal acceleration directly.
    lead_wrist_acceleration = abs(lead_wrist_velocity - trail_wrist_velocity)

    if previous_frame is None:
        body_center_velocity = 0.0
        hip_rotation_velocity = 0.0
    else:
        p_ls = point_to_array(prev_lm(LEFT_SHOULDER))
        p_rs = point_to_array(prev_lm(RIGHT_SHOULDER))
        p_lh = point_to_array(prev_lm(LEFT_HIP))
        p_rh = point_to_array(prev_lm(RIGHT_HIP))
        p_hip_c = _mid(p_lh, p_rh)
        p_shoulder_c = _mid(p_ls, p_rs)
        p_body_c = _mid(p_hip_c, p_shoulder_c)
        if np.all(np.isfinite(body_c)) and np.all(np.isfinite(p_body_c)):
            body_center_velocity = float(np.linalg.norm(body_c - p_body_c))
        else:
            body_center_velocity = 0.0
        ha_now = _line_angle_xy_deg(lead_hip, trail_hip)
        ha_prev = _line_angle_xy_deg(p_lh, p_rh)
        if math.isfinite(ha_now) and math.isfinite(ha_prev):
            dh = ha_now - ha_prev
            while dh > 180.0:
                dh -= 360.0
            while dh < -180.0:
                dh += 360.0
            hip_rotation_velocity = abs(dh)
        else:
            hip_rotation_velocity = 0.0

    # Frame motion energy: sum of displacement magnitudes for key joints
    motion_indices = [
        LEFT_WRIST,
        RIGHT_WRIST,
        LEFT_ELBOW,
        RIGHT_ELBOW,
        LEFT_SHOULDER,
        RIGHT_SHOULDER,
        LEFT_HIP,
        RIGHT_HIP,
        LEFT_KNEE,
        RIGHT_KNEE,
    ]
    frame_motion_energy = sum(vel_idx(i) for i in motion_indices)

    # --- Cricket-specific v1 proxies ---
    front_foot_commitment_signal = safe_float(lead_ankle[0] - hip_c[0])
    # Trail-side vertical chain: knee and ankle below hip (positive if y increases downward)
    back_foot_loading_signal = safe_float(
        0.5 * ((trail_knee[1] - trail_hip[1]) + (trail_ankle[1] - trail_knee[1]))
    )
    if previous_frame is None or not np.all(np.isfinite(body_c)):
        weight_transfer_signal = 0.0
    else:
        p_lh2 = point_to_array(prev_lm(LEFT_HIP))
        p_rh2 = point_to_array(prev_lm(RIGHT_HIP))
        if np.all(np.isfinite(p_lh2)) and np.all(np.isfinite(p_rh2)):
            p_hip_c2 = _mid(p_lh2, p_rh2)
            p_body_c2 = _mid(p_hip_c2, _mid(point_to_array(prev_lm(LEFT_SHOULDER)), point_to_array(prev_lm(RIGHT_SHOULDER))))
            weight_transfer_signal = safe_float(body_c[0] - p_body_c2[0])
        else:
            weight_transfer_signal = 0.0

    follow_through_height_signal = safe_float(lead_wrist[1] - shoulder_c[1])
    follow_through_extension_signal = float(
        np.linalg.norm(lead_wrist - lead_shoulder)
        if np.all(np.isfinite(lead_wrist)) and np.all(np.isfinite(lead_shoulder))
        else float("nan")
    )
    if math.isfinite(lead_elbow_angle):
        # Straighter elbow (larger interior angle, ~180°) → higher signal (~1.0).
        lead_elbow_extension_signal = safe_float(float(lead_elbow_angle) / 180.0)
    else:
        lead_elbow_extension_signal = 0.0
    bat_side_wrist_height_signal = safe_float(trail_wrist[1] - shoulder_c[1])
    denom = max(sequence_length - 1, 1)
    stance_to_swing_progress_signal = safe_float(frame_index / denom)

    raw: dict[str, float] = {
        "lead_elbow_angle": lead_elbow_angle,
        "trail_elbow_angle": trail_elbow_angle,
        "lead_knee_angle": lead_knee_angle,
        "trail_knee_angle": trail_knee_angle,
        "lead_shoulder_angle": lead_shoulder_angle,
        "trail_shoulder_angle": trail_shoulder_angle,
        "lead_wrist_relative_x": lead_wrist_relative_x,
        "hip_rotation_angle": hip_rotation_angle,
        "trunk_lean": trunk_lean,
        "head_over_base_offset": head_over_base_offset,
        "head_to_lead_knee_alignment": head_to_lead_knee_alignment,
        "shoulder_hip_separation": shoulder_hip_separation,
        "stance_width": stance_width,
        "body_center_offset_x": body_center_offset_x,
        "body_center_offset_y": body_center_offset_y,
        "upper_body_balance_offset": upper_body_balance_offset,
        "lead_wrist_velocity": lead_wrist_velocity,
        "trail_wrist_velocity": trail_wrist_velocity,
        "lead_elbow_velocity": lead_elbow_velocity,
        "trail_elbow_velocity": trail_elbow_velocity,
        "body_center_velocity": body_center_velocity,
        "lead_wrist_acceleration": lead_wrist_acceleration,
        "hip_rotation_velocity": hip_rotation_velocity,
        "frame_motion_energy": frame_motion_energy,
        "front_foot_commitment_signal": front_foot_commitment_signal,
        "back_foot_loading_signal": back_foot_loading_signal,
        "weight_transfer_signal": weight_transfer_signal,
        "follow_through_height_signal": follow_through_height_signal,
        "follow_through_extension_signal": follow_through_extension_signal,
        "lead_elbow_extension_signal": lead_elbow_extension_signal,
        "bat_side_wrist_height_signal": bat_side_wrist_height_signal,
        "stance_to_swing_progress_signal": stance_to_swing_progress_signal,
    }

    columns = load_temporal_feature_columns()
    validate_feature_columns_loaded(columns)

    ordered: dict[str, float] = {}
    for name in columns:
        ordered[name] = safe_float(raw.get(name, 0.0), 0.0)

    validate_features_dict(ordered, columns)
    return ordered


def features_to_vector(
    features_dict: Mapping[str, float],
    feature_columns: Sequence[str],
) -> np.ndarray:
    """Stack feature values in ``feature_columns`` order → shape ``(len(columns),)``."""
    validate_features_dict(features_dict, feature_columns)
    return np.array([float(features_dict[k]) for k in feature_columns], dtype=np.float64)


def validate_features_dict(
    features_dict: Mapping[str, float],
    feature_columns: Sequence[str],
) -> None:
    """Require exactly 32 keys in schema order and finite floats."""
    cols = list(feature_columns)
    if len(cols) != 32:
        raise ValueError(f"Expected 32 feature columns, got {len(cols)}.")
    if list(features_dict.keys()) != cols:
        raise ValueError("features_dict keys must match feature_columns order exactly.")
    for k in cols:
        v = features_dict.get(k)
        try:
            fv = float(v)  # accepts int, float, numpy scalars
        except (TypeError, ValueError) as e:
            raise TypeError(f"Feature {k!r} must be numeric, got {type(v).__name__}.") from e
        if not math.isfinite(fv):
            raise ValueError(f"Feature {k!r} must be finite, got {v!r}.")


def _smoke() -> None:
    frame = {"landmarks": [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(33)]}
    # Nudge a few joints so angles / offsets are non-degenerate
    lm = frame["landmarks"]
    lm[LEFT_SHOULDER] = {"x": 0.45, "y": 0.4, "z": 0.0}
    lm[RIGHT_SHOULDER] = {"x": 0.55, "y": 0.4, "z": 0.0}
    lm[LEFT_ELBOW] = {"x": 0.42, "y": 0.45, "z": 0.0}
    lm[RIGHT_ELBOW] = {"x": 0.58, "y": 0.45, "z": 0.0}
    lm[LEFT_WRIST] = {"x": 0.40, "y": 0.5, "z": 0.0}
    lm[RIGHT_WRIST] = {"x": 0.60, "y": 0.5, "z": 0.0}
    lm[LEFT_HIP] = {"x": 0.47, "y": 0.6, "z": 0.0}
    lm[RIGHT_HIP] = {"x": 0.53, "y": 0.6, "z": 0.0}
    lm[LEFT_KNEE] = {"x": 0.46, "y": 0.72, "z": 0.0}
    lm[RIGHT_KNEE] = {"x": 0.54, "y": 0.72, "z": 0.0}
    lm[LEFT_ANKLE] = {"x": 0.45, "y": 0.9, "z": 0.0}
    lm[RIGHT_ANKLE] = {"x": 0.55, "y": 0.9, "z": 0.0}
    lm[NOSE] = {"x": 0.5, "y": 0.35, "z": 0.0}

    f0 = compute_temporal_frame_features(frame, None, 0, 60)
    f1 = compute_temporal_frame_features(frame, frame, 1, 60)
    assert len(f0) == 32
    vec = features_to_vector(f0, load_temporal_feature_columns())
    assert vec.shape == (32,)
    assert f1["lead_wrist_velocity"] == 0.0
    print("temporal_frame_features smoke OK:", list(f0.keys())[:4], "...")


if __name__ == "__main__":
    _smoke()
