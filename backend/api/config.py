"""Runtime configuration for the Smart Cricket API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


VALID_ENVIRONMENTS = {"development", "test", "staging", "production"}
VALID_MEDIAPIPE_DELEGATES = {"auto", "cpu", "gpu"}


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
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:4028",
            "http://127.0.0.1:4028",
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
    analysis_job_wait_timeout_seconds: int = _int_env("SMART_CRICKET_ANALYSIS_JOB_WAIT_TIMEOUT_SECONDS", 180)
    max_pending_analysis_jobs: int = _int_env("SMART_CRICKET_MAX_PENDING_ANALYSIS_JOBS", 8)
    enable_pose_output: bool = _bool_env("SMART_CRICKET_ENABLE_POSE_OUTPUT", False)
    mediapipe_delegate: str = _str_env("SMART_CRICKET_MEDIAPIPE_DELEGATE", "auto")
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
    audio_storage_backend: str = os.getenv("SMART_CRICKET_AUDIO_STORAGE_BACKEND", "local")
    audio_supabase_bucket: str | None = os.getenv("SMART_CRICKET_AUDIO_SUPABASE_BUCKET") or None
    tts_enabled: bool = _bool_env("SMART_CRICKET_TTS_ENABLED", True)
    tts_provider: str = os.getenv("SMART_CRICKET_TTS_PROVIDER", "local")
    tts_language_code: str = os.getenv("SMART_CRICKET_TTS_LANGUAGE_CODE", "en-IN")
    tts_voice: str | None = os.getenv("SMART_CRICKET_TTS_VOICE") or None
    tts_audio_format: str = os.getenv("SMART_CRICKET_TTS_AUDIO_FORMAT", "mp3")
    tts_request_timeout_seconds: int = _int_env("SMART_CRICKET_TTS_REQUEST_TIMEOUT_SECONDS", 5)
    tts_max_text_characters: int = _int_env("SMART_CRICKET_TTS_MAX_TEXT_CHARACTERS", 500)
    tts_retry_count: int = _int_env("SMART_CRICKET_TTS_RETRY_COUNT", 1)
    jwks_timeout_seconds: int = _int_env("SMART_CRICKET_JWKS_TIMEOUT_SECONDS", 5)
    jwks_cache_ttl_seconds: int = _int_env("SMART_CRICKET_JWKS_CACHE_TTL_SECONDS", 600)
    rate_limit_backend: str = os.getenv("SMART_CRICKET_RATE_LIMIT_BACKEND", "memory")
    redis_url: str | None = os.getenv("SMART_CRICKET_REDIS_URL") or None
    sentry_dsn: str | None = os.getenv("SMART_CRICKET_SENTRY_DSN") or None
    deployment_base_url: str | None = os.getenv("SMART_CRICKET_DEPLOYMENT_BASE_URL") or None

    def __post_init__(self) -> None:
        if self.environment not in VALID_ENVIRONMENTS:
            raise ValueError(f"SMART_CRICKET_ENV must be one of {sorted(VALID_ENVIRONMENTS)}.")


@dataclass(frozen=True)
class ConfigValidationIssue:
    """One safe configuration validation issue."""

    code: str
    detail: str
    severity: str = "error"


class ProductionConfigurationError(RuntimeError):
    """Raised when staging/production configuration is unsafe."""

    error_code = "production_configuration_invalid"

    def __init__(self, issues: list[ConfigValidationIssue]) -> None:
        super().__init__("Smart Cricket production configuration is invalid.")
        self.issues = issues


def normalize_origins(origins: tuple[str, ...]) -> tuple[str, ...]:
    """Normalize configured CORS origins without weakening exact matching."""

    normalized: list[str] = []
    for origin in origins:
        item = origin.strip()
        if not item:
            continue
        if item == "*":
            normalized.append(item)
            continue
        parsed = urlparse(item)
        if parsed.scheme and parsed.netloc:
            normalized.append(f"{parsed.scheme}://{parsed.netloc}")
        else:
            normalized.append(item.rstrip("/"))
    return tuple(dict.fromkeys(normalized))


def validate_runtime_settings(settings: APISettings) -> list[ConfigValidationIssue]:
    """Return safe, non-secret runtime configuration issues."""

    issues: list[ConfigValidationIssue] = []
    strict = settings.environment in {"staging", "production"}

    def add(code: str, detail: str) -> None:
        issues.append(ConfigValidationIssue(code=code, detail=detail))

    if settings.environment not in VALID_ENVIRONMENTS:
        add("invalid_environment", "SMART_CRICKET_ENV must be development, test, staging, or production.")
    if settings.max_concurrent_analyses < 1 or settings.max_concurrent_analyses > 16:
        add("invalid_worker_limit", "SMART_CRICKET_MAX_CONCURRENT_ANALYSES must be between 1 and 16.")
    if settings.analysis_queue_timeout_seconds < 1 or settings.analysis_queue_timeout_seconds > 60:
        add("invalid_queue_timeout", "SMART_CRICKET_ANALYSIS_QUEUE_TIMEOUT_SECONDS must be between 1 and 60.")
    if settings.analysis_execution_timeout_seconds < 1 or settings.analysis_execution_timeout_seconds > 600:
        add("invalid_execution_timeout", "SMART_CRICKET_ANALYSIS_EXECUTION_TIMEOUT_SECONDS must be between 1 and 600.")
    if settings.mediapipe_delegate not in VALID_MEDIAPIPE_DELEGATES:
        add("invalid_mediapipe_delegate", "SMART_CRICKET_MEDIAPIPE_DELEGATE must be auto, cpu, or gpu.")
    if settings.max_upload_bytes < 1024 or settings.max_upload_bytes > 1024 * 1024 * 1024:
        add("invalid_upload_limit", "SMART_CRICKET_MAX_UPLOAD_BYTES must be between 1 KiB and 1 GiB.")
    if settings.max_video_duration_seconds < 1 or settings.max_video_duration_seconds > 120:
        add("invalid_video_duration", "SMART_CRICKET_MAX_VIDEO_DURATION_SECONDS must be between 1 and 120.")
    if settings.audio_url_ttl_seconds < 1 or settings.audio_max_url_ttl_seconds < settings.audio_url_ttl_seconds:
        add("invalid_audio_ttl", "Audio URL TTL values must be positive and max TTL must be at least the default TTL.")
    if settings.audio_storage_backend.strip().lower() not in {"local", "supabase"}:
        add("invalid_audio_storage_backend", "SMART_CRICKET_AUDIO_STORAGE_BACKEND must be local or supabase.")
    if settings.audio_storage_backend.strip().lower() == "supabase":
        if not settings.audio_supabase_bucket:
            add("audio_bucket_missing", "SMART_CRICKET_AUDIO_SUPABASE_BUCKET is required for Supabase audio storage.")
        if not settings.supabase_url or not settings.supabase_service_role_key:
            add("audio_storage_credentials_missing", "Supabase URL and service-role key are required for Supabase audio storage.")
    tts_provider = settings.tts_provider.strip().lower()
    if tts_provider not in {"local", "development", "macos", "google", "text", "text_only", "none", "disabled"}:
        add("invalid_tts_provider", "SMART_CRICKET_TTS_PROVIDER must be local, google, or text_only.")
    if settings.tts_audio_format.strip().lower() not in {"mp3", "wav", "linear16"}:
        add("invalid_tts_audio_format", "SMART_CRICKET_TTS_AUDIO_FORMAT must be mp3, wav, or linear16.")
    if settings.tts_request_timeout_seconds < 1 or settings.tts_request_timeout_seconds > 30:
        add("invalid_tts_timeout", "SMART_CRICKET_TTS_REQUEST_TIMEOUT_SECONDS must be between 1 and 30.")
    if settings.tts_max_text_characters < 1 or settings.tts_max_text_characters > 5000:
        add("invalid_tts_text_length", "SMART_CRICKET_TTS_MAX_TEXT_CHARACTERS must be between 1 and 5000.")
    if settings.tts_retry_count < 0 or settings.tts_retry_count > 2:
        add("invalid_tts_retry_count", "SMART_CRICKET_TTS_RETRY_COUNT must be between 0 and 2.")
    if settings.evidence_retention_days < 1 or settings.evidence_retention_days > 365:
        add("invalid_evidence_retention", "SMART_CRICKET_EVIDENCE_RETENTION_DAYS must be between 1 and 365.")

    origins = normalize_origins(settings.allowed_origins)
    if strict and "*" in origins:
        add("wildcard_cors_origin", "Staging/production must not allow wildcard CORS origins.")
    if strict and settings.require_auth:
        if not settings.supabase_url:
            add("auth_supabase_url_missing", "SUPABASE_URL is required when auth is enabled.")
        if not settings.jwt_audience:
            add("auth_audience_missing", "SUPABASE_JWT_AUDIENCE is required when auth is enabled.")
        if not settings.jwt_issuer:
            add("auth_issuer_missing", "SUPABASE_JWT_ISSUER is required when auth is enabled.")
        if not (settings.supabase_jwt_secret or settings.supabase_url):
            add("auth_verifier_missing", "A Supabase JWT secret or JWKS-capable Supabase URL is required.")
    if strict and settings.require_feedback_persistence:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            add("persistence_credentials_missing", "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for trusted persistence.")
    if strict and settings.allow_model_improvement_participation:
        backend = settings.evidence_storage_backend.strip().lower()
        if backend != "supabase":
            add("evidence_backend_not_supabase", "Staging/production model improvement requires Supabase evidence storage.")
        if not settings.evidence_supabase_bucket:
            add("evidence_bucket_missing", "SMART_CRICKET_EVIDENCE_SUPABASE_BUCKET is required when model improvement is enabled.")
        if not settings.supabase_url or not settings.supabase_service_role_key:
            add("evidence_credentials_missing", "Supabase URL and service-role key are required for Supabase evidence storage.")
    if strict:
        if not settings.audio_signing_secret or len(settings.audio_signing_secret) < 32:
            add("audio_secret_weak", "SMART_CRICKET_AUDIO_SIGNING_SECRET must be at least 32 characters.")
        if settings.audio_signing_secret and settings.audio_signing_secret == settings.supabase_service_role_key:
            add("audio_secret_reuses_service_key", "Audio signing secret must not reuse the Supabase service-role key.")
        if settings.audio_storage_backend.strip().lower() == "local":
            add("local_audio_storage_in_production", "Staging/production should use Supabase private audio storage.")
        if settings.tts_enabled:
            if tts_provider in {"local", "development", "macos"}:
                add("development_tts_in_production", "Staging/production TTS must use google or text_only, not local development TTS.")
            if tts_provider == "google":
                try:
                    import google.auth  # type: ignore[import-not-found]
                    from google.cloud import texttospeech  # type: ignore[import-not-found]

                    google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                except Exception:
                    add("google_tts_unverified", "Google TTS selected but dependency or Application Default Credentials are unavailable.")
        backend = settings.rate_limit_backend.strip().lower()
        if backend == "memory":
            add("memory_rate_limit_in_production", "Staging/production must use redis or gateway rate limiting.")
        elif backend == "redis" and not settings.redis_url:
            add("redis_url_missing", "SMART_CRICKET_REDIS_URL is required for redis rate limiting.")
        elif backend not in {"redis", "gateway"}:
            add("invalid_rate_limit_backend", "Rate-limit backend must be redis or gateway in staging/production.")

    return issues


def production_config_report(settings: APISettings) -> dict[str, object]:
    """Return a readiness-safe configuration validation report."""

    issues = validate_runtime_settings(settings)
    return {
        "ok": not issues,
        "issues": [issue.__dict__ for issue in issues],
    }


def validate_production_settings(settings: APISettings) -> None:
    issues = validate_runtime_settings(settings)
    if issues:
        raise ProductionConfigurationError(issues)


SETTINGS = APISettings()
