"""Runtime configuration for the Smart Cricket API."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if not raw:
        return default
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    return values or default


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


@dataclass(frozen=True)
class APISettings:
    """Environment-backed API settings."""

    allowed_origins: tuple[str, ...] = _csv_env(
        "SMART_CRICKET_CORS_ORIGINS",
        (
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ),
    )
    dev_dataset_endpoints: bool = _bool_env("SMART_CRICKET_ENABLE_DEV_DATASET_ENDPOINTS", False)
    require_auth: bool = _bool_env("SMART_CRICKET_REQUIRE_AUTH", False)
    supabase_jwt_secret: str | None = os.getenv("SUPABASE_JWT_SECRET") or None
    supabase_url: str | None = os.getenv("SUPABASE_URL") or None
    supabase_service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None
    jwt_audience: str | None = os.getenv("SUPABASE_JWT_AUDIENCE") or None
    jwt_issuer: str | None = os.getenv("SUPABASE_JWT_ISSUER") or None
    supabase_publishable_key: str | None = os.getenv("SUPABASE_PUBLISHABLE_KEY") or None
    require_feedback_persistence: bool = _bool_env("SMART_CRICKET_REQUIRE_FEEDBACK_PERSISTENCE", True)
    rate_limit_per_minute: int = _int_env("SMART_CRICKET_RATE_LIMIT_PER_MINUTE", 20)
    feedback_rate_limit_per_minute: int = _int_env("SMART_CRICKET_FEEDBACK_RATE_LIMIT_PER_MINUTE", 30)
    trusted_proxy_hops: int = _int_env("SMART_CRICKET_TRUSTED_PROXY_HOPS", 0)
    persistence_timeout_seconds: int = _int_env("SMART_CRICKET_PERSISTENCE_TIMEOUT_SECONDS", 8)
    max_concurrent_analyses: int = _int_env("SMART_CRICKET_MAX_CONCURRENT_ANALYSES", 1)
    analysis_queue_timeout_seconds: int = _int_env("SMART_CRICKET_ANALYSIS_QUEUE_TIMEOUT_SECONDS", 3)
    max_upload_bytes: int = _int_env("SMART_CRICKET_MAX_UPLOAD_BYTES", 250 * 1024 * 1024)
    max_video_duration_seconds: int = _int_env("SMART_CRICKET_MAX_VIDEO_DURATION_SECONDS", 20)
    max_video_pixels: int = _int_env("SMART_CRICKET_MAX_VIDEO_PIXELS", 1920 * 1080)
    uncertainty_confidence_threshold: int = _int_env("SMART_CRICKET_UNCERTAINTY_CONFIDENCE_PERCENT", 55)
    min_clean_pose_frames: int = _int_env("SMART_CRICKET_MIN_CLEAN_POSE_FRAMES", 20)
    evidence_retention_days: int = _int_env("SMART_CRICKET_EVIDENCE_RETENTION_DAYS", 30)
    evidence_storage_backend: str = os.getenv("SMART_CRICKET_EVIDENCE_STORAGE_BACKEND", "none")
    consent_version: str = os.getenv("SMART_CRICKET_MODEL_IMPROVEMENT_CONSENT_VERSION", "2026-08-04-v1")


SETTINGS = APISettings()
