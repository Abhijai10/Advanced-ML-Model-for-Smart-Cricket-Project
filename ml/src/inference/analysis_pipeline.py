"""Offline orchestration pipeline for Smart Cricket analysis.

Phase 12 connects the already-built ML modules into one structured result:
sequence validation, model prediction, shot segmentation, technique scoring,
and coaching feedback.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from feedback.feedback_engine import generate_feedback_for_sample  # noqa: E402
from inference.inference_config import (  # noqa: E402
    DATASET_DIR,
    EXPECTED_FEATURE_DIM,
    EXPECTED_NUM_CLASSES,
    EXPECTED_SEQUENCE_LENGTH,
    PHASE10_TEMPLATE_PATH,
    PHASE12_VERSION,
    PHASE8_BEST_MODEL_DIR,
)
from inference.result_schema import AnalysisResult, PredictionResult, SegmentResult  # noqa: E402
from models.bilstm_classifier import BiLSTMClassifier  # noqa: E402
from models.gru_classifier import GRUClassifier  # noqa: E402
from models.model_config import TemporalClassifierConfig  # noqa: E402
from scoring.technique_scoring import score_sequence  # noqa: E402
from segmentation.shot_segmenter import ShotSegmenter  # noqa: E402
from training.checkpointing import load_checkpoint  # noqa: E402
from training.feature_scaler import TemporalFeatureScaler  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _validate_sequence(sequence: np.ndarray) -> np.ndarray:
    array = np.asarray(sequence, dtype=np.float32)
    if array.shape != (EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM):
        raise ValueError(
            f"Expected sequence shape {(EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM)}, got {array.shape}."
        )
    if not np.isfinite(array).all():
        raise ValueError("Inference sequence contains NaN or infinite values.")
    return array


def _class_names(label_mapping: dict[str, Any]) -> list[str]:
    index_to_class = label_mapping.get("index_to_class")
    if not isinstance(index_to_class, dict):
        raise ValueError("Label mapping missing index_to_class.")
    names = [str(index_to_class[str(i)]) for i in range(len(index_to_class))]
    if len(names) != EXPECTED_NUM_CLASSES:
        raise ValueError(f"Expected {EXPECTED_NUM_CLASSES} classes, got {len(names)}.")
    return names


def _model_from_checkpoint(checkpoint: dict[str, Any]) -> torch.nn.Module:
    cfg = checkpoint["model_config"]
    config = TemporalClassifierConfig(
        sequence_length=int(cfg["sequence_length"]),
        input_size=int(cfg["input_size"]),
        num_classes=int(cfg["num_classes"]),
        hidden_size=int(cfg["hidden_size"]),
        num_layers=int(cfg["num_layers"]),
        dropout=float(cfg["dropout"]),
        gru_bidirectional=str(checkpoint["model_name"]) == "bigru",
        lstm_bidirectional=True,
    )
    model_name = str(checkpoint["model_name"])
    if model_name in {"gru", "bigru"}:
        model = GRUClassifier(config)
    elif model_name == "bilstm":
        model = BiLSTMClassifier(config)
    else:
        raise ValueError(f"Unsupported checkpoint model_name: {model_name}")
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.eval()
    return model


def _predict(sequence: np.ndarray, class_names: list[str]) -> PredictionResult:
    checkpoint = load_checkpoint(PHASE8_BEST_MODEL_DIR / "checkpoint.pt", map_location="cpu")
    model = _model_from_checkpoint(checkpoint)
    scaler = TemporalFeatureScaler.load(PHASE8_BEST_MODEL_DIR / "scaler")
    X_scaled = scaler.transform(sequence[None, :, :])
    with torch.no_grad():
        logits = model(torch.as_tensor(X_scaled, dtype=torch.float32))
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
    if probs.shape != (EXPECTED_NUM_CLASSES,):
        raise ValueError(f"Expected {EXPECTED_NUM_CLASSES} probabilities, got shape {probs.shape}.")
    predicted_index = int(probs.argmax())
    return PredictionResult(
        predicted_shot=class_names[predicted_index],
        shot_confidence=float(probs[predicted_index]),
        class_probabilities={class_names[i]: float(probs[i]) for i in range(len(class_names))},
    )


def _segment(sequence: np.ndarray, feature_columns: list[str]) -> SegmentResult:
    result = ShotSegmenter().segment_sequence(sequence, feature_columns)
    segment = result.segment
    if segment is None:
        return SegmentResult(
            start_frame=None,
            end_frame=None,
            peak_frame=None,
            prediction_trigger_frame=None,
            completed=False,
            completion_reason=None,
            trigger_count=0,
        )
    return SegmentResult(
        start_frame=segment.start_frame,
        end_frame=segment.end_frame,
        peak_frame=segment.peak_frame,
        prediction_trigger_frame=segment.prediction_trigger_frame,
        completed=segment.completed,
        completion_reason=segment.completion_reason,
        trigger_count=segment.trigger_count,
    )


def _score_to_feedback_sample(
    *,
    source_metadata: dict[str, Any],
    prediction: PredictionResult,
    score_result: Any,
) -> dict[str, Any]:
    component_scores = {
        component.component_name: {
            "score": component.score,
            "weight": component.weight,
            "description": component.description,
            "deviations": [
                {
                    "feature_name": deviation.feature_name,
                    "statistic": deviation.statistic,
                    "actual_value": deviation.actual_value,
                    "expected_low": deviation.expected_low,
                    "expected_high": deviation.expected_high,
                    "template_center": deviation.template_center,
                    "deviation": deviation.deviation,
                    "score": deviation.score,
                }
                for deviation in component.deviations
            ],
        }
        for component in score_result.component_scores
    }
    return {
        "file_name": source_metadata.get("file_name", "unknown"),
        "true_label_name": source_metadata.get("true_label_name", "unknown"),
        "prediction_correct": source_metadata.get("true_label_name") == prediction.predicted_shot,
        "score_result": {
            "technique_match_score": score_result.technique_match_score,
            "predicted_shot": prediction.predicted_shot,
            "classifier_confidence": prediction.shot_confidence,
            "component_scores": component_scores,
            "deviation_summary": list(score_result.deviation_summary),
            "recommendations": list(score_result.recommendations),
        },
    }


def analyze_sequence(sequence: np.ndarray, source_metadata: dict[str, Any] | None = None) -> AnalysisResult:
    """Analyze one finalized temporal feature sequence and return stable JSON data."""
    source_metadata = dict(source_metadata or {})
    sequence = _validate_sequence(sequence)
    schema = _load_json(DATASET_DIR / "temporal_feature_schema.json")
    label_mapping = _load_json(DATASET_DIR / "temporal_label_mapping.json")
    templates = _load_json(PHASE10_TEMPLATE_PATH)
    feature_columns = list(schema.get("feature_columns", []))
    if len(feature_columns) != EXPECTED_FEATURE_DIM:
        raise ValueError("Temporal feature schema must contain 32 feature columns.")
    class_names = _class_names(label_mapping)

    prediction = _predict(sequence, class_names)
    segment = _segment(sequence, feature_columns)
    score_result = score_sequence(
        sequence,
        predicted_shot=prediction.predicted_shot,
        feature_columns=feature_columns,
        templates=templates,
        classifier_confidence=prediction.shot_confidence,
    )
    feedback = generate_feedback_for_sample(
        _score_to_feedback_sample(
            source_metadata=source_metadata,
            prediction=prediction,
            score_result=score_result,
        )
    )
    debug_metadata = {
        "phase": "Phase 12",
        "version": PHASE12_VERSION,
        "created_at": _utc_now(),
        "pipeline_mode": "offline_temporal_sequence",
        "input_contract": "[60, 32] temporal feature sequence",
        "model_artifact": str(PHASE8_BEST_MODEL_DIR / "checkpoint.pt"),
        "template_artifact": str(PHASE10_TEMPLATE_PATH),
        "segmentation_completed": segment.completed,
        "feedback_source": "Phase 11 feedback engine",
        "pipeline_note": (
            "Phase 12 v1 orchestrates finalized temporal sequences. Raw video upload/API handling "
            "is intentionally deferred to later roadmap phases."
        ),
        "feedback_debug_metadata": feedback.debug_metadata,
    }
    return AnalysisResult(
        predicted_shot=prediction.predicted_shot,
        shot_confidence=prediction.shot_confidence,
        technique_match_score=score_result.technique_match_score,
        detected_issues=[issue.to_dict() for issue in feedback.detected_issues],
        coaching_tips=list(feedback.coaching_tips),
        detailed_feedback=feedback.detailed_feedback,
        spoken_feedback=feedback.spoken_feedback,
        debug_metadata=debug_metadata,
        prediction=prediction,
        segmentation=segment,
        source_metadata=source_metadata,
    )


def load_dataset_sequence(*, sample_index: int | None = None, file_name: str | None = None) -> tuple[np.ndarray, dict[str, Any]]:
    """Load one finalized sequence by dataset sample index or file name."""
    index_df = pd.read_csv(DATASET_DIR / "temporal_dataset_index.csv", dtype={"video_id": str})
    if sample_index is None and file_name is None:
        raise ValueError("Provide sample_index or file_name.")
    if file_name is not None:
        matches = index_df[index_df["file_name"].astype(str) == str(file_name)]
        if matches.empty:
            raise ValueError(f"Unknown file_name in temporal dataset index: {file_name}")
        row = matches.iloc[0]
        sample_index = int(row["row_index"])
    else:
        if sample_index is None or sample_index < 0 or sample_index >= len(index_df):
            raise ValueError(f"sample_index must be between 0 and {len(index_df) - 1}.")
        row = index_df.iloc[int(sample_index)]

    X = np.load(DATASET_DIR / "X_sequence.npy")
    y = np.load(DATASET_DIR / "y_sequence.npy")
    if X.shape != (80, EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM):
        raise ValueError(f"Unexpected X_sequence shape: {X.shape}")
    label_mapping = _load_json(DATASET_DIR / "temporal_label_mapping.json")
    class_names = _class_names(label_mapping)
    resolved_index = int(sample_index)
    metadata = {
        "sample_index": resolved_index,
        "row_index": int(row["row_index"]),
        "video_id": str(row["video_id"]),
        "file_name": str(row["file_name"]),
        "source_file": str(row["source_file"]),
        "true_label_name": class_names[int(y[resolved_index])],
        "sequence_path": str(row["sequence_path"]),
    }
    return X[resolved_index], metadata
