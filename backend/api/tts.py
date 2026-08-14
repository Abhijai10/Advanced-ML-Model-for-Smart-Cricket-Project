"""Production-capable TTS provider boundary for Smart Cricket."""

from __future__ import annotations

import concurrent.futures
import os
import shutil
import subprocess
import tempfile
import time
import wave
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .config import APISettings, SETTINGS
from .observability import METRICS, logger


SUPPORTED_AUDIO_FORMATS = {
    "mp3": ("audio/mpeg", ".mp3"),
    "wav": ("audio/wav", ".wav"),
    "linear16": ("audio/wav", ".wav"),
}
TRANSIENT_ERROR_CODES = {"tts_provider_unavailable", "tts_request_failed", "tts_timeout"}


@dataclass(frozen=True)
class TTSResult:
    """Provider-neutral TTS result."""

    status: str
    provider: str
    audio_bytes: bytes = b""
    mime_type: str = "application/octet-stream"
    extension: str = ""
    duration_seconds: float | None = None
    error_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def available(self) -> bool:
        return self.status == "success" and bool(self.audio_bytes)


class TTSProvider(Protocol):
    """Interface implemented by every TTS provider."""

    provider_id: str

    def synthesize(self, text: str, *, request_id: str, language: str, voice: str | None = None) -> TTSResult:
        ...


class TTSError(RuntimeError):
    """Safe normalized provider failure."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def sanitize_tts_text(text: str, *, max_chars: int) -> str:
    """Normalize plain text for provider calls without allowing SSML injection."""

    if max_chars < 1 or max_chars > 5000:
        raise TTSError("tts_invalid_input", "TTS max text length is outside the supported range.")
    clean_chars: list[str] = []
    for char in str(text):
        if char in {"\n", "\r", "\t"}:
            clean_chars.append(" ")
        elif ord(char) < 32 or ord(char) == 127:
            continue
        else:
            clean_chars.append(char)
    clean = " ".join("".join(clean_chars).strip().split())
    if not clean:
        raise TTSError("tts_invalid_input", "TTS text is empty after sanitization.")
    if len(clean) > max_chars:
        clean = clean[:max_chars].rstrip()
    return clean


def _format_metadata(settings: APISettings) -> tuple[str, str]:
    fmt = settings.tts_audio_format.strip().lower()
    if fmt not in SUPPORTED_AUDIO_FORMATS:
        raise TTSError("tts_unsupported_format", "Unsupported TTS audio format.")
    return SUPPORTED_AUDIO_FORMATS[fmt]


class TextOnlyTTSProvider:
    """Explicit no-audio provider used when TTS is disabled or unavailable."""

    provider_id = "text_only"

    def synthesize(self, text: str, *, request_id: str, language: str, voice: str | None = None) -> TTSResult:
        return TTSResult(status="text_only", provider=self.provider_id, error_code="tts_unconfigured")


class LocalDevelopmentTTSProvider:
    """Development-only local TTS using macOS say, with a labelled WAV cue fallback."""

    provider_id = "local_development"

    def __init__(self, settings: APISettings = SETTINGS) -> None:
        self.settings = settings

    def synthesize(self, text: str, *, request_id: str, language: str, voice: str | None = None) -> TTSResult:
        mime_type, extension = _format_metadata(self.settings)
        if extension not in {".wav", ".mp3"}:
            raise TTSError("tts_unsupported_format", "Local development TTS supports wav/mp3 metadata only.")
        with tempfile.TemporaryDirectory() as tmp:
            temp_path = Path(tmp) / f"{request_id}{extension}"
            say_path = self._try_macos_say(text, temp_path, voice=voice)
            if say_path and say_path.is_file() and say_path.stat().st_size > 0:
                audio = say_path.read_bytes()
                return TTSResult("success", "macos_say_development", audio, "audio/aiff", say_path.suffix, metadata={"language": language})
            cue = temp_path.with_suffix(".wav")
            self._write_audio_cue_wav(cue, text)
            return TTSResult(
                "success",
                "local_audio_cue_development",
                cue.read_bytes(),
                "audio/wav",
                ".wav",
                metadata={"language": language, "is_audio_cue": True},
            )

    def _try_macos_say(self, text: str, path: Path, *, voice: str | None) -> Path | None:
        if shutil.which("say") is None:
            return None
        output = path.with_suffix(".aiff")
        cmd = ["say", "-o", str(output)]
        if voice:
            cmd.extend(["-v", voice])
        cmd.append(text)
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=self.settings.tts_request_timeout_seconds)
        if output.is_file() and output.stat().st_size > 8192:
            return output
        output.unlink(missing_ok=True)
        return None

    def _write_audio_cue_wav(self, path: Path, text: str) -> None:
        sample_rate = 22050
        duration_seconds = min(4.0, max(1.0, len(text) / 45.0))
        total_frames = int(sample_rate * duration_seconds)
        amplitude = 6500
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            for i in range(total_frames):
                t = i / sample_rate
                envelope = min(1.0, i / (sample_rate * 0.08), (total_frames - i) / (sample_rate * 0.12))
                freq = 440.0 + 32.0 * math.sin(2.0 * math.pi * 0.8 * t)
                sample = int(amplitude * max(0.0, envelope) * math.sin(2.0 * math.pi * freq * t))
                wav.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))


class GoogleCloudTTSProvider:
    """Google Cloud Text-to-Speech adapter using ADC-supported credential discovery."""

    provider_id = "google"

    def __init__(self, settings: APISettings = SETTINGS) -> None:
        self.settings = settings

    def synthesize(self, text: str, *, request_id: str, language: str, voice: str | None = None) -> TTSResult:
        try:
            from google.cloud import texttospeech  # type: ignore[import-not-found]
            import google.auth  # type: ignore[import-not-found]
        except Exception as exc:
            raise TTSError("tts_provider_unavailable", "Google Cloud TTS dependency is not installed.") from exc
        try:
            google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        except Exception as exc:
            raise TTSError("tts_auth_failed", "Google Cloud Application Default Credentials are unavailable.") from exc

        mime_type, extension = _format_metadata(self.settings)
        encoding = texttospeech.AudioEncoding.MP3 if extension == ".mp3" else texttospeech.AudioEncoding.LINEAR16
        client = texttospeech.TextToSpeechClient()
        voice_params: dict[str, Any] = {"language_code": language}
        if voice:
            voice_params["name"] = voice
        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(**voice_params),
            audio_config=texttospeech.AudioConfig(audio_encoding=encoding),
            timeout=self.settings.tts_request_timeout_seconds,
        )
        audio = bytes(response.audio_content or b"")
        if not audio:
            raise TTSError("tts_invalid_output", "Google Cloud TTS returned empty audio.")
        return TTSResult("success", self.provider_id, audio, mime_type, extension, metadata={"language": language, "voice": voice})


def _provider_for_settings(settings: APISettings) -> TTSProvider:
    if not settings.tts_enabled:
        return TextOnlyTTSProvider()
    provider = settings.tts_provider.strip().lower()
    if provider in {"text", "text_only", "none", "disabled"}:
        return TextOnlyTTSProvider()
    if provider in {"local", "development", "macos"}:
        return LocalDevelopmentTTSProvider(settings)
    if provider == "google":
        return GoogleCloudTTSProvider(settings)
    raise TTSError("tts_unconfigured", "Unsupported TTS provider.")


def synthesize_with_config(text: str, *, request_id: str, settings: APISettings = SETTINGS) -> TTSResult:
    """Bounded, retry-limited TTS synthesis with safe fallback semantics."""

    provider = _provider_for_settings(settings)
    provider_id = getattr(provider, "provider_id", "unknown")
    try:
        clean = sanitize_tts_text(text, max_chars=settings.tts_max_text_characters)
    except TTSError as exc:
        METRICS.increment("smart_cricket_tts_failure", provider=provider_id, code=exc.error_code)
        return TTSResult("failed", provider_id, error_code=exc.error_code)

    attempts = max(1, min(settings.tts_retry_count + 1, 3))
    started = time.perf_counter()
    METRICS.increment("smart_cricket_tts_request", provider=provider_id)
    for attempt in range(attempts):
        try:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(
                    provider.synthesize,
                    clean,
                    request_id=request_id,
                    language=settings.tts_language_code,
                    voice=settings.tts_voice,
            )
            try:
                result = future.result(timeout=settings.tts_request_timeout_seconds)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
            if result.available:
                METRICS.increment("smart_cricket_tts_success", provider=result.provider)
                METRICS.observe("smart_cricket_tts_latency", time.perf_counter() - started, provider=result.provider)
                logger.info("tts_completed", extra={"event": "tts_completed", "request_id": request_id, "provider": result.provider, "status": result.status})
                return result
            METRICS.increment("smart_cricket_tts_fallback", provider=result.provider, code=result.error_code or "text_only")
            return result
        except concurrent.futures.TimeoutError:
            code = "tts_timeout"
        except TTSError as exc:
            code = exc.error_code
        except Exception:
            code = "tts_request_failed"
        METRICS.increment("smart_cricket_tts_failure", provider=provider_id, code=code)
        if code == "tts_timeout":
            METRICS.increment("smart_cricket_tts_timeout", provider=provider_id)
        if code not in TRANSIENT_ERROR_CODES or attempt >= attempts - 1:
            logger.warning("tts_fallback", extra={"event": "tts_fallback", "request_id": request_id, "provider": provider_id, "error_code": code})
            METRICS.increment("smart_cricket_tts_fallback", provider=provider_id, code=code)
            return TTSResult("failed", provider_id, error_code=code)
        time.sleep(min(0.25 * (2**attempt), 1.0))
    return TTSResult("failed", provider_id, error_code="tts_request_failed")


def google_tts_credentials_hint_available() -> bool:
    """Return a non-secret hint for release checks; does not validate live access."""

    return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT"))
