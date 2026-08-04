"""FastAPI routes for Smart Cricket API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from .config import SETTINGS
from .persistence import build_feedback_record, persist_feedback_record
from .schemas import AnalyzeResponse, FeedbackRequest, FeedbackResponse, HealthResponse, ReadyResponse
from .services import (
    APIValidationError,
    AuthContext,
    analyze_dataset_sample,
    analyze_uploaded_video,
    api_health,
    api_readiness,
    enforce_auth,
    enforce_rate_limit,
    persist_verified_analysis_for_auth_user,
)


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    """Return a lightweight service health response."""
    return api_health()


@router.get("/ready", response_model=ReadyResponse)
def ready() -> dict:
    """Return runtime readiness checks for inference dependencies."""
    payload = api_readiness()
    if payload["status"] != "ready":
        raise HTTPException(status_code=503, detail=payload)
    return payload


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: Request,
    file: UploadFile = File(...),
    _rate_limit: None = Depends(enforce_rate_limit),
    auth: AuthContext = Depends(enforce_auth),
) -> dict:
    """Analyze one uploaded cricket batting video from its actual bytes."""
    try:
        result = analyze_uploaded_video(file, request_id=request.state.request_id)
        persist_verified_analysis_for_auth_user(
            auth=auth,
            result=result,
            filename=result["api_metadata"]["upload_filename"],
            request_id=request.state.request_id,
        )
        return result
    except APIValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": str(exc),
                "error_code": exc.error_code,
                "request_id": request.state.request_id,
                "debug_metadata": {"filename": file.filename},
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "detail": "Smart Cricket analysis failed unexpectedly.",
                "error_code": "analysis_failed",
                "request_id": request.state.request_id,
                "debug_metadata": {"error_type": type(exc).__name__},
            },
        ) from exc


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    request: Request,
    _rate_limit: None = Depends(enforce_rate_limit),
    auth: AuthContext = Depends(enforce_auth),
) -> dict:
    """Accept controlled-beta feedback without treating it as ground truth."""
    try:
        row = build_feedback_record(
            payload=payload,
            user_id=auth.user_id,
            request_id=request.state.request_id,
            authorization_present=auth.authorization_present,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": str(exc),
                "error_code": "invalid_feedback",
                "request_id": request.state.request_id,
            },
        ) from exc

    outcome = persist_feedback_record(row)
    return {
        "status": "accepted",
        "feedback_id": row["id"],
        "accepted_for_review": bool(row["accepted_for_review"]),
        "stored": outcome.stored,
        "duplicate_clip_hash": outcome.duplicate,
        "request_id": request.state.request_id,
        "message": (
            "Feedback was queued for human review."
            if row["accepted_for_review"]
            else "Feedback was recorded as product feedback only because model-improvement consent was not granted."
        ),
    }


@router.post("/dev/analyze-dataset", response_model=AnalyzeResponse)
def dev_analyze_dataset(
    request: Request,
    sample_index: int | None = None,
    file_name: str | None = None,
) -> dict:
    """Analyze a stored dataset sequence for local validation only."""
    if not SETTINGS.dev_dataset_endpoints:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": "Dataset sample analysis is disabled.",
                "error_code": "dev_endpoint_disabled",
                "request_id": request.state.request_id,
            },
        )
    try:
        return analyze_dataset_sample(
            sample_index=sample_index,
            file_name=file_name,
            request_id=request.state.request_id,
        )
    except APIValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": str(exc),
                "error_code": exc.error_code,
                "request_id": request.state.request_id,
            },
        ) from exc
