"""FastAPI routes for Smart Cricket Phase 13."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from .schemas import AnalyzeResponse, HealthResponse
from .services import APIValidationError, analyze_uploaded_video, api_health


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    """Return a lightweight service health response."""
    return api_health()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(file: UploadFile = File(...)) -> dict:
    """Analyze one uploaded cricket batting video."""
    try:
        return analyze_uploaded_video(file)
    except APIValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": str(exc),
                "error_code": exc.error_code,
                "debug_metadata": {"filename": file.filename},
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "detail": "Smart Cricket analysis failed unexpectedly.",
                "error_code": "analysis_failed",
                "debug_metadata": {"error_type": type(exc).__name__},
            },
        ) from exc
