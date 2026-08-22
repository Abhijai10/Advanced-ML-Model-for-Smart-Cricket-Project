"""Raw video to Smart Cricket analysis pipeline.

This module keeps the Phase 12 sequence analyzer intact and adds the missing
web-app bridge: uploaded video -> pose landmarks -> 60-frame feature sequence.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from features.temporal_frame_features import compute_temporal_frame_features, features_to_vector, load_temporal_feature_columns  # noqa: E402
from inference.analysis_pipeline import analyze_sequence  # noqa: E402
from preprocessing.align_pose_orientation import align_frame_landmarks  # noqa: E402
from preprocessing.clean_pose_data import should_remove_frame  # noqa: E402
from preprocessing.extract_pose import FeatureExtractionError, MediaPipeInitializationError, extract_pose_from_video  # noqa: E402
from preprocessing.normalize_pose_data import normalize_frame_landmarks  # noqa: E402
from preprocessing.prepare_sequences import resample_frames  # noqa: E402


SEQUENCE_LENGTH = 60
FEATURE_DIM = 32
VISIBILITY_THRESHOLD = 0.3


class ModelLoadError(RuntimeError):
    """Raised when a required trained-model artifact cannot be loaded."""

    error_code = "model_load_failed"


class InferenceExecutionError(RuntimeError):
    """Raised when scoring/model inference fails after feature extraction."""

    error_code = "inference_failed"


def _clean_frames(frames: list[Any]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        if should_remove_frame(frame, VISIBILITY_THRESHOLD):
            continue
        cleaned.append(frame)
    return cleaned


def _normalize_frames(frames: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    normalized: list[dict[str, Any]] = []
    warnings = 0
    for frame in frames:
        out = dict(frame)
        landmarks = out.get("landmarks")
        if not isinstance(landmarks, list):
            warnings += 1
            normalized.append(out)
            continue
        normalized_landmarks, success = normalize_frame_landmarks(landmarks)
        out["landmarks"] = normalized_landmarks
        normalized.append(out)
        if not success:
            warnings += 1
    return normalized, warnings


def _align_frames(frames: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    aligned: list[dict[str, Any]] = []
    warnings = 0
    for frame in frames:
        out = dict(frame)
        landmarks = out.get("landmarks")
        if not isinstance(landmarks, list):
            warnings += 1
            aligned.append(out)
            continue
        aligned_landmarks, success = align_frame_landmarks(landmarks)
        out["landmarks"] = aligned_landmarks
        aligned.append(out)
        if not success:
            warnings += 1
    return aligned, warnings


def _frames_to_feature_sequence(frames: list[dict[str, Any]]) -> np.ndarray:
    if len(frames) != SEQUENCE_LENGTH:
        raise ValueError(f"Expected {SEQUENCE_LENGTH} prepared frames, got {len(frames)}.")
    feature_columns = load_temporal_feature_columns()
    if len(feature_columns) != FEATURE_DIM:
        raise ValueError(f"Expected {FEATURE_DIM} temporal features, got {len(feature_columns)}.")

    sequence = np.zeros((SEQUENCE_LENGTH, FEATURE_DIM), dtype=np.float32)
    for frame_index, current_frame in enumerate(frames):
        previous_frame = frames[frame_index - 1] if frame_index > 0 else None
        features = compute_temporal_frame_features(
            current_frame,
            previous_frame=previous_frame,
            frame_index=frame_index,
            sequence_length=SEQUENCE_LENGTH,
        )
        sequence[frame_index, :] = np.asarray(features_to_vector(features, feature_columns), dtype=np.float32)

    if not np.isfinite(sequence).all():
        raise ValueError("Raw-video feature sequence contains NaN or infinite values.")
    return sequence


def build_sequence_from_raw_video(video_path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Extract a finalized 60x32 temporal feature sequence from one raw video."""
    try:
        pose_payload = extract_pose_from_video(video_path, frame_skip=1, visualize=False)
    except MediaPipeInitializationError:
        raise
    except FeatureExtractionError:
        raise
    except Exception as exc:
        raise FeatureExtractionError("Pose extraction could not process the uploaded video.") from exc
    metadata = dict(pose_payload.get("video_metadata", {}))
    frames = pose_payload.get("frames", [])
    if not isinstance(frames, list) or not frames:
        raise FeatureExtractionError("No frames were extracted from the uploaded video.")

    cleaned = _clean_frames(frames)
    if not cleaned:
        raise FeatureExtractionError("No usable pose frames remained after cleaning.")

    normalized, normalize_warnings = _normalize_frames(cleaned)
    aligned, align_warnings = _align_frames(normalized)
    prepared = resample_frames(aligned, SEQUENCE_LENGTH)
    sequence = _frames_to_feature_sequence(prepared)
    resampled_timing = [
        {
            "sequence_frame": i,
            "source_frame": frame.get("frame_index"),
            "timestamp_seconds": frame.get("timestamp"),
        }
        for i, frame in enumerate(prepared)
    ]

    source_metadata = {
        "input_mode": "raw_uploaded_video",
        "file_name": video_path.name,
        "true_label_name": "unknown",
        "video_metadata": metadata,
        "frames_extracted": len(frames),
        "frames_after_cleaning": len(cleaned),
        "frames_after_resampling": len(prepared),
        "resampled_timing": resampled_timing,
        "normalization_warnings": normalize_warnings,
        "alignment_warnings": align_warnings,
    }
    return sequence, source_metadata


def analyze_raw_video(video_path: Path) -> dict[str, Any]:
    """Analyze one uploaded raw video and return the standard analysis payload."""
    sequence, source_metadata = build_sequence_from_raw_video(video_path)
    try:
        result = analyze_sequence(sequence, source_metadata).to_dict()
    except FileNotFoundError as exc:
        raise ModelLoadError("A required Smart Cricket model artifact is unavailable.") from exc
    except Exception as exc:
        raise InferenceExecutionError("Smart Cricket model inference could not complete.") from exc
    result["debug_metadata"]["pipeline_mode"] = "raw_video_upload"
    result["debug_metadata"]["pipeline_note"] = (
        "Raw video was converted through pose extraction, cleaning, normalization, "
        "alignment, fixed-length resampling, temporal feature extraction, and the "
        "Phase 12 analysis pipeline."
    )
    return result
