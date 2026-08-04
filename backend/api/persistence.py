"""Optional server-side persistence for trusted Smart Cricket records."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .config import SETTINGS


SUPPORTED_SHOTS = {"cover_drive", "defensive_shot", "pull_shot", "sweep_shot"}
TIP_FLAGS = {"useful", "incorrect", "unsafe", "unclear"}


@dataclass(frozen=True)
class PersistenceResult:
    """Outcome from an optional persistence operation."""

    stored: bool
    record_id: str | None = None
    duplicate: bool = False
    error_code: str | None = None


def is_persistence_configured() -> bool:
    """Return whether backend-only Supabase writes can be attempted."""
    return bool(SETTINGS.supabase_url and SETTINGS.supabase_service_role_key)


def _postgrest_insert(table: str, row: dict[str, Any]) -> PersistenceResult:
    if not is_persistence_configured():
        return PersistenceResult(stored=False, error_code="persistence_not_configured")

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
            return PersistenceResult(stored=False, duplicate=True, error_code="duplicate_record")
        return PersistenceResult(stored=False, error_code=f"supabase_http_{exc.code}")
    except Exception:
        return PersistenceResult(stored=False, error_code="persistence_failed")

    record_id = None
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        record_id = str(payload[0].get("id") or "")
    return PersistenceResult(stored=True, record_id=record_id or row.get("id"))


def persist_analysis_session(
    *,
    user_id: str | None,
    result: dict[str, Any],
    filename: str,
    request_id: str,
    clip_hash: str,
) -> PersistenceResult:
    """Persist a verified analysis response as server-owned history when configured."""
    if not user_id:
        return PersistenceResult(stored=False, error_code="missing_user")
    segment = result.get("segmentation", {}) if isinstance(result.get("segmentation"), dict) else {}
    timing = result.get("timing", {}) if isinstance(result.get("timing"), dict) else {}
    row = {
        "id": str(uuid4()),
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
        "persistence_source": "server_verified_inference",
    }
    return _postgrest_insert("analysis_sessions", row)


def build_feedback_record(
    *,
    payload: Any,
    user_id: str | None,
    request_id: str,
    authorization_present: bool,
) -> dict[str, Any]:
    """Create a trusted feedback row from a validated client payload."""
    corrected_shot = payload.corrected_shot
    predicted_shot = payload.predicted_shot
    if predicted_shot not in SUPPORTED_SHOTS:
        raise ValueError("predicted_shot is not a supported Smart Cricket label.")
    if corrected_shot is not None and corrected_shot not in SUPPORTED_SHOTS:
        raise ValueError("corrected_shot is not a supported Smart Cricket label.")
    if payload.prediction_was_correct == "incorrect" and corrected_shot is None:
        raise ValueError("corrected_shot is required when marking a prediction incorrect.")
    invalid_flags = sorted(set(payload.tip_flags) - TIP_FLAGS)
    if invalid_flags:
        raise ValueError(f"Unsupported tip flag(s): {', '.join(invalid_flags)}.")

    consent = bool(payload.consent_to_model_improvement)
    return {
        "id": str(uuid4()),
        "user_id": user_id,
        "analysis_session_id": payload.analysis_session_id,
        "client_analysis_id": payload.client_analysis_id,
        "clip_hash": payload.clip_hash.lower(),
        "predicted_shot": predicted_shot,
        "prediction_was_correct": payload.prediction_was_correct,
        "corrected_shot": corrected_shot,
        "technique_feedback_rating": payload.technique_feedback_rating,
        "tip_flags": payload.tip_flags,
        "notes": payload.notes,
        "consent_to_model_improvement": consent,
        "accepted_for_review": consent,
        "review_status": "candidate" if consent else "not_consented",
        "model_version": payload.model_version,
        "pipeline_version": payload.pipeline_version,
        "request_id": request_id,
        "auth_present": authorization_present,
        "provenance": {
            "source": "user_reported_feedback",
            "ground_truth": False,
            "requires_expert_review": True,
            "ai_assisted_review_allowed": True,
            "ai_is_ground_truth": False,
        },
    }


def persist_feedback_record(row: dict[str, Any]) -> PersistenceResult:
    """Persist a beta feedback record if Supabase server credentials are configured."""
    return _postgrest_insert("analysis_feedback", row)
