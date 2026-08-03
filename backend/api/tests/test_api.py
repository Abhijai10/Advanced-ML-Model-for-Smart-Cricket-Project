"""Tests for Phase 13 FastAPI integration."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from backend.api.app import app


class SmartCricketAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["inference_ready"])

    def test_analyze_known_dataset_video(self) -> None:
        response = self.client.post(
            "/analyze",
            files={"file": ("cover_drive_average_02.mov", b"test-video", "video/quicktime")},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["predicted_shot"], "cover_drive")
        self.assertIn("coaching_tips", payload)
        self.assertTrue(payload["spoken_feedback"])
        self.assertIn("api_metadata", payload)
        self.assertTrue(payload["voice_output"]["available"])
        self.assertEqual(payload["voice_output"]["audio_format"], "wav")

    def test_unknown_video_returns_clean_error(self) -> None:
        response = self.client.post(
            "/analyze",
            files={"file": ("unknown_video.mov", b"test-video", "video/quicktime")},
        )
        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertEqual(detail["error_code"], "unknown_dataset_video")

    def test_rejects_unsupported_file_type(self) -> None:
        response = self.client.post(
            "/analyze",
            files={"file": ("shot.txt", b"not-video", "text/plain")},
        )
        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertEqual(detail["error_code"], "unsupported_file_type")


if __name__ == "__main__":
    unittest.main()
