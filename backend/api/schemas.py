"""API response schemas for Smart Cricket Phase 13."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health-check response for backend/API readiness."""

    status: str = "ok"
    service: str = "smart_cricket_api"
    phase: str = "Phase 13"
    inference_ready: bool
    version: str


class ReadyResponse(BaseModel):
    """Readiness response with dependency checks."""

    status: str
    service: str
    version: str
    checks: dict[str, dict[str, Any]]


class AnalyzeResponse(BaseModel):
    """Frontend-consumable analysis response."""

    predicted_shot: str
    shot_confidence: float = Field(ge=0.0, le=1.0)
    technique_match_score: float = Field(ge=0.0, le=100.0)
    detected_issues: list[dict[str, Any]]
    coaching_tips: list[str]
    detailed_feedback: str
    spoken_feedback: str
    analysis_quality: dict[str, Any] = Field(default_factory=dict)
    debug_metadata: dict[str, Any]
    source_metadata: dict[str, Any]
    prediction: dict[str, Any]
    segmentation: dict[str, Any]
    timing: dict[str, Any] = Field(default_factory=dict)
    voice_output: dict[str, Any]
    api_metadata: dict[str, Any]


class EvidenceDeletionResponse(BaseModel):
    """Response for consent-withdrawal and evidence deletion operations."""

    status: str
    analysis_session_id: str
    evidence_deleted: bool
    training_eligibility_disabled: bool
    request_id: str


class FeedbackRequest(BaseModel):
    """Controlled-beta user feedback on one analysis result.

    The client may describe what it saw, but cannot set trusted ownership,
    request, review, or training fields.
    """

    model_config = ConfigDict(extra="forbid")

    analysis_session_id: str | None = Field(default=None, max_length=128)
    prediction_was_correct: str = Field(pattern=r"^(correct|incorrect|unsure)$")
    corrected_shot: str | None = None
    technique_feedback_rating: int | None = Field(default=None, ge=1, le=5)
    tip_flags: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)
    consent_to_model_improvement: bool
    client_analysis_id: str | None = Field(default=None, max_length=128)


class FeedbackResponse(BaseModel):
    """Response for a feedback submission."""

    status: str
    storage_status: str
    feedback_id: str | None = None
    accepted_for_review: bool
    stored: bool
    duplicate_clip_hash: bool
    request_id: str
    message: str


class ProductFeedbackRequest(BaseModel):
    """General app/product feedback, never model-training data."""

    model_config = ConfigDict(extra="forbid")

    usability_rating: int | None = Field(default=None, ge=1, le=5)
    bug_category: str | None = Field(default=None, max_length=120)
    feature_request: str | None = Field(default=None, max_length=500)
    notes: str = Field(min_length=1, max_length=2000)
    page_context: str | None = Field(default=None, max_length=120)


class ErrorResponse(BaseModel):
    """Stable API error shape."""

    detail: str
    error_code: str
    debug_metadata: dict[str, Any] = Field(default_factory=dict)
