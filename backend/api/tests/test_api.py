"""Tests for FastAPI integration and upload safety."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.app import app
from ml.src.voice.tts_service import VoiceOutput


def _fake_analysis(video_path: Path) -> dict:
    digest = hashlib.sha256(video_path.read_bytes()).hexdigest()
    shot = "cover_drive" if int(digest[0], 16) % 2 == 0 else "pull_shot"
    return {
        "predicted_shot": shot,
        "shot_confidence": 0.82,
        "technique_match_score": 74.0,
        "detected_issues": [],
        "coaching_tips": ["Keep the head still through contact."],
        "detailed_feedback": f"Digest {digest[:8]} was analyzed from uploaded bytes.",
        "spoken_feedback": "Keep the head still through contact.",
        "debug_metadata": {"digest": digest},
        "source_metadata": {
            "file_name": video_path.name,
            "frames_extracted": 60,
            "frames_after_cleaning": 60,
            "resampled_timing": [
                {"sequence_frame": i, "source_frame": i, "timestamp_seconds": i / 24.0}
                for i in range(60)
            ],
        },
        "prediction": {"class_probabilities": {shot: 0.82}},
        "segmentation": {
            "start_frame": 6,
            "end_frame": 30,
            "peak_frame": 18,
            "prediction_trigger_frame": 30,
            "completed": True,
            "completion_reason": "test",
            "trigger_count": 1,
        },
    }


def _fake_low_quality_analysis(video_path: Path) -> dict:
    payload = _fake_analysis(video_path)
    payload["shot_confidence"] = 0.31
    payload["source_metadata"]["frames_after_cleaning"] = 4
    return payload


def _fake_voice(spoken_feedback: str, **kwargs) -> VoiceOutput:
    path = Path(tempfile.gettempdir()) / kwargs["output_path"].name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF0000WAVE")
    return VoiceOutput(
        spoken_feedback=spoken_feedback,
        provider="test_tts",
        audio_path=str(path),
        audio_format="wav",
        audio_bytes=path.stat().st_size,
        playable=True,
        generated_at="2026-08-04T00:00:00Z",
        voice_name=None,
        speech_rate=175,
    )


@unittest.skipIf(shutil.which("ffmpeg") is None, "ffmpeg is required for generated video fixtures")
class SmartCricketAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture_dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _make_video(self, name: str, color: str) -> bytes:
        path = self.fixture_dir / name
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s=160x120:d=1:r=24",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            check=True,
        )
        return path.read_bytes()

    def _post_video(self, filename: str, content: bytes, media_type: str = "video/mp4"):
        with patch("backend.api.services.analyze_raw_video", side_effect=_fake_analysis), patch(
            "backend.api.services.synthesize_spoken_feedback",
            side_effect=_fake_voice,
        ):
            return self.client.post(
                "/analyze",
                files={"file": (filename, content, media_type)},
                headers={"x-request-id": "test-request"},
            )

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["inference_ready"])

    def test_readiness_endpoint(self) -> None:
        response = self.client.get("/ready")
        self.assertIn(response.status_code, {200, 503})
        payload = response.json() if response.status_code == 200 else response.json()["detail"]
        self.assertIn("checkpoint", payload["checks"])
        self.assertIn("temporary_storage", payload["checks"])

    def test_analyze_uses_uploaded_bytes_even_with_known_dataset_filename(self) -> None:
        content = self._make_video("source.mp4", "blue")
        response = self._post_video("cover_drive_average_02.mov", content, "video/quicktime")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        digest = hashlib.sha256(content).hexdigest()
        self.assertEqual(payload["debug_metadata"]["digest"], digest)
        self.assertEqual(payload["api_metadata"]["analysis_mode"], "raw_video_upload")
        self.assertEqual(payload["analysis_quality"]["status"], "ok")
        self.assertIn("/audio/test-request-", payload["voice_output"]["audio_url"])

    def test_low_quality_result_is_marked_insufficient_quality(self) -> None:
        content = self._make_video("low-quality.mp4", "blue")
        with patch("backend.api.services.analyze_raw_video", side_effect=_fake_low_quality_analysis), patch(
            "backend.api.services.synthesize_spoken_feedback",
            side_effect=_fake_voice,
        ):
            response = self.client.post(
                "/analyze",
                files={"file": ("low-quality.mp4", content, "video/mp4")},
                headers={"x-request-id": "test-request"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["analysis_quality"]["status"], "insufficient_quality")
        self.assertGreaterEqual(len(payload["analysis_quality"]["reasons"]), 2)

    def test_same_video_under_different_filenames_returns_same_digest(self) -> None:
        content = self._make_video("same.mp4", "red")
        first = self._post_video("one_name.mp4", content).json()
        second = self._post_video("another_name.mp4", content).json()
        self.assertEqual(first["debug_metadata"]["digest"], second["debug_metadata"]["digest"])

    def test_different_content_with_same_filename_returns_different_digest(self) -> None:
        blue = self._make_video("blue.mp4", "blue")
        green = self._make_video("green.mp4", "green")
        first = self._post_video("same_name.mp4", blue).json()
        second = self._post_video("same_name.mp4", green).json()
        self.assertNotEqual(first["debug_metadata"]["digest"], second["debug_metadata"]["digest"])

    def test_invalid_bytes_with_known_filename_are_rejected_before_inference(self) -> None:
        response = self._post_video("cover_drive_average_02.mov", b"test-video", "video/quicktime")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["error_code"], "invalid_video_bytes")

    def test_accepts_mp4_mov_and_webm_containers(self) -> None:
        cases = [
            ("sample.mp4", "blue", "video/mp4"),
            ("sample.mov", "red", "video/quicktime"),
            ("sample.webm", "green", "video/webm"),
        ]
        for filename, color, media_type in cases:
            with self.subTest(filename=filename):
                response = self._post_video(filename, self._make_video(filename, color), media_type)
                self.assertEqual(response.status_code, 200, response.text)

    def test_rejects_unsupported_file_type(self) -> None:
        response = self.client.post(
            "/analyze",
            files={"file": ("shot.txt", b"not-video", "text/plain")},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["error_code"], "unsupported_file_type")

    def test_dataset_sample_endpoint_is_disabled_by_default(self) -> None:
        response = self.client.post("/dev/analyze-dataset?file_name=cover_drive_average_02.mov")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["error_code"], "dev_endpoint_disabled")


if __name__ == "__main__":
    unittest.main()
