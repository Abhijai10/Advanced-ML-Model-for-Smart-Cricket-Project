"""FastAPI routes for Smart Cricket API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from .config import SETTINGS
from .schemas import AnalyzeResponse, HealthResponse, ReadyResponse
from .services import (
    APIValidationError,
    analyze_dataset_sample,
    analyze_uploaded_video,
    api_health,
    api_readiness,
    enforce_auth,
    enforce_rate_limit,
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
    _auth: None = Depends(enforce_auth),
) -> dict:
    """Analyze one uploaded cricket batting video from its actual bytes."""
    try:
        return analyze_uploaded_video(file, request_id=request.state.request_id)
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
