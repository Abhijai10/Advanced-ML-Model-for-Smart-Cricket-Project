"""API response schemas for Smart Cricket Phase 13."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
    debug_metadata: dict[str, Any]
    source_metadata: dict[str, Any]
    prediction: dict[str, Any]
    segmentation: dict[str, Any]
    timing: dict[str, Any] = Field(default_factory=dict)
    voice_output: dict[str, Any]
    api_metadata: dict[str, Any]


class ErrorResponse(BaseModel):
    """Stable API error shape."""

    detail: str
    error_code: str
    debug_metadata: dict[str, Any] = Field(default_factory=dict)
