"""Reusable geometry helpers for Smart Cricket feature engineering (Phase 5.3).

These utilities do not compute the 32 blueprint features; they only provide
safe building blocks for later phases.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np


def _float_or_nan(value: Any) -> float:
    """Parse a value to float, or NaN if missing or not a finite number."""
    if value is None:
        return float("nan")
    try:
        x = float(value)
    except (TypeError, ValueError):
        return float("nan")
    if not math.isfinite(x):
        return float("nan")
    return x


def _as_vector3(point: Any) -> np.ndarray:
    """Turn a point into a length-3 float vector; invalid components become NaN."""
    if point is None:
        return np.full(3, np.nan, dtype=float)

    if isinstance(point, dict):
        x = _float_or_nan(point.get("x"))
        y = _float_or_nan(point.get("y"))
        z = _float_or_nan(point.get("z"))
        if math.isnan(z) and "z" not in point:
            z = 0.0
        return np.array([x, y, z], dtype=float)

    arr = np.asarray(point, dtype=float).reshape(-1)
    if arr.size >= 3:
        out = arr[:3].astype(float, copy=True)
        if not np.all(np.isfinite(out)):
            out = out.astype(float)
            out[~np.isfinite(out)] = np.nan
        return out
    if arr.size == 0:
        return np.full(3, np.nan, dtype=float)
    padded = np.full(3, np.nan, dtype=float)
    padded[: arr.size] = arr
    if arr.size == 2:
        padded[2] = 0.0
    return padded


def get_landmark(frame: dict, landmark_index: int) -> dict | None:
    """Return the landmark dict for ``landmark_index`` in ``frame``, or None if missing.

    Expects ``frame`` to be a mapping with a ``"landmarks"`` entry that is either:
    - a list/tuple of landmark dicts (index = pose landmark id), or
    - a dict keyed by int or str indices.
    """
    if not isinstance(frame, dict):
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


def landmark_to_array(landmark: dict) -> np.ndarray:
    """Convert a landmark dict's x, y, z into a numeric ``(3,)`` array.

    Missing x/y yield NaN. If ``z`` is omitted, it defaults to ``0.0`` (common for 2D-only data).
    """
    if not isinstance(landmark, dict):
        return np.full(3, np.nan, dtype=float)

    x = _float_or_nan(landmark.get("x"))
    y = _float_or_nan(landmark.get("y"))
    if "z" in landmark:
        z = _float_or_nan(landmark.get("z"))
    else:
        z = 0.0
    return np.array([x, y, z], dtype=float)


def euclidean_distance(point_a: Any, point_b: Any) -> float:
    """Euclidean distance in 3D. Returns NaN if inputs are invalid or degenerate."""
    a = _as_vector3(point_a)
    b = _as_vector3(point_b)
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)):
        return float("nan")
    d = b - a
    norm = float(np.linalg.norm(d))
    if not math.isfinite(norm):
        return float("nan")
    return norm


def vector_between(point_a: Any, point_b: Any) -> np.ndarray:
    """Return the vector from ``point_a`` to ``point_b`` (i.e. ``point_b - point_a``).

    Components may be NaN if a point is invalid.
    """
    a = _as_vector3(point_a)
    b = _as_vector3(point_b)
    return b - a


def calculate_angle(point_a: Any, point_b: Any, point_c: Any) -> float:
    """Angle ∠ABC in degrees: vertex at ``point_b``, with segments to A and C.

    Example: shoulder–elbow–wrist gives the elbow angle; hip–knee–ankle gives the knee angle.
    Returns NaN if vectors are zero-length or inputs are invalid.
    """
    ba = vector_between(point_b, point_a)
    bc = vector_between(point_b, point_c)
    if np.any(~np.isfinite(ba)) or np.any(~np.isfinite(bc)):
        return float("nan")

    len_ba = float(np.linalg.norm(ba))
    len_bc = float(np.linalg.norm(bc))
    if len_ba == 0.0 or len_bc == 0.0:
        return float("nan")

    cos_theta = float(np.dot(ba, bc) / (len_ba * len_bc))
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return float(math.degrees(math.acos(cos_theta)))


def safe_mean(values: list[float]) -> float:
    """Mean of numeric values, ignoring None and NaN. Returns 0.0 if nothing valid."""
    nums: list[float] = []
    for v in values:
        if v is None:
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(x):
            nums.append(x)
    if not nums:
        return 0.0
    return float(sum(nums) / len(nums))


def safe_circular_mean_degrees(values: list[float]) -> float:
    """Circular mean for angles in degrees, ignoring invalid values."""
    nums: list[float] = []
    for v in values:
        if v is None:
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(x):
            nums.append(x)
    if not nums:
        return 0.0
    radians = np.deg2rad(np.asarray(nums, dtype=float))
    sin_mean = float(np.sin(radians).mean())
    cos_mean = float(np.cos(radians).mean())
    if sin_mean == 0.0 and cos_mean == 0.0:
        return 0.0
    return float(math.degrees(math.atan2(sin_mean, cos_mean)))


def safe_min(values: list[float]) -> float:
    """Minimum of numeric values, ignoring None and NaN. Returns 0.0 if nothing valid."""
    nums: list[float] = []
    for v in values:
        if v is None:
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(x):
            nums.append(x)
    if not nums:
        return 0.0
    return float(min(nums))


def safe_max(values: list[float]) -> float:
    """Maximum of numeric values, ignoring None and NaN. Returns 0.0 if nothing valid."""
    nums: list[float] = []
    for v in values:
        if v is None:
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(x):
            nums.append(x)
    if not nums:
        return 0.0
    return float(max(nums))


def calculate_velocity_series(points: Sequence[Any]) -> list[float]:
    """Frame-to-frame movement magnitude between consecutive valid 3D points.

    Invalid points are skipped. If fewer than two valid points remain, returns ``[]``.
    """
    valid: list[np.ndarray] = []
    for p in points:
        v = _as_vector3(p)
        if np.all(np.isfinite(v)):
            valid.append(v)

    if len(valid) < 2:
        return []

    out: list[float] = []
    for i in range(len(valid) - 1):
        step = valid[i + 1] - valid[i]
        mag = float(np.linalg.norm(step))
        if math.isfinite(mag):
            out.append(mag)
    return out


def _main_smoke_tests() -> None:
    """Tiny sanity checks for local development (not a full test suite)."""
    d = euclidean_distance([0, 0, 0], [3, 4, 0])
    if not math.isclose(d, 5.0, rel_tol=0.0, abs_tol=1e-9):
        raise AssertionError(f"expected distance 5, got {d}")

    ang = calculate_angle([1, 0, 0], [0, 0, 0], [0, 1, 0])
    if not math.isclose(ang, 90.0, rel_tol=0.0, abs_tol=1e-6):
        raise AssertionError(f"expected angle ~90°, got {ang}")

    vel = calculate_velocity_series([(0, 0, 0), (1, 0, 0), (3, 0, 0)])
    if len(vel) != 2 or not math.isclose(vel[0], 1.0) or not math.isclose(vel[1], 2.0):
        raise AssertionError(f"expected velocity series [1, 2], got {vel}")

    print("Success: geometry_utils basic checks passed.")


if __name__ == "__main__":
    _main_smoke_tests()
