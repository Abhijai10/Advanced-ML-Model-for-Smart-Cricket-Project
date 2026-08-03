"""Motion-energy helpers for Phase 9 shot segmentation.

The segmenter uses existing temporal features instead of raw pixels. This keeps
Phase 9 explainable and aligned with the Phase 5.5/6 temporal feature contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


DEFAULT_MOTION_FEATURE_WEIGHTS: dict[str, float] = {
    "lead_wrist_velocity": 1.0,
    "trail_wrist_velocity": 0.85,
    "lead_elbow_velocity": 0.45,
    "trail_elbow_velocity": 0.35,
    "body_center_velocity": 0.8,
    "lead_wrist_acceleration": 0.55,
    "frame_motion_energy": 1.25,
}


@dataclass(frozen=True)
class MotionEnergyConfig:
    """Configuration for turning temporal features into a smooth motion signal."""

    smoothing_window: int = 5
    robust_percentile: float = 95.0
    minimum_scale: float = 1e-6
    start_threshold: float = 0.28
    active_threshold: float = 0.18
    end_threshold: float = 0.12


@dataclass(frozen=True)
class MotionEnergySignal:
    """Per-frame motion-energy arrays used by the segmentation state machine."""

    raw_energy: np.ndarray
    normalized_energy: np.ndarray
    smoothed_energy: np.ndarray
    start_threshold: float
    active_threshold: float
    end_threshold: float
    feature_weights: dict[str, float]


def validate_feature_sequence(sequence: np.ndarray, expected_features: int = 32) -> None:
    """Validate one temporal feature sequence shaped [T, F]."""
    if not isinstance(sequence, np.ndarray):
        raise ValueError(f"Expected numpy.ndarray, got {type(sequence).__name__}.")
    if sequence.ndim != 2:
        raise ValueError(f"Expected rank-2 sequence [T,F], got shape {sequence.shape}.")
    if sequence.shape[0] <= 0:
        raise ValueError(f"Expected at least one frame, got shape {sequence.shape}.")
    if sequence.shape[1] != expected_features:
        raise ValueError(f"Expected {expected_features} features, got {sequence.shape[1]}.")
    if not np.isfinite(sequence).all():
        raise ValueError("Feature sequence contains NaN or infinite values.")


def moving_average(values: np.ndarray, window: int) -> np.ndarray:
    """Return centered moving average with stable length."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError(f"moving_average expects rank-1 input, got shape {values.shape}.")
    window = int(window)
    if window <= 1:
        return values.astype(np.float64, copy=True)
    pad_left = window // 2
    pad_right = window - 1 - pad_left
    padded = np.pad(values, (pad_left, pad_right), mode="edge")
    kernel = np.ones(window, dtype=np.float64) / float(window)
    return np.convolve(padded, kernel, mode="valid")


def compute_motion_energy_signal(
    sequence: np.ndarray,
    feature_columns: Sequence[str],
    config: MotionEnergyConfig = MotionEnergyConfig(),
    feature_weights: dict[str, float] | None = None,
) -> MotionEnergySignal:
    """Compute raw, normalized, and smoothed motion energy for one shot sequence."""
    validate_feature_sequence(sequence)
    columns = list(feature_columns)
    if len(columns) != sequence.shape[1]:
        raise ValueError(
            f"feature_columns length {len(columns)} != sequence feature dim {sequence.shape[1]}."
        )
    weights = dict(feature_weights or DEFAULT_MOTION_FEATURE_WEIGHTS)
    raw = np.zeros(sequence.shape[0], dtype=np.float64)
    used: dict[str, float] = {}
    for name, weight in weights.items():
        if name not in columns:
            continue
        idx = columns.index(name)
        raw += abs(float(weight)) * np.abs(sequence[:, idx].astype(np.float64))
        used[name] = float(weight)
    if not used:
        raise ValueError("No configured motion-energy feature names were found in feature_columns.")

    scale = float(np.percentile(raw, config.robust_percentile))
    if not np.isfinite(scale) or scale < config.minimum_scale:
        scale = float(max(raw.max(), config.minimum_scale))
    normalized = np.clip(raw / scale, 0.0, 1.0)
    smoothed = np.clip(moving_average(normalized, config.smoothing_window), 0.0, 1.0)
    return MotionEnergySignal(
        raw_energy=raw.astype(np.float64),
        normalized_energy=normalized.astype(np.float64),
        smoothed_energy=smoothed.astype(np.float64),
        start_threshold=float(config.start_threshold),
        active_threshold=float(config.active_threshold),
        end_threshold=float(config.end_threshold),
        feature_weights=used,
    )
