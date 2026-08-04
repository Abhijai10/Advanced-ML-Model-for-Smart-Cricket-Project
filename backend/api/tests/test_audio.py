"""Signed audio access and cleanup tests."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from backend.api import audio


def _settings(**overrides):
    base = {
        "audio_signing_secret": "a" * 40,
        "audio_url_ttl_seconds": 900,
        "audio_max_url_ttl_seconds": 3600,
        "audio_retention_seconds": 60,
        "environment": "test",
        "supabase_service_role_key": "service-role-key",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class AudioSecurityTests(unittest.TestCase):
    def test_audio_signature_rejects_expired_and_far_future_links(self) -> None:
        with patch("backend.api.audio.SETTINGS", _settings()):
            url = audio.sign_audio_url("sample.wav", ttl_seconds=999999)
            expires = int(url.split("expires=", 1)[1].split("&", 1)[0])
            signature = url.split("signature=", 1)[1]
            self.assertLessEqual(expires - int(time.time()), 3600)
            self.assertTrue(audio._valid_signature("sample.wav", expires, signature))
            self.assertFalse(audio._valid_signature("sample.wav", int(time.time()) - 1, signature))
            self.assertFalse(audio._valid_signature("sample.wav", int(time.time()) + 999999, signature))

    def test_audio_secret_missing_fails_outside_local_modes(self) -> None:
        with patch("backend.api.audio.SETTINGS", _settings(audio_signing_secret=None, environment="production")):
            with self.assertRaises(HTTPException):
                audio._audio_secret()

    def test_audio_secret_must_not_reuse_service_role_key(self) -> None:
        with patch("backend.api.audio.SETTINGS", _settings(audio_signing_secret="service-role-key")):
            with self.assertRaises(HTTPException):
                audio._audio_secret()

    def test_cleanup_deletes_expired_wav_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "old.wav"
            fresh = Path(tmp) / "fresh.wav"
            old.write_bytes(b"old")
            fresh.write_bytes(b"fresh")
            now = time.time()
            os.utime(old, (now - 120, now - 120))
            os.utime(fresh, (now, now))
            with patch("backend.api.audio.AUDIO_OUTPUT_DIR", Path(tmp)), patch("backend.api.audio.SETTINGS", _settings(audio_retention_seconds=60)):
                result = audio.cleanup_expired_audio(now=now)
            self.assertEqual(result.deleted, 1)
            self.assertFalse(old.exists())
            self.assertTrue(fresh.exists())


if __name__ == "__main__":
    unittest.main()
