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
        "audio_storage_backend": "local",
        "audio_supabase_bucket": None,
        "supabase_url": None,
        "environment": "test",
        "supabase_service_role_key": "service-role-key",
        "persistence_timeout_seconds": 1,
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

    def test_get_audio_rejects_traversal_and_unsupported_extension(self) -> None:
        with patch("backend.api.audio.SETTINGS", _settings()):
            with self.assertRaises(HTTPException):
                audio.get_audio("../sample.wav", expires=int(time.time()) + 60, signature="bad")
            with self.assertRaises(HTTPException):
                audio.get_audio("sample.txt", expires=int(time.time()) + 60, signature="bad")

    def test_store_audio_artifact_preserves_mime_extension_and_hides_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("backend.api.audio.AUDIO_OUTPUT_DIR", Path(tmp)), patch("backend.api.audio.SETTINGS", _settings()):
                result = audio.store_audio_artifact(
                    b"RIFF0000WAVEfmt ",
                    provider="test_tts",
                    mime_type="audio/wav",
                    extension=".wav",
                    request_id="request-1",
                )
            self.assertTrue(result.ok)
            artifact = result.artifact
            self.assertIsNotNone(artifact)
            assert artifact is not None
            self.assertEqual(artifact.mime_type, "audio/wav")
            self.assertEqual(artifact.extension, "wav")
            self.assertIn("/audio/", artifact.audio_url or "")
            self.assertNotIn(str(tmp), str(artifact.public_dict()))

    def test_store_audio_rejects_mismatched_mime(self) -> None:
        with patch("backend.api.audio.SETTINGS", _settings()):
            result = audio.store_audio_artifact(
                b"RIFF0000WAVEfmt ",
                provider="test_tts",
                mime_type="audio/mpeg",
                extension=".wav",
                request_id="request-1",
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "mismatched_audio_mime_type")

    def test_refresh_rejects_retention_expired_local_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.wav"
            path.write_bytes(b"RIFF0000WAVEfmt ")
            now = time.time()
            os.utime(path, (now - 120, now - 120))
            with patch("backend.api.audio.AUDIO_OUTPUT_DIR", Path(tmp)), patch("backend.api.audio.SETTINGS", _settings(audio_retention_seconds=60)):
                with self.assertRaises(HTTPException) as ctx:
                    audio.refresh_local_audio_url("artifact.wav")
            self.assertEqual(ctx.exception.status_code, 410)

    def test_cleanup_deletes_expired_audio_files_and_supports_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "old.wav"
            old_mp3 = Path(tmp) / "old.mp3"
            fresh = Path(tmp) / "fresh.wav"
            old.write_bytes(b"old")
            old_mp3.write_bytes(b"ID3old")
            fresh.write_bytes(b"fresh")
            now = time.time()
            os.utime(old, (now - 120, now - 120))
            os.utime(old_mp3, (now - 120, now - 120))
            os.utime(fresh, (now, now))
            with patch("backend.api.audio.AUDIO_OUTPUT_DIR", Path(tmp)), patch("backend.api.audio.SETTINGS", _settings(audio_retention_seconds=60)):
                dry = audio.cleanup_expired_audio(now=now, dry_run=True)
                result = audio.cleanup_expired_audio(now=now)
            self.assertEqual(dry.expired, 2)
            self.assertEqual(dry.deleted, 0)
            self.assertEqual(result.deleted, 2)
            self.assertFalse(old.exists())
            self.assertFalse(old_mp3.exists())
            self.assertTrue(fresh.exists())


if __name__ == "__main__":
    unittest.main()
