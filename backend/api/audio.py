"""Signed local audio access for demo/runtime voice artifacts."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from pathlib import Path
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ml.src.voice.voice_config import AUDIO_OUTPUT_DIR

from .config import SETTINGS


router = APIRouter()


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
    if safe_name != filename or not _valid_signature(safe_name, expires, signature):
        raise HTTPException(status_code=403, detail="Audio link is invalid or expired.")
    path = Path(AUDIO_OUTPUT_DIR) / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio file was not found.")
    return FileResponse(path)


@dataclass(frozen=True)
class AudioCleanupResult:
    deleted: int
    retained: int


def cleanup_expired_audio(*, now: float | None = None) -> AudioCleanupResult:
    """Delete generated audio files older than the configured retention window."""
    current = now or time.time()
    deleted = 0
    retained = 0
    for path in Path(AUDIO_OUTPUT_DIR).glob("*.wav"):
        try:
            age = current - path.stat().st_mtime
            if age > SETTINGS.audio_retention_seconds:
                path.unlink()
                deleted += 1
            else:
                retained += 1
        except FileNotFoundError:
            continue
    return AudioCleanupResult(deleted=deleted, retained=retained)
