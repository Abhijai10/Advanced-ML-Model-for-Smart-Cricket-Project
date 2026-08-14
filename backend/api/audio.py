"""Protected audio artifact storage and delivery."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib import request
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ml.src.voice.voice_config import AUDIO_OUTPUT_DIR

from .config import SETTINGS
from .observability import METRICS


router = APIRouter()
ALLOWED_AUDIO_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".aiff": "audio/aiff",
}


@dataclass(frozen=True)
class AudioArtifact:
    """Safe API-facing audio artifact metadata."""

    artifact_id: str
    provider: str
    mime_type: str
    extension: str
    created_at: str
    expires_at: str
    byte_count: int
    checksum: str
    storage_backend: str
    audio_url: str | None = None
    signed_url_expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AudioStoreResult:
    ok: bool
    artifact: AudioArtifact | None = None
    error_code: str | None = None
    detail: str | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _iso_from_epoch(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def _audio_secret() -> bytes:
    secret = SETTINGS.audio_signing_secret
    if not secret:
        if SETTINGS.environment not in {"development", "test"}:
            raise HTTPException(status_code=503, detail="Audio signing is not configured.")
        secret = "smart-cricket-local-audio-signing-test-only"
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="Audio signing secret is too short.")
    if SETTINGS.supabase_service_role_key and secret == SETTINGS.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Audio signing secret must not reuse the Supabase service-role key.")
    return secret.encode("utf-8")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def sign_audio_url(filename: str, *, ttl_seconds: int = 900) -> str:
    ttl = max(1, min(ttl_seconds, SETTINGS.audio_max_url_ttl_seconds, SETTINGS.audio_url_ttl_seconds))
    expires = int(time.time()) + ttl
    payload = f"{Path(filename).name}:{expires}".encode("utf-8")
    signature = _b64(hmac.new(_audio_secret(), payload, hashlib.sha256).digest())
    return f"/audio/{Path(filename).name}?expires={expires}&signature={signature}"


def _valid_signature(filename: str, expires: int, signature: str) -> bool:
    now = int(time.time())
    if expires < now:
        return False
    if expires - now > SETTINGS.audio_max_url_ttl_seconds:
        return False
    payload = f"{Path(filename).name}:{expires}".encode("utf-8")
    expected = _b64(hmac.new(_audio_secret(), payload, hashlib.sha256).digest())
    return hmac.compare_digest(expected, signature)


@router.get("/audio/{filename}")
def get_audio(filename: str, expires: int, signature: str) -> FileResponse:
    safe_name = Path(filename).name
    suffix = Path(safe_name).suffix.lower()
    if safe_name != filename or suffix not in ALLOWED_AUDIO_TYPES or not _valid_signature(safe_name, expires, signature):
        raise HTTPException(status_code=403, detail="Audio link is invalid or expired.")
    path = Path(AUDIO_OUTPUT_DIR) / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio file was not found.")
    return FileResponse(path, media_type=ALLOWED_AUDIO_TYPES[suffix], filename=safe_name)


@router.post("/audio-artifacts/{artifact_id}/signed-url")
def refresh_local_audio_url(artifact_id: str) -> dict[str, Any]:
    """Refresh a local development signed URL for an opaque artifact ID."""

    safe_name = Path(artifact_id).name
    suffix = Path(safe_name).suffix.lower()
    if safe_name != artifact_id or suffix not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=403, detail="Audio artifact is invalid.")
    path = Path(AUDIO_OUTPUT_DIR) / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio artifact was not found.")
    if time.time() - path.stat().st_mtime > SETTINGS.audio_retention_seconds:
        raise HTTPException(status_code=410, detail="Audio artifact has expired.")
    expires_at = _iso_from_epoch(time.time() + min(SETTINGS.audio_url_ttl_seconds, SETTINGS.audio_max_url_ttl_seconds))
    return {"audio_url": sign_audio_url(safe_name), "expires_at": expires_at}


def _validate_audio_bytes(audio_bytes: bytes, *, extension: str, mime_type: str) -> tuple[str, str]:
    ext = extension if extension.startswith(".") else f".{extension}"
    ext = ext.lower()
    if ext not in ALLOWED_AUDIO_TYPES:
        raise ValueError("unsupported_audio_extension")
    expected = ALLOWED_AUDIO_TYPES[ext]
    if mime_type != expected:
        raise ValueError("mismatched_audio_mime_type")
    if not audio_bytes:
        raise ValueError("empty_audio_artifact")
    if ext == ".mp3" and not (audio_bytes.startswith(b"ID3") or audio_bytes[:1] == b"\xff"):
        raise ValueError("invalid_mp3_output")
    if ext == ".wav" and not audio_bytes.startswith(b"RIFF"):
        raise ValueError("invalid_wav_output")
    return ext, expected


def store_audio_artifact(
    audio_bytes: bytes,
    *,
    provider: str,
    mime_type: str,
    extension: str,
    request_id: str,
    user_id: str | None = None,
    analysis_session_id: str | None = None,
) -> AudioStoreResult:
    """Store generated audio and return safe signed-access metadata."""

    try:
        ext, safe_mime = _validate_audio_bytes(audio_bytes, extension=extension, mime_type=mime_type)
    except ValueError as exc:
        METRICS.increment("smart_cricket_audio_storage_failure", backend="validation", code=str(exc))
        return AudioStoreResult(False, error_code=str(exc))
    backend = SETTINGS.audio_storage_backend.strip().lower()
    if backend == "supabase":
        return _store_supabase_audio(
            audio_bytes,
            provider=provider,
            mime_type=safe_mime,
            extension=ext,
            request_id=request_id,
            user_id=user_id,
            analysis_session_id=analysis_session_id,
        )
    return _store_local_audio(audio_bytes, provider=provider, mime_type=safe_mime, extension=ext, request_id=request_id)


def _store_local_audio(audio_bytes: bytes, *, provider: str, mime_type: str, extension: str, request_id: str) -> AudioStoreResult:
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    artifact_id = f"{request_id}-{uuid4().hex}{extension}"
    path = AUDIO_OUTPUT_DIR / artifact_id
    path.write_bytes(audio_bytes)
    checksum = hashlib.sha256(audio_bytes).hexdigest()
    url = sign_audio_url(artifact_id)
    now = time.time()
    artifact = AudioArtifact(
        artifact_id=artifact_id,
        provider=provider,
        mime_type=mime_type,
        extension=extension.lstrip("."),
        created_at=_utc_now(),
        expires_at=_iso_from_epoch(now + SETTINGS.audio_retention_seconds),
        byte_count=len(audio_bytes),
        checksum=checksum,
        storage_backend="local",
        audio_url=url,
        signed_url_expires_at=_iso_from_epoch(now + min(SETTINGS.audio_url_ttl_seconds, SETTINGS.audio_max_url_ttl_seconds)),
    )
    METRICS.increment("smart_cricket_audio_storage_success", backend="local", provider=provider)
    return AudioStoreResult(True, artifact=artifact)


def _store_supabase_audio(
    audio_bytes: bytes,
    *,
    provider: str,
    mime_type: str,
    extension: str,
    request_id: str,
    user_id: str | None,
    analysis_session_id: str | None,
) -> AudioStoreResult:
    if not SETTINGS.supabase_url or not SETTINGS.supabase_service_role_key or not SETTINGS.audio_supabase_bucket:
        METRICS.increment("smart_cricket_audio_storage_failure", backend="supabase", code="audio_storage_unconfigured")
        return AudioStoreResult(False, error_code="audio_storage_unconfigured")
    owner = user_id or "anonymous"
    session = analysis_session_id or request_id
    object_path = f"{owner}/{session}/{uuid4().hex}{extension}"
    base = SETTINGS.supabase_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {SETTINGS.supabase_service_role_key}",
        "apikey": SETTINGS.supabase_service_role_key,
        "Content-Type": mime_type,
        "x-upsert": "false",
    }
    try:
        upload = request.Request(
            f"{base}/storage/v1/object/{SETTINGS.audio_supabase_bucket}/{object_path}",
            data=audio_bytes,
            headers=headers,
            method="POST",
        )
        with request.urlopen(upload, timeout=SETTINGS.persistence_timeout_seconds) as response:
            if response.status >= 300:
                raise RuntimeError(f"HTTP{response.status}")
        signed = _sign_supabase_audio_url(base, object_path)
    except Exception:
        METRICS.increment("smart_cricket_audio_storage_failure", backend="supabase", code="audio_storage_request_failed")
        return AudioStoreResult(False, error_code="audio_storage_request_failed")
    checksum = hashlib.sha256(audio_bytes).hexdigest()
    now = time.time()
    artifact = AudioArtifact(
        artifact_id=hashlib.sha256(object_path.encode("utf-8")).hexdigest()[:32],
        provider=provider,
        mime_type=mime_type,
        extension=extension.lstrip("."),
        created_at=_utc_now(),
        expires_at=_iso_from_epoch(now + SETTINGS.audio_retention_seconds),
        byte_count=len(audio_bytes),
        checksum=checksum,
        storage_backend="supabase",
        audio_url=signed,
        signed_url_expires_at=_iso_from_epoch(now + min(SETTINGS.audio_url_ttl_seconds, SETTINGS.audio_max_url_ttl_seconds)),
        metadata={"access_type": "supabase_storage_signed_url"},
    )
    METRICS.increment("smart_cricket_audio_storage_success", backend="supabase", provider=provider)
    return AudioStoreResult(True, artifact=artifact)


def _sign_supabase_audio_url(base_url: str, object_path: str) -> str:
    payload = json.dumps({"expiresIn": min(SETTINGS.audio_url_ttl_seconds, SETTINGS.audio_max_url_ttl_seconds)}).encode("utf-8")
    req = request.Request(
        f"{base_url}/storage/v1/object/sign/{SETTINGS.audio_supabase_bucket}/{object_path}",
        data=payload,
        headers={
            "Authorization": f"Bearer {SETTINGS.supabase_service_role_key}",
            "apikey": SETTINGS.supabase_service_role_key or "",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=SETTINGS.persistence_timeout_seconds) as response:
        body = json.loads(response.read().decode("utf-8") or "{}")
    signed = body.get("signedURL") or body.get("signedUrl") or body.get("signed_url")
    if not isinstance(signed, str) or not signed:
        METRICS.increment("smart_cricket_audio_signed_url_failure", backend="supabase", code="missing_signed_url")
        raise RuntimeError("missing signed url")
    if signed.startswith("/"):
        signed = f"{base_url}{signed}"
    return signed


@dataclass(frozen=True)
class AudioCleanupResult:
    scanned: int
    expired: int
    deleted: int
    failed: int
    skipped: int


def cleanup_expired_audio(*, now: float | None = None, dry_run: bool = False) -> AudioCleanupResult:
    """Delete generated audio files older than the configured retention window."""
    current = now or time.time()
    scanned = 0
    expired = 0
    deleted = 0
    failed = 0
    skipped = 0
    for path in Path(AUDIO_OUTPUT_DIR).iterdir() if Path(AUDIO_OUTPUT_DIR).is_dir() else []:
        if path.suffix.lower() not in ALLOWED_AUDIO_TYPES:
            skipped += 1
            continue
        scanned += 1
        try:
            age = current - path.stat().st_mtime
            if age > SETTINGS.audio_retention_seconds:
                expired += 1
                if dry_run:
                    skipped += 1
                else:
                    path.unlink()
                    deleted += 1
            else:
                skipped += 1
        except (FileNotFoundError, OSError):
            failed += 1
            METRICS.increment("smart_cricket_audio_cleanup_failed", backend="local")
            continue
    if deleted:
        METRICS.increment("smart_cricket_audio_cleanup_deleted", value=deleted, backend="local")
    return AudioCleanupResult(scanned=scanned, expired=expired, deleted=deleted, failed=failed, skipped=skipped)
