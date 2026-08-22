"""In-process HTTP analysis job queue (no WebSockets)."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from .config import SETTINGS
from .services import (
    APIValidationError,
    AnalysisOverloadError,
    AnalysisTimeoutError,
    AnalysisWorkerError,
    AuthContext,
    _cleanup_temp_path,
    _save_upload_to_temp,
    _validate_video_upload,
    analyze_saved_video_with_retention,
    persist_verified_analysis_for_auth_user,
)


LOGGER = logging.getLogger(__name__)
_JOBS_LOCK = threading.Lock()
_JOBS: dict[str, "AnalysisJob"] = {}
_PENDING_COUNT = 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class AnalysisJob:
    """Mutable in-memory analysis job record."""

    job_id: str
    status: str
    created_at: str
    updated_at: str
    request_id: str
    auth: AuthContext
    filename: str
    temp_path: Path
    upload_bytes: int
    clip_hash: str
    video_probe: dict[str, Any]
    retain_evidence: bool = False
    content_type: str | None = None
    result: dict[str, Any] | None = None
    progress: int = 0
    error_code: str | None = None
    detail: str | None = None
    owner_user_id: str | None = None
    _thread: threading.Thread | None = field(default=None, repr=False)


def _set_job_fields(job: AnalysisJob, **kwargs: Any) -> None:
    for key, value in kwargs.items():
        setattr(job, key, value)
    job.updated_at = _utc_now()


def _count_active_or_pending() -> int:
    return sum(1 for job in _JOBS.values() if job.status in {"queued", "processing"})


def enqueue_analysis_job(
    file: UploadFile,
    *,
    request_id: str,
    auth: AuthContext,
    retain_evidence: bool = False,
) -> dict[str, str]:
    """Validate/save upload, enqueue background analysis, return job acknowledgement."""
    global _PENDING_COUNT
    with _JOBS_LOCK:
        if _count_active_or_pending() >= SETTINGS.max_pending_analysis_jobs:
            raise AnalysisOverloadError("Too many analysis jobs are already queued. Try again shortly.")

    filename = _validate_video_upload(file)
    temp_path, upload_bytes, clip_hash, video_probe = _save_upload_to_temp(file, filename)
    job_id = uuid4().hex
    now = _utc_now()
    job = AnalysisJob(
        job_id=job_id,
        status="queued",
        created_at=now,
        updated_at=now,
        request_id=request_id,
        auth=auth,
        filename=filename,
        temp_path=temp_path,
        upload_bytes=upload_bytes,
        clip_hash=clip_hash,
        video_probe=video_probe,
        retain_evidence=retain_evidence,
        content_type=getattr(file, "content_type", None),
        owner_user_id=auth.user_id,
    )
    with _JOBS_LOCK:
        _JOBS[job_id] = job
        _PENDING_COUNT = _count_active_or_pending()

    worker = threading.Thread(target=_run_job, args=(job_id,), name=f"analysis-job-{job_id[:8]}", daemon=True)
    job._thread = worker
    worker.start()
    return {"job_id": job_id, "status": "queued"}


def get_analysis_job(job_id: str, *, auth: AuthContext) -> dict[str, Any] | None:
    """Return a job payload if it exists and is visible to the caller."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        if job.owner_user_id and auth.user_id and job.owner_user_id != auth.user_id:
            return None
        if job.owner_user_id and not auth.user_id:
            return None
        payload = {
            "job_id": job.job_id,
            "status": job.status,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "progress": job.progress,
            "error_code": job.error_code,
            "detail": job.detail,
            "result": job.result,
        }
    return payload


def _run_job(job_id: str) -> None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if job is None:
        return
    try:
        _set_job_fields(job, status="processing", progress=15)
        result, evidence_outcome = analyze_saved_video_with_retention(
            temp_path=job.temp_path,
            filename=job.filename,
            upload_bytes=job.upload_bytes,
            clip_hash=job.clip_hash,
            video_probe=job.video_probe,
            request_id=job.request_id,
            auth=job.auth,
            retain_evidence=job.retain_evidence,
            content_type=job.content_type,
            wait_for_capacity=True,
        )
        persist_verified_analysis_for_auth_user(
            auth=job.auth,
            result=result,
            filename=result["api_metadata"]["upload_filename"],
            request_id=job.request_id,
            analysis_session_id=result["api_metadata"].get("planned_analysis_session_id"),
            evidence_outcome=evidence_outcome,
        )
        _set_job_fields(job, status="completed", progress=100, result=result, error_code=None, detail=None)
    except AnalysisOverloadError as exc:
        _set_job_fields(job, status="failed", progress=100, error_code=exc.error_code, detail=str(exc))
    except AnalysisTimeoutError as exc:
        _set_job_fields(job, status="failed", progress=100, error_code=exc.error_code, detail=str(exc))
    except AnalysisWorkerError as exc:
        _set_job_fields(
            job,
            status="failed",
            progress=100,
            error_code=exc.error_code,
            detail="Smart Cricket inference worker failed safely. Try again with a clearer, shorter clip.",
        )
    except APIValidationError as exc:
        _set_job_fields(job, status="failed", error_code=exc.error_code, detail=str(exc))
    except Exception:
        LOGGER.exception("Unexpected analysis job failure (job_id=%s).", job_id)
        _set_job_fields(
            job,
            status="failed",
            progress=100,
            error_code="analysis_failed",
            detail="Smart Cricket analysis failed unexpectedly.",
        )
    finally:
        try:
            _cleanup_temp_path(job.temp_path)
        except Exception:
            LOGGER.exception("Failed cleaning analysis job temp path (job_id=%s).", job_id)
        _prune_jobs()


def _prune_jobs(*, max_age_seconds: int = 3600) -> None:
    """Drop completed/failed jobs older than the retention window."""
    cutoff = time.time() - max_age_seconds
    with _JOBS_LOCK:
        stale = []
        for job_id, job in _JOBS.items():
            if job.status not in {"completed", "failed"}:
                continue
            try:
                created = datetime.fromisoformat(job.created_at.replace("Z", "+00:00")).timestamp()
            except ValueError:
                created = 0.0
            if created < cutoff:
                stale.append(job_id)
        for job_id in stale:
            _JOBS.pop(job_id, None)


def reset_jobs_for_tests() -> None:
    """Clear in-memory jobs between unit tests."""
    with _JOBS_LOCK:
        _JOBS.clear()
