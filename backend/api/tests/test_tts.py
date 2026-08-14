"""Tests for the production TTS provider boundary."""

from __future__ import annotations

import time
import unittest
from dataclasses import replace
from unittest.mock import patch

from backend.api.config import SETTINGS
from backend.api.tts import TTSError, TTSResult, sanitize_tts_text, synthesize_with_config


class TTSProviderTests(unittest.TestCase):
    def test_sanitize_tts_text_removes_control_characters_and_caps_length(self) -> None:
        clean = sanitize_tts_text("  Keep\tstill\x00\nand finish.  ", max_chars=14)
        self.assertEqual(clean, "Keep still and")

    def test_text_only_provider_is_explicit(self) -> None:
        settings = replace(SETTINGS, tts_enabled=False)
        result = synthesize_with_config("Keep the head still.", request_id="request-1", settings=settings)
        self.assertFalse(result.available)
        self.assertEqual(result.provider, "text_only")
        self.assertEqual(result.error_code, "tts_unconfigured")

    def test_timeout_degrades_to_safe_error_code(self) -> None:
        class SlowProvider:
            provider_id = "slow"

            def synthesize(self, *args, **kwargs):
                time.sleep(0.2)
                return TTSResult("success", "slow", b"RIFF0000WAVE", "audio/wav", ".wav")

        settings = replace(SETTINGS, tts_request_timeout_seconds=1, tts_retry_count=0)
        with patch("backend.api.tts._provider_for_settings", return_value=SlowProvider()):
            result = synthesize_with_config("Keep the head still.", request_id="request-1", settings=settings)
        self.assertTrue(result.available)

        settings = replace(SETTINGS, tts_request_timeout_seconds=1, tts_retry_count=0)
        with patch("backend.api.tts._provider_for_settings", return_value=SlowProvider()):
            with patch.object(SlowProvider, "synthesize", side_effect=lambda *a, **k: time.sleep(2)):
                result = synthesize_with_config("Keep the head still.", request_id="request-1", settings=settings)
        self.assertFalse(result.available)
        self.assertEqual(result.error_code, "tts_timeout")

    def test_invalid_format_returns_safe_failure(self) -> None:
        class BadFormatProvider:
            provider_id = "bad_format"

            def synthesize(self, *args, **kwargs):
                raise TTSError("tts_unsupported_format", "bad format")

        with patch("backend.api.tts._provider_for_settings", return_value=BadFormatProvider()):
            result = synthesize_with_config("Keep the head still.", request_id="request-1")
        self.assertFalse(result.available)
        self.assertEqual(result.error_code, "tts_unsupported_format")

    def test_google_missing_dependency_or_credentials_is_normalized(self) -> None:
        settings = replace(SETTINGS, tts_provider="google", tts_audio_format="mp3")
        result = synthesize_with_config("Keep the head still.", request_id="request-1", settings=settings)
        self.assertFalse(result.available)
        self.assertIn(result.error_code, {"tts_provider_unavailable", "tts_auth_failed"})


if __name__ == "__main__":
    unittest.main()
