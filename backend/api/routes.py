"""FastAPI routes for Smart Cricket API."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile

from .config import SETTINGS
from .evidence import get_evidence_provider
from .persistence import (
    build_feedback_record,
    is_persistence_configured,
    load_analysis_session,
    mark_analysis_withdrawn_or_deleted,
    mark_feedback_withdrawn_or_deleted,
    persist_feedback_record,
)
from .schemas import AnalyzeResponse, EvidenceDeletionResponse, FeedbackRequest, FeedbackResponse, HealthResponse, ProductFeedbackRequest, ReadyResponse
from .services import (
    AnalysisOverloadError,
    AnalysisTimeoutError,
    APIValidationError,
    AuthContext,
    analyze_dataset_sample,
    analyze_uploaded_video_with_retention,
    api_health,
    api_readiness,
    enforce_auth,
    enforce_feedback_rate_limit,
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
    retain_evidence: bool = Form(default=False),
    _rate_limit: None = Depends(enforce_rate_limit),
    auth: AuthContext = Depends(enforce_auth),
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
    response: Response,
    _rate_limit: None = Depends(enforce_feedback_rate_limit),
    auth: AuthContext = Depends(enforce_auth),
) -> dict:
    """Accept controlled-beta feedback without treating it as ground truth."""
    if not is_persistence_configured():
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
            "message": "This feedback candidate was already saved for review.",
        }
    if not outcome.stored:
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
        "message": (
            "Feedback was saved and queued for human review."
            if row["accepted_for_review"]
            else "Feedback was saved as product feedback only because model-improvement consent was not granted."
        ),
    }


@router.post("/product-feedback", response_model=FeedbackResponse)
def submit_product_feedback(
    payload: ProductFeedbackRequest,
    request: Request,
    response: Response,
    _rate_limit: None = Depends(enforce_feedback_rate_limit),
    auth: AuthContext = Depends(enforce_auth),
) -> dict:
    """Accept general product feedback that can never enter model training."""
    if not is_persistence_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "detail": "Product feedback storage is not configured, so this feedback was not saved.",
                "error_code": "persistence_not_configured",
                "request_id": request.state.request_id,
            },
        )
    row = {
        "id": str(uuid4()),
        "user_id": auth.user_id,
        "analysis_session_id": None,
        "prediction_was_correct": "unsure",
        "corrected_shot": None,
        "technique_feedback_rating": payload.usability_rating,
        "tip_flags": [],
        "notes": payload.notes,
        "consent_to_model_improvement": False,
        "accepted_for_review": False,
        "review_status": "product_feedback",
        "dataset_eligibility_status": "not_eligible",
        "storage_status": "metadata_only",
        "evidence_metadata": {
            "feedback_type": "general_product_feedback",
            "bug_category": payload.bug_category,
            "feature_request": payload.feature_request,
            "page_context": payload.page_context,
        },
        "request_id": request.state.request_id,
        "auth_present": auth.authorization_present,
    }
    outcome = persist_feedback_record(row)
    if not outcome.stored:
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
    mark_analysis_withdrawn_or_deleted(analysis_session_id=analysis_session_id, user_id=auth.user_id, deleted=False)
    mark_feedback_withdrawn_or_deleted(analysis_session_id=analysis_session_id, user_id=auth.user_id, deleted=False)
    return {
        "status": "withdrawn",
        "analysis_session_id": analysis_session_id,
        "evidence_deleted": False,
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
    object_path = record.get("evidence_object_path")
    deleted = False
    if object_path:
        outcome = get_evidence_provider().delete(str(object_path))
        deleted = outcome.status == "deleted"
        if outcome.status not in {"deleted", "not_found"}:
            raise HTTPException(status_code=503, detail={"detail": "Retained evidence could not be deleted right now.", "error_code": outcome.error_code or "evidence_delete_failed", "request_id": request.state.request_id})
    mark_analysis_withdrawn_or_deleted(analysis_session_id=analysis_session_id, user_id=auth.user_id, deleted=True)
    mark_feedback_withdrawn_or_deleted(analysis_session_id=analysis_session_id, user_id=auth.user_id, deleted=True)
    return {
        "status": "deleted",
        "analysis_session_id": analysis_session_id,
        "evidence_deleted": deleted,
        "training_eligibility_disabled": True,
        "request_id": request.state.request_id,
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
