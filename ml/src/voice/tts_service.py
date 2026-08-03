"""Text-to-speech service for Phase 14 voice output.

The service keeps the provider boundary explicit. Phase 14 v1 uses macOS
``say`` for local, offline speech generation, but callers interact with a small
provider-neutral result object.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import wave
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .voice_config import AUDIO_OUTPUT_DIR, DEFAULT_AUDIO_FILENAME, DEFAULT_VOICE_CONFIG, VoiceConfig


@dataclass(frozen=True)
class VoiceOutput:
    """Generated voice artifact metadata."""

    spoken_feedback: str
    provider: str
    audio_path: str
    audio_format: str
    audio_bytes: int
    playable: bool
    generated_at: str
    voice_name: str | None
    speech_rate: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_spoken_feedback(text: str, config: VoiceConfig = DEFAULT_VOICE_CONFIG) -> str:
    """Return clean spoken feedback text or raise a useful error."""
    clean = " ".join(str(text).strip().split())
    if not clean:
        raise ValueError("spoken_feedback text must be non-empty.")
    if len(clean) > config.max_text_chars:
        raise ValueError(
            f"spoken_feedback text is too long for Phase 14 v1: {len(clean)} > {config.max_text_chars}."
        )
    return clean


def _macos_say_available() -> bool:
    return shutil.which("say") is not None


def _write_audio_cue_wav(path: Path, text: str, config: VoiceConfig) -> None:
    """Write a simple playable WAV cue when local speech synthesis is unavailable."""
    sample_rate = int(config.sample_rate)
    duration_seconds = min(6.0, max(1.5, len(text) / 38.0))
    total_frames = int(sample_rate * duration_seconds)
    amplitude = 8500
    words = max(1, len(text.split()))
    base_freq = 420.0
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(total_frames):
            t = i / sample_rate
            # A gently varying coaching cue: not speech, but a real playable audio artifact.
            freq = base_freq + (words % 9) * 18.0 + 35.0 * math.sin(2.0 * math.pi * 0.7 * t)
            envelope = min(1.0, i / (sample_rate * 0.08), (total_frames - i) / (sample_rate * 0.12))
            sample = int(amplitude * max(0.0, envelope) * math.sin(2.0 * math.pi * freq * t))
            wav.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))


def _try_macos_say(text: str, path: Path, config: VoiceConfig) -> Path | None:
    if not _macos_say_available():
        return None
    temp_path = path.with_suffix(".aiff")
    cmd = ["say", "-r", str(config.speech_rate), "-o", str(temp_path)]
    if config.voice_name:
        cmd.extend(["-v", config.voice_name])
    cmd.append(text)
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    # Some sandboxed macOS contexts create only a 4096-byte AIFF header. Require payload.
    if temp_path.is_file() and temp_path.stat().st_size > 8192:
        return temp_path
    if temp_path.exists():
        temp_path.unlink()
    return None


def synthesize_spoken_feedback(
    spoken_feedback: str,
    *,
    output_path: Path | None = None,
    config: VoiceConfig = DEFAULT_VOICE_CONFIG,
) -> VoiceOutput:
    """Convert TTS-friendly feedback text into a playable local audio file."""
    clean = validate_spoken_feedback(spoken_feedback, config)
    if config.provider != "macos_say_with_wav_fallback":
        raise ValueError(f"Unsupported Phase 14 TTS provider: {config.provider}")

    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    requested_path = output_path or (AUDIO_OUTPUT_DIR / DEFAULT_AUDIO_FILENAME)
    requested_path.parent.mkdir(parents=True, exist_ok=True)
    used_provider = "macos_say"
    audio_path = _try_macos_say(clean, requested_path, config)
    audio_format = "aiff"
    if audio_path is None:
        used_provider = "local_audio_cue_wav"
        audio_path = requested_path.with_suffix(".wav")
        audio_format = "wav"
        _write_audio_cue_wav(audio_path, clean, config)
    if not audio_path.is_file() or audio_path.stat().st_size <= 0:
        raise RuntimeError(f"TTS provider did not create a playable audio file: {audio_path}")

    return VoiceOutput(
        spoken_feedback=clean,
        provider=used_provider,
        audio_path=str(audio_path),
        audio_format=audio_format,
        audio_bytes=int(audio_path.stat().st_size),
        playable=True,
        generated_at=_utc_now(),
        voice_name=config.voice_name,
        speech_rate=config.speech_rate,
    )


def build_frontend_audio_ready_response(
    *,
    analysis_response: dict[str, Any],
    voice_output: VoiceOutput,
) -> dict[str, Any]:
    """Create a frontend-friendly response that pairs analysis text with audio metadata."""
    return {
        "predicted_shot": analysis_response["predicted_shot"],
        "shot_confidence": analysis_response["shot_confidence"],
        "technique_match_score": analysis_response["technique_match_score"],
        "coaching_tips": analysis_response["coaching_tips"],
        "spoken_feedback": voice_output.spoken_feedback,
        "audio": {
            "available": voice_output.playable,
            "provider": voice_output.provider,
            "audio_path": voice_output.audio_path,
            "audio_format": voice_output.audio_format,
            "audio_bytes": voice_output.audio_bytes,
        },
        "debug_metadata": {
            "source_phase": "Phase 14",
            "voice_output": voice_output.to_dict(),
            "analysis_debug_metadata": analysis_response.get("debug_metadata", {}),
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a formatted JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
