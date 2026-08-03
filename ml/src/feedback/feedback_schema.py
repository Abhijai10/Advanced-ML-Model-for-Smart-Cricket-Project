"""Structured output schema for Phase 11 coaching feedback."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DetectedIssue:
    """One measurable technique issue used to generate coaching feedback."""

    component_name: str
    feature_name: str
    statistic: str
    severity: str
    issue: str
    why_it_matters: str
    coaching_tip: str
    evidence: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FeedbackOutput:
    """Complete feedback output for one cricket shot sample."""

    file_name: str
    predicted_shot: str
    true_label_name: str
    technique_match_score: float
    classifier_confidence: float | None
    detected_issues: tuple[DetectedIssue, ...]
    coaching_tips: tuple[str, ...]
    detailed_feedback: str
    spoken_feedback: str
    debug_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["detected_issues"] = [issue.to_dict() for issue in self.detected_issues]
        return payload
