"""Stable JSON result schema for Phase 12 analysis outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PredictionResult:
    """Shot classification result."""

    predicted_shot: str
    shot_confidence: float
    class_probabilities: dict[str, float]


@dataclass(frozen=True)
class SegmentResult:
    """Shot segmentation and prediction-gating result."""

    start_frame: int | None
    end_frame: int | None
    peak_frame: int | None
    prediction_trigger_frame: int | None
    completed: bool
    completion_reason: str | None
    trigger_count: int


@dataclass(frozen=True)
class AnalysisResult:
    """Complete Phase 12 offline analysis result."""

    predicted_shot: str
    shot_confidence: float
    technique_match_score: float
    detected_issues: list[dict[str, Any]]
    coaching_tips: list[str]
    detailed_feedback: str
    spoken_feedback: str
    debug_metadata: dict[str, Any]
    prediction: PredictionResult
    segmentation: SegmentResult
    source_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
