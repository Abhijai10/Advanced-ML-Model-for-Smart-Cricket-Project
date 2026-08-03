"""Tests for Phase 14 voice output service."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from voice.tts_service import build_frontend_audio_ready_response, synthesize_spoken_feedback, validate_spoken_feedback
from voice.voice_config import VoiceConfig


class TTSServiceTests(unittest.TestCase):
    def test_validate_spoken_feedback_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            validate_spoken_feedback("   ")

    def test_validate_spoken_feedback_rejects_too_long(self) -> None:
        with self.assertRaises(ValueError):
            validate_spoken_feedback("x" * 20, VoiceConfig(max_text_chars=10))

    def test_frontend_audio_ready_response_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / "voice.wav"
            voice = synthesize_spoken_feedback(
                "Keep your head steady.",
                output_path=audio_path,
            )
            response = build_frontend_audio_ready_response(
                analysis_response={
                    "predicted_shot": "cover_drive",
                    "shot_confidence": 0.9,
                    "technique_match_score": 88.0,
                    "coaching_tips": ["Keep your head steady."],
                    "debug_metadata": {},
                },
                voice_output=voice,
            )
            self.assertTrue(response["audio"]["available"])
            self.assertEqual(response["spoken_feedback"], "Keep your head steady.")


if __name__ == "__main__":
    unittest.main()
