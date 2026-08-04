"""Signed local audio access for demo/runtime voice artifacts."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ml.src.voice.voice_config import AUDIO_OUTPUT_DIR

from .config import SETTINGS


router = APIRouter()


def _audio_secret() -> bytes:
    secret = SETTINGS.supabase_jwt_secret or SETTINGS.supabase_service_role_key
    if not secret:
        secret = "smart-cricket-local-audio-signing"
    return secret.encode("utf-8")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def sign_audio_url(filename: str, *, ttl_seconds: int = 900) -> str:
    expires = int(time.time()) + ttl_seconds
    payload = f"{Path(filename).name}:{expires}".encode("utf-8")
    signature = _b64(hmac.new(_audio_secret(), payload, hashlib.sha256).digest())
    return f"/audio/{Path(filename).name}?expires={expires}&signature={signature}"


def _valid_signature(filename: str, expires: int, signature: str) -> bool:
    if expires < int(time.time()):
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
