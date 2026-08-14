"""FastAPI routes for Smart Cricket API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import PlainTextResponse

from .config import SETTINGS
from .evidence import delete_evidence_for_record
from .observability import METRICS
from .persistence import (
    build_product_feedback_record,
    build_feedback_record,
    is_persistence_configured,
    load_analysis_session,
    mark_analysis_withdrawn_or_deleted,
    mark_feedback_withdrawn_or_deleted,
    persist_feedback_record,
    persist_product_feedback_record,
)
from .schemas import AnalyzeResponse, CapabilitiesResponse, EvidenceDeletionResponse, FeedbackRequest, FeedbackResponse, HealthResponse, ProductFeedbackRequest, ReadyResponse
from .services import (
    AnalysisOverloadError,
    AnalysisTimeoutError,
    AnalysisWorkerError,
    APIValidationError,
    AuthContext,
    analyze_dataset_sample,
    analyze_uploaded_video_with_retention,
    api_health,
    api_readiness,
    enforce_auth,
    enforce_feedback_rate_limit,
    enforce_rate_limit,
    PHASE13_VERSION,
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


@router.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities() -> dict:
    """Return non-secret product capabilities for frontend controls."""
    return {
        "auth_required": SETTINGS.require_auth,
        "feedback_enabled": is_persistence_configured(),
        "model_improvement_enabled": SETTINGS.allow_model_improvement_participation,
        "evidence_retention_enabled": SETTINGS.allow_model_improvement_participation
        and SETTINGS.evidence_storage_backend.strip().lower() in {"local", "supabase"},
        "tts_provider": SETTINGS.tts_provider.strip().lower() if SETTINGS.tts_enabled else "text_only",
        "audio_storage_backend": SETTINGS.audio_storage_backend.strip().lower(),
        "max_upload_bytes": SETTINGS.max_upload_bytes,
        "max_recording_duration_seconds": SETTINGS.max_video_duration_seconds,
        "accepted_video_extensions": [".avi", ".mkv", ".mov", ".mp4", ".webm"],
        "api_version": PHASE13_VERSION,
    }


@router.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    """Return local Prometheus-compatible metrics."""

    return METRICS.render_prometheus()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: Request,
    file: UploadFile = File(...),
    retain_evidence: bool = Form(default=False),
    auth: AuthContext = Depends(enforce_auth),
    _rate_limit: None = Depends(enforce_rate_limit),
) -> dict:
    """Analyze one uploaded cricket batting video from its actual bytes."""
    try:
        result, evidence_outcome = analyze_uploaded_video_with_retention(
            file,
            request_id=request.state.request_id,
            auth=auth,
            retain_evidence=retain_evidence,
        )
        persist_verified_analysis_for_auth_user(
            auth=auth,
            result=result,
            filename=result["api_metadata"]["upload_filename"],
            request_id=request.state.request_id,
            analysis_session_id=result["api_metadata"].get("planned_analysis_session_id"),
            evidence_outcome=evidence_outcome,
        )
        return result
    except AnalysisOverloadError as exc:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": str(max(1, SETTINGS.analysis_queue_timeout_seconds))},
            detail={
                "detail": str(exc),
                "error_code": exc.error_code,
                "request_id": request.state.request_id,
            },
        ) from exc
    except AnalysisTimeoutError as exc:
        raise HTTPException(
            status_code=503,
            headers={"Retry-After": "10"},
            detail={
                "detail": str(exc),
                "error_code": exc.error_code,
                "request_id": request.state.request_id,
            },
        ) from exc
    except AnalysisWorkerError as exc:
        raise HTTPException(
            status_code=503,
            headers={"Retry-After": "10"},
            detail={
                "detail": "Smart Cricket inference worker failed safely. Try again with a clearer, shorter clip.",
                "error_code": exc.error_code,
                "request_id": request.state.request_id,
            },
        ) from exc
    except APIValidationError as exc:
        METRICS.increment("smart_cricket_upload_rejection", error_code=exc.error_code)
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
    response: Response,
    auth: AuthContext = Depends(enforce_auth),
    _rate_limit: None = Depends(enforce_feedback_rate_limit),
) -> dict:
    """Accept controlled-beta feedback without treating it as ground truth."""
    if not is_persistence_configured():
        METRICS.increment("smart_cricket_feedback_failure", error_code="persistence_not_configured")
        raise HTTPException(
            status_code=503,
            detail={
                "detail": "Feedback storage is not configured, so this feedback was not saved.",
                "error_code": "persistence_not_configured",
                "request_id": request.state.request_id,
            },
        )
    if payload.consent_to_model_improvement and not auth.user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "detail": "Sign in before sharing feedback for model improvement.",
                "error_code": "auth_required_for_model_improvement",
                "request_id": request.state.request_id,
            },
        )
    analysis = None
    if payload.analysis_session_id:
        if not auth.user_id:
            raise HTTPException(
                status_code=401,
                detail={
                    "detail": "Sign in to submit feedback for a verified analysis.",
                    "error_code": "auth_required_for_analysis_feedback",
                    "request_id": request.state.request_id,
                },
            )
        lookup = load_analysis_session(analysis_session_id=payload.analysis_session_id, user_id=auth.user_id)
        if lookup.status == "not_found":
            raise HTTPException(
                status_code=404,
                detail={
                    "detail": "The analysis session was not found for this user.",
                    "error_code": "analysis_session_not_found",
                    "request_id": request.state.request_id,
                },
            )
        if not lookup.stored:
            raise HTTPException(
                status_code=503,
                detail={
                    "detail": "The analysis session could not be verified right now. Try again later.",
                    "error_code": lookup.error_code or "analysis_lookup_failed",
                    "request_id": request.state.request_id,
                },
            )
        analysis = lookup.record
    elif payload.consent_to_model_improvement:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "A verified analysis session is required for model-improvement feedback.",
                "error_code": "analysis_session_required",
                "request_id": request.state.request_id,
            },
        )

    try:
        row = build_feedback_record(
            payload=payload,
            user_id=auth.user_id,
            request_id=request.state.request_id,
            authorization_present=auth.authorization_present,
            analysis=analysis,
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
    message = _feedback_success_message(row)
    if outcome.status == "duplicate":
        response.status_code = 200
        return {
            "status": "duplicate",
            "storage_status": "duplicate",
            "feedback_id": None,
            "accepted_for_review": bool(row["accepted_for_review"]),
            "stored": False,
            "duplicate_clip_hash": True,
            "request_id": request.state.request_id,
            "message": _feedback_duplicate_message(row),
        }
    if not outcome.stored:
        METRICS.increment("smart_cricket_feedback_failure", error_code=outcome.error_code or outcome.status)
        raise HTTPException(
            status_code=503 if outcome.status in {"persistence_not_configured", "temporary_failure"} else 502,
            detail={
                "detail": "Feedback could not be saved durably. Please try again later.",
                "error_code": outcome.error_code or outcome.status,
                "storage_status": outcome.status,
                "request_id": request.state.request_id,
            },
        )
    response.status_code = 201
    return {
        "status": "stored",
        "storage_status": "stored",
        "feedback_id": row["id"],
        "accepted_for_review": bool(row["accepted_for_review"]),
        "stored": True,
        "duplicate_clip_hash": False,
        "request_id": request.state.request_id,
        "message": message,
    }


@router.post("/product-feedback", response_model=FeedbackResponse)
def submit_product_feedback(
    payload: ProductFeedbackRequest,
    request: Request,
    response: Response,
    auth: AuthContext = Depends(enforce_auth),
    _rate_limit: None = Depends(enforce_feedback_rate_limit),
) -> dict:
    """Accept general product feedback that can never enter model training."""
    if not is_persistence_configured():
        METRICS.increment("smart_cricket_feedback_failure", error_code="persistence_not_configured")
        raise HTTPException(
            status_code=503,
            detail={
                "detail": "Product feedback storage is not configured, so this feedback was not saved.",
                "error_code": "persistence_not_configured",
                "request_id": request.state.request_id,
            },
        )
    row = build_product_feedback_record(payload=payload, user_id=auth.user_id, request_id=request.state.request_id)
    outcome = persist_product_feedback_record(row)
    if not outcome.stored:
        METRICS.increment("smart_cricket_feedback_failure", error_code=outcome.error_code or outcome.status)
        raise HTTPException(
            status_code=503 if outcome.status in {"persistence_not_configured", "temporary_failure"} else 502,
            detail={
                "detail": "Product feedback could not be saved durably. Please try again later.",
                "error_code": outcome.error_code or outcome.status,
                "storage_status": outcome.status,
                "request_id": request.state.request_id,
            },
        )
    response.status_code = 201
    return {
        "status": "stored",
        "storage_status": "stored",
        "feedback_id": outcome.record_id,
        "accepted_for_review": False,
        "stored": True,
        "duplicate_clip_hash": False,
        "request_id": request.state.request_id,
        "message": "Product feedback was saved. It is not used as model-training data.",
    }


@router.post("/analysis/{analysis_session_id}/withdraw-consent", response_model=EvidenceDeletionResponse)
def withdraw_consent(
    analysis_session_id: str,
    request: Request,
    auth: AuthContext = Depends(enforce_auth),
) -> dict:
    """Withdraw model-improvement consent and permanently disable training eligibility."""
    if not auth.user_id:
        raise HTTPException(status_code=401, detail={"detail": "Sign in to withdraw consent.", "error_code": "missing_auth", "request_id": request.state.request_id})
    lookup = load_analysis_session(analysis_session_id=analysis_session_id, user_id=auth.user_id)
    if lookup.status == "not_found":
        raise HTTPException(status_code=404, detail={"detail": "Analysis session was not found.", "error_code": "analysis_session_not_found", "request_id": request.state.request_id})
    if not lookup.stored:
        raise HTTPException(status_code=503, detail={"detail": "Analysis session could not be verified.", "error_code": lookup.error_code or "analysis_lookup_failed", "request_id": request.state.request_id})
    delete_outcome = delete_evidence_for_record(lookup.record or {})
    deletion_success = delete_outcome.status in {"deleted", "already_deleted", "not_found"}
    analysis_update = mark_analysis_withdrawn_or_deleted(
        analysis_session_id=analysis_session_id,
        user_id=auth.user_id,
        deleted=delete_outcome.status in {"deleted", "already_deleted"},
        deletion_pending=not deletion_success,
        deletion_error_code=None if deletion_success else delete_outcome.error_code or delete_outcome.status,
        evidence_metadata=(lookup.record or {}).get("evidence_metadata") if isinstance((lookup.record or {}).get("evidence_metadata"), dict) else None,
    )
    feedback_update = mark_feedback_withdrawn_or_deleted(
        analysis_session_id=analysis_session_id,
        user_id=auth.user_id,
        deleted=delete_outcome.status in {"deleted", "already_deleted"},
        deletion_pending=not deletion_success,
    )
    if not analysis_update.stored:
        raise HTTPException(status_code=503, detail={"detail": "Consent withdrawal could not be saved durably.", "error_code": analysis_update.error_code or analysis_update.status, "request_id": request.state.request_id})
    if feedback_update.status not in {"stored", "not_found"}:
        raise HTTPException(status_code=503, detail={"detail": "Feedback eligibility could not be updated durably.", "error_code": feedback_update.error_code or feedback_update.status, "request_id": request.state.request_id})
    return {
        "status": "withdrawn" if deletion_success else "withdrawn_deletion_pending",
        "analysis_session_id": analysis_session_id,
        "evidence_deleted": delete_outcome.status in {"deleted", "already_deleted"},
        "training_eligibility_disabled": True,
        "request_id": request.state.request_id,
    }


@router.delete("/analysis/{analysis_session_id}/evidence", response_model=EvidenceDeletionResponse)
def delete_evidence(
    analysis_session_id: str,
    request: Request,
    auth: AuthContext = Depends(enforce_auth),
) -> dict:
    """Delete retained evidence for an owned analysis and disable training eligibility."""
    if not auth.user_id:
        raise HTTPException(status_code=401, detail={"detail": "Sign in to delete retained evidence.", "error_code": "missing_auth", "request_id": request.state.request_id})
    lookup = load_analysis_session(analysis_session_id=analysis_session_id, user_id=auth.user_id)
    if lookup.status == "not_found":
        raise HTTPException(status_code=404, detail={"detail": "Analysis session was not found.", "error_code": "analysis_session_not_found", "request_id": request.state.request_id})
    if not lookup.stored:
        raise HTTPException(status_code=503, detail={"detail": "Analysis session could not be verified.", "error_code": lookup.error_code or "analysis_lookup_failed", "request_id": request.state.request_id})
    record = lookup.record or {}
    outcome = delete_evidence_for_record(record)
    deleted = outcome.status in {"deleted", "already_deleted"}
    if outcome.status not in {"deleted", "already_deleted", "not_found"}:
        analysis_update = mark_analysis_withdrawn_or_deleted(
            analysis_session_id=analysis_session_id,
            user_id=auth.user_id,
            deleted=False,
            deletion_pending=True,
            deletion_error_code=outcome.error_code or outcome.status,
            evidence_metadata=record.get("evidence_metadata") if isinstance(record.get("evidence_metadata"), dict) else None,
        )
        mark_feedback_withdrawn_or_deleted(analysis_session_id=analysis_session_id, user_id=auth.user_id, deletion_pending=True)
        if not analysis_update.stored:
            raise HTTPException(status_code=503, detail={"detail": "Evidence deletion failure could not be recorded durably.", "error_code": analysis_update.error_code or analysis_update.status, "request_id": request.state.request_id})
        raise HTTPException(status_code=503, detail={"detail": "Retained evidence could not be deleted right now; it has been marked for cleanup retry.", "error_code": outcome.error_code or "evidence_delete_failed", "request_id": request.state.request_id})
    analysis_update = mark_analysis_withdrawn_or_deleted(analysis_session_id=analysis_session_id, user_id=auth.user_id, deleted=deleted)
    feedback_update = mark_feedback_withdrawn_or_deleted(analysis_session_id=analysis_session_id, user_id=auth.user_id, deleted=deleted)
    if not analysis_update.stored:
        raise HTTPException(status_code=503, detail={"detail": "Evidence deletion could not be saved durably.", "error_code": analysis_update.error_code or analysis_update.status, "request_id": request.state.request_id})
    if feedback_update.status not in {"stored", "not_found"}:
        raise HTTPException(status_code=503, detail={"detail": "Feedback eligibility could not be updated durably.", "error_code": feedback_update.error_code or feedback_update.status, "request_id": request.state.request_id})
    return {
        "status": "deleted" if deleted else "not_found",
        "analysis_session_id": analysis_session_id,
        "evidence_deleted": deleted,
        "training_eligibility_disabled": True,
        "request_id": request.state.request_id,
    }


def _feedback_success_message(row: dict) -> str:
    if row.get("accepted_for_review"):
        return "Feedback was saved and queued for human review."
    if not row.get("consent_to_model_improvement"):
        return "Feedback was saved as metadata only because model-improvement consent was not granted."
    review_status = row.get("review_status")
    if review_status == "evidence_not_retained":
        return "Feedback was saved, but no retained evidence is available, so it will not enter model-training review."
    if review_status == "awaiting_evidence":
        return "Feedback was saved, but evidence is not currently reviewable, so it is not queued for model-training review."
    return "Feedback was saved as metadata only and is not queued for model-training review."


def _feedback_duplicate_message(row: dict) -> str:
    if row.get("accepted_for_review"):
        return "This reviewable feedback candidate was already saved."
    if not row.get("consent_to_model_improvement"):
        return "This metadata-only feedback was already saved."
    return "This feedback was already saved, but it is not reviewable because retained evidence is unavailable."


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
