"""Validate Phase 14 voice output and write artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from voice.tts_service import build_frontend_audio_ready_response, synthesize_spoken_feedback, write_json  # noqa: E402
from voice.voice_config import (  # noqa: E402
    FRONTEND_AUDIO_READY_RESPONSE_PATH,
    PHASE13_SAMPLE_RESPONSE_PATH,
    PHASE14_VERSION,
    SAMPLE_VOICE_OUTPUT_PATH,
    VOICE_HEALTH_PATH,
    VOICE_REPORT_PATH,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _write_report(health: dict[str, Any], frontend_response: dict[str, Any]) -> None:
    with VOICE_REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Phase 14 Voice Output Report\n\n")
        f.write("## Validation Status\n\n")
        f.write(f"- Validation passed: `{health['validation_passed']}`\n")
        f.write(f"- Audio generated: `{health['audio_generated']}`\n")
        f.write(f"- Audio playable: `{health['audio_playable']}`\n")
        f.write(f"- Audio bytes: `{health['audio_bytes']}`\n")
        f.write(f"- Spoken feedback matches analysis: `{health['spoken_feedback_matches_visible_feedback']}`\n\n")
        f.write("## Audio-Ready Response\n\n")
        f.write(f"- Predicted shot: `{frontend_response['predicted_shot']}`\n")
        f.write(f"- Technique match score: `{frontend_response['technique_match_score']:.4f}`\n")
        f.write(f"- Audio path: `{frontend_response['audio']['audio_path']}`\n")
        f.write(f"- Audio format: `{frontend_response['audio']['audio_format']}`\n")
        f.write(f"- Spoken feedback: {frontend_response['spoken_feedback']}\n\n")
        f.write("## Engineering Notes\n\n")
        f.write(
            "- Phase 14 consumes existing spoken_feedback text and does not regenerate coaching content.\n"
            "- TTS is isolated behind a service boundary so the provider can be swapped later.\n"
            "- The frontend audio-ready response keeps text and audio metadata together.\n"
        )


def generate_phase14_artifacts() -> dict[str, Any]:
    analysis = _load_json(PHASE13_SAMPLE_RESPONSE_PATH)
    spoken_feedback = str(analysis.get("spoken_feedback", ""))
    voice_output = synthesize_spoken_feedback(spoken_feedback)
    frontend_response = build_frontend_audio_ready_response(
        analysis_response=analysis,
        voice_output=voice_output,
    )
    write_json(SAMPLE_VOICE_OUTPUT_PATH, voice_output.to_dict())
    write_json(FRONTEND_AUDIO_READY_RESPONSE_PATH, frontend_response)

    audio_generated = Path(voice_output.audio_path).is_file()
    audio_bytes = Path(voice_output.audio_path).stat().st_size if audio_generated else 0
    spoken_matches = voice_output.spoken_feedback == spoken_feedback.strip()
    health = {
        "phase": "Phase 14",
        "version": PHASE14_VERSION,
        "created_at": _utc_now(),
        "provider": voice_output.provider,
        "audio_generated": audio_generated,
        "audio_playable": bool(voice_output.playable and audio_bytes > 0),
        "audio_bytes": int(audio_bytes),
        "spoken_feedback_matches_visible_feedback": spoken_matches,
        "frontend_audio_ready_response_created": FRONTEND_AUDIO_READY_RESPONSE_PATH.is_file(),
        "validation_passed": bool(audio_generated and audio_bytes > 0 and spoken_matches),
        "output_files": {
            "sample_voice_output": str(SAMPLE_VOICE_OUTPUT_PATH),
            "frontend_audio_ready_response": str(FRONTEND_AUDIO_READY_RESPONSE_PATH),
            "voice_health": str(VOICE_HEALTH_PATH),
            "voice_report": str(VOICE_REPORT_PATH),
            "audio_output_dir": str(Path(voice_output.audio_path).parent),
            "audio_file": str(voice_output.audio_path),
        },
    }
    write_json(VOICE_HEALTH_PATH, health)
    _write_report(health, frontend_response)
    return health


def main() -> int:
    health = generate_phase14_artifacts()
    if not health["validation_passed"]:
        print("FAIL: Phase 14 voice output validation failed.")
        return 1
    print("PASS: Phase 14 voice output artifacts are valid.")
    print(f"Audio file: {health['output_files']['audio_file']}")
    print(f"Audio bytes: {health['audio_bytes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
