"""Tests for the release-candidate configuration checker."""

from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch

from backend.api.config import SETTINGS
from scripts import verify_release_candidate


class ReleaseCandidateCheckTests(unittest.TestCase):
    def test_checks_include_tts_audio_and_no_secret_values(self) -> None:
        settings = replace(
            SETTINGS,
            environment="test",
            tts_provider="text_only",
            audio_storage_backend="local",
            supabase_service_role_key="super-secret-service-key",
        )
        with patch("scripts.verify_release_candidate.SETTINGS", settings):
            checks = verify_release_candidate.run_checks()
        names = {check.name for check in checks}
        self.assertIn("TTS provider", names)
        self.assertIn("Audio storage", names)
        rendered = " ".join(f"{check.name} {check.status} {check.detail}" for check in checks)
        self.assertNotIn("super-secret-service-key", rendered)


if __name__ == "__main__":
    unittest.main()
