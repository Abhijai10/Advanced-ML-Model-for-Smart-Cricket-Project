"""Configuration for Phase 14 voice output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ML_ROOT = Path(__file__).resolve().parents[2]
PHASE14_DIR = ML_ROOT / "artifacts" / "phase14"
AUDIO_OUTPUT_DIR = PHASE14_DIR / "audio_output"
PHASE13_SAMPLE_RESPONSE_PATH = ML_ROOT / "artifacts" / "phase13" / "sample_api_response.json"

VOICE_HEALTH_PATH = PHASE14_DIR / "voice_health.json"
VOICE_REPORT_PATH = PHASE14_DIR / "voice_output_report.md"
SAMPLE_VOICE_OUTPUT_PATH = PHASE14_DIR / "sample_voice_output.json"
FRONTEND_AUDIO_READY_RESPONSE_PATH = PHASE14_DIR / "frontend_audio_ready_response.json"

PHASE14_VERSION = "phase_14_voice_output_v1"
DEFAULT_AUDIO_FILENAME = "sample_spoken_feedback.wav"


@dataclass(frozen=True)
class VoiceConfig:
    """Provider-separated TTS configuration."""

    provider: str = "macos_say_with_wav_fallback"
    speech_rate: int = 175
    audio_format: str = "wav"
    voice_name: str | None = None
    max_text_chars: int = 500
    sample_rate: int = 22050


DEFAULT_VOICE_CONFIG = VoiceConfig()
