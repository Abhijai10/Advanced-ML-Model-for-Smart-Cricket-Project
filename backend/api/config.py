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


def _str_env(name: str, default: str) -> str:
    return (os.getenv(name) or default).strip().lower()


@dataclass(frozen=True)
class APISettings:
    """Environment-backed API settings."""

    environment: str = _str_env("SMART_CRICKET_ENV", "development")
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
    analysis_execution_timeout_seconds: int = _int_env("SMART_CRICKET_ANALYSIS_EXECUTION_TIMEOUT_SECONDS", 45)
    max_upload_bytes: int = _int_env("SMART_CRICKET_MAX_UPLOAD_BYTES", 250 * 1024 * 1024)
    max_video_duration_seconds: int = _int_env("SMART_CRICKET_MAX_VIDEO_DURATION_SECONDS", 20)
    max_video_pixels: int = _int_env("SMART_CRICKET_MAX_VIDEO_PIXELS", 1920 * 1080)
    uncertainty_confidence_threshold: int = _int_env("SMART_CRICKET_UNCERTAINTY_CONFIDENCE_PERCENT", 55)
    min_clean_pose_frames: int = _int_env("SMART_CRICKET_MIN_CLEAN_POSE_FRAMES", 20)
    evidence_retention_days: int = _int_env("SMART_CRICKET_EVIDENCE_RETENTION_DAYS", 30)
    evidence_storage_backend: str = os.getenv("SMART_CRICKET_EVIDENCE_STORAGE_BACKEND", "none")
    evidence_local_storage_dir: str = os.getenv("SMART_CRICKET_EVIDENCE_LOCAL_STORAGE_DIR", "/tmp/smart-cricket-evidence")
    evidence_supabase_bucket: str | None = os.getenv("SMART_CRICKET_EVIDENCE_SUPABASE_BUCKET") or None
    allow_model_improvement_participation: bool = _bool_env("SMART_CRICKET_ALLOW_MODEL_IMPROVEMENT_PARTICIPATION", False)
    consent_version: str = os.getenv("SMART_CRICKET_MODEL_IMPROVEMENT_CONSENT_VERSION", "2026-08-04-v1")
    audio_signing_secret: str | None = os.getenv("SMART_CRICKET_AUDIO_SIGNING_SECRET") or None
    audio_url_ttl_seconds: int = _int_env("SMART_CRICKET_AUDIO_URL_TTL_SECONDS", 900)
    audio_max_url_ttl_seconds: int = _int_env("SMART_CRICKET_AUDIO_MAX_URL_TTL_SECONDS", 3600)
    audio_retention_seconds: int = _int_env("SMART_CRICKET_AUDIO_RETENTION_SECONDS", 3600)
    jwks_timeout_seconds: int = _int_env("SMART_CRICKET_JWKS_TIMEOUT_SECONDS", 5)
    jwks_cache_ttl_seconds: int = _int_env("SMART_CRICKET_JWKS_CACHE_TTL_SECONDS", 600)
    rate_limit_backend: str = os.getenv("SMART_CRICKET_RATE_LIMIT_BACKEND", "memory")


SETTINGS = APISettings()
