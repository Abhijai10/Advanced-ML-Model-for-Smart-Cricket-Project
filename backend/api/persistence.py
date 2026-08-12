"""Optional server-side persistence for trusted Smart Cricket records."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .config import SETTINGS
from .evidence import evidence_is_reviewable


SUPPORTED_SHOTS = {"cover_drive", "defensive_shot", "pull_shot", "sweep_shot"}
TIP_FLAGS = {"useful", "incorrect", "unsafe", "unclear"}


@dataclass(frozen=True)
class PersistenceResult:
    """Outcome from an optional persistence operation."""

    stored: bool
    status: str
    record_id: str | None = None
    duplicate: bool = False
    error_code: str | None = None
    record: dict[str, Any] | None = None


def is_persistence_configured() -> bool:
    """Return whether backend-only Supabase writes can be attempted."""
    return bool(SETTINGS.supabase_url and SETTINGS.supabase_service_role_key)


def _postgrest_insert(table: str, row: dict[str, Any]) -> PersistenceResult:
    if not is_persistence_configured():
        return PersistenceResult(stored=False, status="persistence_not_configured", error_code="persistence_not_configured")

    url = f"{SETTINGS.supabase_url.rstrip('/')}/rest/v1/{table}"
    body = json.dumps(row).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "apikey": SETTINGS.supabase_service_role_key or "",
            "authorization": f"Bearer {SETTINGS.supabase_service_role_key}",
            "content-type": "application/json",
            "prefer": "return=representation",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=SETTINGS.persistence_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8") or "[]")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 409 or "duplicate key" in detail.lower():
            return PersistenceResult(stored=False, status="duplicate", duplicate=True, error_code="duplicate_record")
        status = "temporary_failure" if exc.code in {408, 429, 500, 502, 503, 504} else "failed"
        return PersistenceResult(stored=False, status=status, error_code=f"supabase_http_{exc.code}")
    except Exception:
        return PersistenceResult(stored=False, status="temporary_failure", error_code="persistence_failed")

    record_id = None
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        record_id = str(payload[0].get("id") or "")
    record = payload[0] if isinstance(payload, list) and payload and isinstance(payload[0], dict) else None
    return PersistenceResult(stored=True, status="stored", record_id=record_id or row.get("id"), record=record)


def _postgrest_select_one(table: str, filters: dict[str, str]) -> PersistenceResult:
    if not is_persistence_configured():
        return PersistenceResult(stored=False, status="persistence_not_configured", error_code="persistence_not_configured")

    query = urllib.parse.urlencode({key: f"eq.{value}" for key, value in filters.items()})
    request = urllib.request.Request(
        f"{SETTINGS.supabase_url.rstrip('/')}/rest/v1/{table}?select=*&{query}&limit=1",
        method="GET",
        headers={
            "apikey": SETTINGS.supabase_service_role_key or "",
            "authorization": f"Bearer {SETTINGS.supabase_service_role_key}",
            "accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=SETTINGS.persistence_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8") or "[]")
    except urllib.error.HTTPError as exc:
        status = "temporary_failure" if exc.code in {408, 429, 500, 502, 503, 504} else "failed"
        return PersistenceResult(stored=False, status=status, error_code=f"supabase_http_{exc.code}")
    except Exception:
        return PersistenceResult(stored=False, status="temporary_failure", error_code="persistence_failed")

    if not isinstance(payload, list) or not payload:
        return PersistenceResult(stored=False, status="not_found", error_code="analysis_not_found")
    if not isinstance(payload[0], dict):
        return PersistenceResult(stored=False, status="failed", error_code="unexpected_response")
    return PersistenceResult(stored=True, status="stored", record_id=str(payload[0].get("id") or ""), record=payload[0])


def _postgrest_select_many(table: str, query_params: dict[str, str]) -> PersistenceResult:
    if not is_persistence_configured():
        return PersistenceResult(stored=False, status="persistence_not_configured", error_code="persistence_not_configured")
    query = urllib.parse.urlencode(query_params)
    request = urllib.request.Request(
        f"{SETTINGS.supabase_url.rstrip('/')}/rest/v1/{table}?select=*&{query}",
        method="GET",
        headers={
            "apikey": SETTINGS.supabase_service_role_key or "",
            "authorization": f"Bearer {SETTINGS.supabase_service_role_key}",
            "accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=SETTINGS.persistence_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8") or "[]")
    except urllib.error.HTTPError as exc:
        status = "temporary_failure" if exc.code in {408, 429, 500, 502, 503, 504} else "failed"
        return PersistenceResult(stored=False, status=status, error_code=f"supabase_http_{exc.code}")
    except Exception:
        return PersistenceResult(stored=False, status="temporary_failure", error_code="persistence_failed")
    if not isinstance(payload, list):
        return PersistenceResult(stored=False, status="failed", error_code="unexpected_response")
    return PersistenceResult(stored=True, status="stored", record=payload)


def _postgrest_patch(table: str, filters: dict[str, str], row: dict[str, Any]) -> PersistenceResult:
    if not is_persistence_configured():
        return PersistenceResult(stored=False, status="persistence_not_configured", error_code="persistence_not_configured")
    query = urllib.parse.urlencode({key: f"eq.{value}" for key, value in filters.items()})
    request = urllib.request.Request(
        f"{SETTINGS.supabase_url.rstrip('/')}/rest/v1/{table}?{query}",
        data=json.dumps(row).encode("utf-8"),
        method="PATCH",
        headers={
            "apikey": SETTINGS.supabase_service_role_key or "",
            "authorization": f"Bearer {SETTINGS.supabase_service_role_key}",
            "content-type": "application/json",
            "prefer": "return=representation",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=SETTINGS.persistence_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8") or "[]")
    except urllib.error.HTTPError as exc:
        status = "temporary_failure" if exc.code in {408, 429, 500, 502, 503, 504} else "failed"
        return PersistenceResult(stored=False, status=status, error_code=f"supabase_http_{exc.code}")
    except Exception:
        return PersistenceResult(stored=False, status="temporary_failure", error_code="persistence_failed")
    if not isinstance(payload, list):
        return PersistenceResult(stored=False, status="failed", error_code="unexpected_response")
    if not payload:
        return PersistenceResult(stored=False, status="not_found", error_code="record_not_found")
    record = payload[0] if isinstance(payload[0], dict) else None
    if record is None:
        return PersistenceResult(stored=False, status="failed", error_code="unexpected_response")
    return PersistenceResult(stored=True, status="stored", record_id=str((record or {}).get("id") or ""), record=record)


def persist_analysis_session(
    *,
    user_id: str | None,
    result: dict[str, Any],
    filename: str,
    request_id: str,
    clip_hash: str,
    provenance: dict[str, Any],
    analysis_session_id: str | None = None,
    evidence_outcome: Any | None = None,
) -> PersistenceResult:
    """Persist a verified analysis response as server-owned history when configured."""
    if not user_id:
        return PersistenceResult(stored=False, status="missing_user", error_code="missing_user")
    segment = result.get("segmentation", {}) if isinstance(result.get("segmentation"), dict) else {}
    timing = result.get("timing", {}) if isinstance(result.get("timing"), dict) else {}
    evidence_metadata = evidence_outcome.metadata if evidence_outcome and evidence_outcome.metadata else {
        "storage_backend": SETTINGS.evidence_storage_backend,
        "raw_clip_retained": False,
        "processed_evidence_retained": False,
        "external_storage_verification": "not_configured",
    }
    row = {
        "id": analysis_session_id or str(uuid4()),
        "user_id": user_id,
        "video_file_name": filename,
        "predicted_shot": result.get("predicted_shot"),
        "shot_confidence": result.get("shot_confidence"),
        "technique_match_score": result.get("technique_match_score"),
        "shot_start_frame": segment.get("start_frame"),
        "shot_end_frame": segment.get("end_frame"),
        "shot_duration_seconds": timing.get("duration_seconds"),
        "spoken_feedback": result.get("spoken_feedback"),
        "coaching_tips": result.get("coaching_tips") or [],
        "full_result": result,
        "request_id": request_id,
        "clip_hash": clip_hash,
        "model_version": (result.get("debug_metadata") or {}).get("model_version"),
        "pipeline_version": (result.get("api_metadata") or {}).get("pipeline_version"),
        "model_provenance": provenance,
        "checkpoint_sha256": provenance.get("checkpoint_sha256"),
        "feature_contract_version": provenance.get("feature_contract_version"),
        "feature_schema_sha256": provenance.get("feature_schema_sha256"),
        "scaler_mean_sha256": provenance.get("scaler_mean_sha256"),
        "scaler_std_sha256": provenance.get("scaler_std_sha256"),
        "label_mapping_sha256": provenance.get("label_mapping_sha256"),
        "scoring_template_sha256": provenance.get("scoring_template_sha256"),
        "feedback_engine_version": provenance.get("feedback_engine_version"),
        "storage_status": evidence_outcome.status if evidence_outcome else "not_retained",
        "consent_scope": "model_improvement_raw_clip" if evidence_outcome and evidence_outcome.retained else "none",
        "consent_version": SETTINGS.consent_version if evidence_outcome and evidence_outcome.retained else None,
        "consented_at": evidence_metadata.get("created_at") if evidence_outcome and evidence_outcome.retained else None,
        "retention_expires_at": evidence_metadata.get("retention_expires_at") if evidence_outcome and evidence_outcome.retained else None,
        "evidence_object_path": evidence_outcome.object_path if evidence_outcome else None,
        "evidence_metadata": evidence_metadata,
        "withdrawn_at": None,
        "deleted_at": None,
        "persistence_source": "server_verified_inference",
    }
    return _postgrest_insert("analysis_sessions", row)


def load_analysis_session(*, analysis_session_id: str, user_id: str) -> PersistenceResult:
    """Load a trusted server-created analysis for feedback binding."""
    return _postgrest_select_one("analysis_sessions", {"id": analysis_session_id, "user_id": user_id})


def list_evidence_cleanup_candidates(*, now_iso: str, limit: int = 100) -> PersistenceResult:
    """List retained analyses whose evidence should no longer be accessible."""
    return _postgrest_select_many(
        "analysis_sessions",
        {
            "storage_status": "in.(stored,deletion_pending)",
            "retention_expires_at": f"lte.{now_iso}",
            "limit": str(max(1, min(limit, 1000))),
            "order": "retention_expires_at.asc",
        },
    )


def list_feedback_review_candidates(*, now_iso: str, limit: int = 100) -> PersistenceResult:
    """List user-consented feedback rows that are pending human review."""
    return _postgrest_select_many(
        "analysis_feedback",
        {
            "accepted_for_review": "eq.true",
            "consent_to_model_improvement": "eq.true",
            "review_status": "eq.candidate",
            "dataset_eligibility_status": "eq.pending_review",
            "storage_status": "eq.stored",
            "withdrawn_at": "is.null",
            "deleted_at": "is.null",
            "retention_expires_at": f"gt.{now_iso}",
            "order": "created_at.asc",
            "limit": str(max(1, min(limit, 1000))),
        },
    )


def record_feedback_review_decision(
    *,
    feedback_id: str,
    reviewer_id: str,
    reviewer_label: str | None,
    label_quality_score: float | None,
    second_review_required: bool,
    disagreement_notes: str | None,
    rejection_reason: str | None,
    unsafe_content_flag: bool,
    split_assignment: str | None,
    training_inclusion_version: str | None,
    approved: bool,
) -> PersistenceResult:
    """Record a trusted reviewer decision for one feedback candidate."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    review_status = "approved" if approved else "rejected"
    row = {
        "reviewer_id": reviewer_id,
        "reviewed_at": now,
        "reviewer_label": reviewer_label,
        "label_quality_score": label_quality_score,
        "second_review_required": second_review_required,
        "disagreement_notes": disagreement_notes,
        "rejection_reason": rejection_reason,
        "unsafe_content_flag": unsafe_content_flag,
        "split_assignment": split_assignment if approved else None,
        "training_inclusion_version": training_inclusion_version if approved else None,
        "review_status": review_status,
        "dataset_eligibility_status": "eligible" if approved and not unsafe_content_flag else "rejected",
        "accepted_for_review": bool(approved and not unsafe_content_flag),
    }
    return _postgrest_patch("analysis_feedback", {"id": feedback_id}, row)


def mark_analysis_withdrawn_or_deleted(
    *,
    analysis_session_id: str,
    user_id: str,
    deleted: bool = False,
    deletion_pending: bool = False,
    deletion_error_code: str | None = None,
    evidence_metadata: dict[str, Any] | None = None,
) -> PersistenceResult:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    storage_status = "deleted" if deleted else "deletion_pending" if deletion_pending else "withdrawn"
    row = {
        "withdrawn_at": now,
        "storage_status": storage_status,
        "consent_scope": "withdrawn",
        "deleted_at": now if deleted else None,
    }
    if deletion_error_code:
        row["evidence_metadata"] = {
            **(evidence_metadata or {}),
            "deletion_error_code": deletion_error_code,
            "deletion_attempted_at": now,
        }
    return _postgrest_patch("analysis_sessions", {"id": analysis_session_id, "user_id": user_id}, row)


def mark_feedback_withdrawn_or_deleted(
    *,
    analysis_session_id: str,
    user_id: str,
    deleted: bool = False,
    deletion_pending: bool = False,
) -> PersistenceResult:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    terminal_status = "deleted" if deleted else "deletion_pending" if deletion_pending else "withdrawn"
    row = {
        "withdrawn_at": now,
        "deleted_at": now if deleted else None,
        "review_status": terminal_status,
        "dataset_eligibility_status": "deleted" if deleted else "withdrawn",
        "accepted_for_review": False,
    }
    return _postgrest_patch("analysis_feedback", {"analysis_session_id": analysis_session_id, "user_id": user_id}, row)


def build_feedback_record(
    *,
    payload: Any,
    user_id: str | None,
    request_id: str,
    authorization_present: bool,
    analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    """Create a trusted feedback row from a validated client payload."""
    corrected_shot = payload.corrected_shot
    predicted_shot = (analysis or {}).get("predicted_shot")
    if predicted_shot not in SUPPORTED_SHOTS:
        raise ValueError("The bound analysis does not contain a supported Smart Cricket label.")
    if corrected_shot is not None and corrected_shot not in SUPPORTED_SHOTS:
        raise ValueError("corrected_shot is not a supported Smart Cricket label.")
    if payload.prediction_was_correct == "incorrect" and corrected_shot is None:
        raise ValueError("corrected_shot is required when marking a prediction incorrect.")
    invalid_flags = sorted(set(payload.tip_flags) - TIP_FLAGS)
    if invalid_flags:
        raise ValueError(f"Unsupported tip flag(s): {', '.join(invalid_flags)}.")

    consent = bool(payload.consent_to_model_improvement)
    if consent and not user_id:
        raise ValueError("Authentication is required for model-improvement feedback.")
    if consent and not analysis:
        raise ValueError("A verified analysis session is required for model-improvement feedback.")
    provenance = (analysis or {}).get("model_provenance") if isinstance((analysis or {}).get("model_provenance"), dict) else {}
    clip_hash = (analysis or {}).get("clip_hash")
    reviewable_evidence = bool(
        consent
        and SETTINGS.allow_model_improvement_participation
        and analysis
        and evidence_is_reviewable(analysis)
    )
    if consent and analysis and not reviewable_evidence:
        storage_state = (analysis or {}).get("storage_status") or "not_retained"
        review_status = "evidence_not_retained" if storage_state in {"not_retained", "deleted", "withdrawn", "deletion_pending"} else "awaiting_evidence"
    elif consent:
        review_status = "candidate"
    else:
        review_status = "not_consented"
    retention_deadline = (analysis or {}).get("retention_expires_at") if consent else None
    return {
        "id": str(uuid4()),
        "user_id": user_id,
        "analysis_session_id": payload.analysis_session_id,
        "client_analysis_id": payload.client_analysis_id,
        "clip_hash": str(clip_hash).lower() if clip_hash else None,
        "predicted_shot": predicted_shot,
        "prediction_was_correct": payload.prediction_was_correct,
        "corrected_shot": corrected_shot,
        "technique_feedback_rating": payload.technique_feedback_rating,
        "tip_flags": payload.tip_flags,
        "notes": payload.notes,
        "consent_to_model_improvement": consent,
        "accepted_for_review": reviewable_evidence,
        "review_status": review_status,
        "model_version": provenance.get("model_version"),
        "pipeline_version": provenance.get("pipeline_version"),
        "feature_contract_version": provenance.get("feature_contract_version"),
        "feature_schema_sha256": provenance.get("feature_schema_sha256"),
        "checkpoint_sha256": provenance.get("checkpoint_sha256"),
        "request_id": request_id,
        "auth_present": authorization_present,
        "consent_version": SETTINGS.consent_version if consent else None,
        "consented_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") if consent else None,
        "retention_expires_at": retention_deadline,
        "storage_status": (analysis or {}).get("storage_status") or "not_retained",
        "evidence_object_path": (analysis or {}).get("evidence_object_path"),
        "evidence_metadata": (analysis or {}).get("evidence_metadata") or {},
        "dataset_eligibility_status": "pending_review" if reviewable_evidence else "not_eligible",
        "provenance_completeness_score": 1.0 if reviewable_evidence and provenance else 0.0,
        "label_quality_score": None,
        "provenance": {
            "source": "user_reported_feedback",
            "ground_truth": False,
            "requires_expert_review": True,
            "ai_assisted_review_allowed": True,
            "ai_is_ground_truth": False,
            "analysis_session_verified": bool(analysis),
            "reviewable_evidence": reviewable_evidence,
        },
    }


def persist_feedback_record(row: dict[str, Any]) -> PersistenceResult:
    """Persist a beta feedback record if Supabase server credentials are configured."""
    return _postgrest_insert("analysis_feedback", row)


def build_product_feedback_record(
    *,
    payload: Any,
    user_id: str | None,
    request_id: str,
) -> dict[str, Any]:
    """Create a general product-feedback row that is outside ML training tables."""
    return {
        "id": str(uuid4()),
        "user_id": user_id,
        "usability_rating": payload.usability_rating,
        "bug_category": payload.bug_category,
        "feature_request": payload.feature_request,
        "notes": payload.notes,
        "page_context": payload.page_context,
        "request_id": request_id,
        "status": "new",
    }


def persist_product_feedback_record(row: dict[str, Any]) -> PersistenceResult:
    """Persist general product feedback in its dedicated non-ML table."""
    return _postgrest_insert("product_feedback", row)
