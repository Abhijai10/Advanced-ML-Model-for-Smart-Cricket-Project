"""Tests for FastAPI integration and upload safety."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.config import SETTINGS
from backend.api.evidence import EvidenceOutcome, evidence_is_reviewable
from backend.api.persistence import PersistenceResult
from backend.api.services import AnalysisTimeoutError, AnalysisWorkerError, AuthContext, _FEEDBACK_RATE_LIMIT_BUCKETS, _RATE_LIMIT_BUCKETS, enforce_auth
from backend.api.tts import TTSResult


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


def _fake_tts(spoken_feedback: str, **kwargs) -> TTSResult:
    return TTSResult(
        status="success",
        provider="test_tts",
        audio_bytes=b"RIFF0000WAVEfmt ",
        mime_type="audio/wav",
        extension=".wav",
    )


@unittest.skipIf(shutil.which("ffmpeg") is None, "ffmpeg is required for generated video fixtures")
class SmartCricketAPITests(unittest.TestCase):
    def setUp(self) -> None:
        _RATE_LIMIT_BUCKETS.clear()
        _FEEDBACK_RATE_LIMIT_BUCKETS.clear()
        self.client = TestClient(app)
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture_dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
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
        with patch("backend.api.services._run_raw_video_with_timeout", side_effect=_fake_analysis), patch(
            "backend.api.services.synthesize_with_config",
            side_effect=_fake_tts,
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
        self.assertIsInstance(payload["inference_ready"], bool)

    def test_readiness_endpoint(self) -> None:
        response = self.client.get("/ready")
        self.assertIn(response.status_code, {200, 503})
        payload = response.json() if response.status_code == 200 else response.json()["detail"]
        self.assertIn("checkpoint", payload["checks"])
        self.assertIn("temporary_storage", payload["checks"])

    def test_capabilities_do_not_expose_secrets(self) -> None:
        response = self.client.get("/capabilities")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("model_improvement_enabled", payload)
        self.assertIn("evidence_retention_enabled", payload)
        self.assertNotIn("supabase_service_role_key", payload)
        self.assertNotIn("audio_signing_secret", payload)

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
        with patch("backend.api.services._run_raw_video_with_timeout", side_effect=_fake_low_quality_analysis), patch(
            "backend.api.services.synthesize_with_config",
            side_effect=_fake_tts,
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

    def test_tts_failure_degrades_to_text_only_analysis(self) -> None:
        content = self._make_video("tts-failure.mp4", "blue")
        with patch("backend.api.services._run_raw_video_with_timeout", side_effect=_fake_analysis), patch(
            "backend.api.services.synthesize_with_config",
            return_value=TTSResult(status="failed", provider="google", error_code="tts_provider_unavailable"),
        ):
            response = self.client.post(
                "/analyze",
                files={"file": ("tts-failure.mp4", content, "video/mp4")},
                headers={"x-request-id": "test-request"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertFalse(payload["voice_output"]["available"])
        self.assertEqual(payload["voice_output"]["audio_url"], None)
        self.assertEqual(payload["api_metadata"]["voice_error"], "tts_provider_unavailable")

    def test_analysis_persistence_metadata_is_safe_when_unconfigured(self) -> None:
        content = self._make_video("history.mp4", "blue")
        response = self._post_video("history.mp4", content, "video/mp4")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        persistence = payload["api_metadata"]["analysis_persistence"]
        self.assertFalse(persistence["attempted"])
        self.assertFalse(persistence["stored"])
        self.assertEqual(persistence["error_code"], "missing_user")
        self.assertIsNone(payload["api_metadata"]["analysis_session_id"])

    def test_authenticated_analysis_returns_server_session_and_provenance(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(user_id="00000000-0000-0000-0000-000000000001", authorization_present=True)
        content = self._make_video("history-auth.mp4", "blue")
        with patch(
            "backend.api.services.persist_analysis_session",
            return_value=PersistenceResult(stored=True, status="stored", record_id="11111111-1111-1111-1111-111111111111"),
        ):
            response = self._post_video("history-auth.mp4", content, "video/mp4")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["api_metadata"]["analysis_session_id"], "11111111-1111-1111-1111-111111111111")
        provenance = payload["api_metadata"]["model_provenance"]
        self.assertTrue(provenance["model_version"])
        self.assertTrue(provenance["checkpoint_sha256"])
        self.assertEqual(payload["debug_metadata"]["model_version"], provenance["model_version"])

    def test_feedback_without_persistence_config_is_not_reported_saved(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(
            user_id="00000000-0000-0000-0000-000000000001", authorization_present=True
        )
        response = self.client.post(
            "/feedback",
            json={
                "analysis_session_id": "11111111-1111-1111-1111-111111111111",
                "prediction_was_correct": "incorrect",
                "corrected_shot": "pull_shot",
                "technique_feedback_rating": 4,
                "tip_flags": ["useful"],
                "notes": "Prediction missed the shot.",
                "consent_to_model_improvement": True,
            },
            headers={"x-request-id": "feedback-request"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["error_code"], "persistence_not_configured")

    def test_feedback_rejects_forged_trusted_fields(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(
            user_id="00000000-0000-0000-0000-000000000001", authorization_present=True
        )
        response = self.client.post(
            "/feedback",
            json={
                "user_id": "forged",
                "request_id": "forged",
                "clip_hash": "b" * 64,
                "predicted_shot": "cover_drive",
                "model_version": "forged",
                "prediction_was_correct": "correct",
                "consent_to_model_improvement": False,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_feedback_rejects_invalid_corrected_label(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(
            user_id="00000000-0000-0000-0000-000000000001", authorization_present=True
        )
        response = self.client.post(
            "/feedback",
            json={
                "analysis_session_id": "11111111-1111-1111-1111-111111111111",
                "prediction_was_correct": "incorrect",
                "corrected_shot": "helicopter_shot",
                "consent_to_model_improvement": True,
            },
        )
        self.assertIn(response.status_code, {422, 503})

    def test_feedback_valid_bound_session_without_evidence_is_not_review_candidate(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(user_id="00000000-0000-0000-0000-000000000001", authorization_present=True)
        analysis = {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "clip_hash": "a" * 64,
            "predicted_shot": "cover_drive",
            "storage_status": "not_retained",
            "model_provenance": {
                "model_version": "phase8-best-test",
                "pipeline_version": "phase12",
                "feature_contract_version": "smart_cricket_temporal_features_v1",
                "checkpoint_sha256": "b" * 64,
                "feature_schema_sha256": "c" * 64,
            },
        }
        with patch(
            "backend.api.routes.is_persistence_configured",
            return_value=True,
        ), patch(
            "backend.api.routes.load_analysis_session",
            return_value=PersistenceResult(stored=True, status="stored", record_id=analysis["id"], record=analysis),
        ), patch(
            "backend.api.routes.persist_feedback_record",
            return_value=PersistenceResult(stored=True, status="stored", record_id="feedback-1"),
        ):
            response = self.client.post(
                "/feedback",
                json={
                    "analysis_session_id": analysis["id"],
                    "prediction_was_correct": "incorrect",
                    "corrected_shot": "pull_shot",
                    "consent_to_model_improvement": True,
                },
            )
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        self.assertTrue(payload["stored"])
        self.assertFalse(payload["accepted_for_review"])
        self.assertEqual(payload["storage_status"], "stored")

    def test_feedback_duplicate_clip_hash_is_reported_without_saved_message(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(user_id="00000000-0000-0000-0000-000000000001", authorization_present=True)
        analysis = {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "clip_hash": "d" * 64,
            "predicted_shot": "cover_drive",
            "storage_status": "not_retained",
            "model_provenance": {"model_version": "phase8-best-test", "pipeline_version": "phase12"},
        }
        with patch("backend.api.routes.is_persistence_configured", return_value=True), patch(
            "backend.api.routes.load_analysis_session",
            return_value=PersistenceResult(stored=True, status="stored", record_id=analysis["id"], record=analysis),
        ), patch(
            "backend.api.routes.persist_feedback_record",
            return_value=PersistenceResult(stored=False, status="duplicate", duplicate=True, error_code="duplicate_record"),
        ):
            response = self.client.post(
                "/feedback",
                json={
                    "analysis_session_id": analysis["id"],
                    "prediction_was_correct": "correct",
                    "consent_to_model_improvement": True,
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "duplicate")
        self.assertTrue(payload["duplicate_clip_hash"])
        self.assertFalse(payload["stored"])

    def test_feedback_rejects_fabricated_or_cross_user_analysis_id(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(user_id="00000000-0000-0000-0000-000000000001", authorization_present=True)
        with patch("backend.api.routes.is_persistence_configured", return_value=True), patch(
            "backend.api.routes.load_analysis_session",
            return_value=PersistenceResult(stored=False, status="not_found", error_code="analysis_not_found"),
        ):
            response = self.client.post(
                "/feedback",
                json={
                    "analysis_session_id": "22222222-2222-2222-2222-222222222222",
                    "prediction_was_correct": "correct",
                    "consent_to_model_improvement": True,
                },
            )
        self.assertEqual(response.status_code, 404)

    def test_anonymous_feedback_cannot_enter_model_improvement_queue(self) -> None:
        with patch("backend.api.routes.is_persistence_configured", return_value=True):
            response = self.client.post(
                "/feedback",
                json={
                    "analysis_session_id": "11111111-1111-1111-1111-111111111111",
                    "prediction_was_correct": "correct",
                    "consent_to_model_improvement": True,
                },
            )
        self.assertEqual(response.status_code, 401)

    def test_feedback_missing_auth_is_rejected_when_auth_required(self) -> None:
        strict_settings = SimpleNamespace(
            require_auth=True,
            supabase_jwt_secret="secret",
            jwt_audience=None,
            jwt_issuer=None,
            supabase_publishable_key=None,
            require_feedback_persistence=True,
            rate_limit_per_minute=0,
            feedback_rate_limit_per_minute=0,
            trusted_proxy_hops=0,
            persistence_timeout_seconds=1,
            max_concurrent_analyses=1,
            analysis_queue_timeout_seconds=1,
            supabase_url=None,
            supabase_service_role_key=None,
            dev_dataset_endpoints=False,
            allowed_origins=(),
            max_upload_bytes=250 * 1024 * 1024,
            max_video_duration_seconds=20,
            max_video_pixels=1920 * 1080,
            uncertainty_confidence_threshold=55,
            min_clean_pose_frames=20,
            evidence_retention_days=30,
            evidence_storage_backend="none",
            evidence_local_storage_dir="/tmp/smart-cricket-evidence-test",
            evidence_supabase_bucket=None,
            allow_model_improvement_participation=False,
            consent_version="2026-08-04-v1",
            environment="test",
            analysis_execution_timeout_seconds=45,
            audio_signing_secret="x" * 40,
            audio_url_ttl_seconds=900,
            audio_max_url_ttl_seconds=3600,
            audio_retention_seconds=3600,
            jwks_timeout_seconds=1,
            jwks_cache_ttl_seconds=600,
            rate_limit_backend="memory",
        )
        with patch("backend.api.services.SETTINGS", strict_settings):
            response = self.client.post(
                "/feedback",
                json={
                    "analysis_session_id": "11111111-1111-1111-1111-111111111111",
                    "prediction_was_correct": "correct",
                    "consent_to_model_improvement": False,
                },
            )
        self.assertEqual(response.status_code, 401)

    def test_feedback_with_consent_without_retained_evidence_is_metadata_only(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(user_id="00000000-0000-0000-0000-000000000001", authorization_present=True)
        analysis = {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "clip_hash": "a" * 64,
            "predicted_shot": "cover_drive",
            "storage_status": "not_retained",
            "evidence_object_path": None,
            "model_provenance": {"model_version": "phase8-best-test", "pipeline_version": "phase12"},
        }
        captured: dict[str, dict] = {}

        def capture_feedback(row: dict) -> PersistenceResult:
            captured["row"] = row
            return PersistenceResult(stored=True, status="stored", record_id=row["id"])

        enabled_settings = replace(SETTINGS, allow_model_improvement_participation=True)
        with patch("backend.api.persistence.SETTINGS", enabled_settings), patch("backend.api.routes.is_persistence_configured", return_value=True), patch(
            "backend.api.routes.load_analysis_session",
            return_value=PersistenceResult(stored=True, status="stored", record_id=analysis["id"], record=analysis),
        ), patch("backend.api.routes.persist_feedback_record", side_effect=capture_feedback):
            response = self.client.post(
                "/feedback",
                json={
                    "analysis_session_id": analysis["id"],
                    "prediction_was_correct": "correct",
                    "consent_to_model_improvement": True,
                },
            )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertFalse(response.json()["accepted_for_review"])
        self.assertFalse(captured["row"]["accepted_for_review"])
        self.assertEqual(captured["row"]["dataset_eligibility_status"], "not_eligible")
        self.assertEqual(captured["row"]["review_status"], "evidence_not_retained")

    def test_feedback_with_consent_and_retained_evidence_can_enter_review(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(user_id="00000000-0000-0000-0000-000000000001", authorization_present=True)
        analysis = {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "clip_hash": "a" * 64,
            "predicted_shot": "cover_drive",
            "storage_status": "stored",
            "evidence_object_path": "user/session/object.webm",
            "retention_expires_at": "2999-01-01T00:00:00Z",
            "evidence_metadata": {
                "user_id": "00000000-0000-0000-0000-000000000001",
                "analysis_session_id": "11111111-1111-1111-1111-111111111111",
                "checksum_sha256": "b" * 64,
            },
            "model_provenance": {"model_version": "phase8-best-test", "pipeline_version": "phase12"},
        }
        self.assertTrue(evidence_is_reviewable(analysis))
        captured: dict[str, dict] = {}

        def capture_feedback(row: dict) -> PersistenceResult:
            captured["row"] = row
            return PersistenceResult(stored=True, status="stored", record_id=row["id"])

        enabled_settings = replace(SETTINGS, allow_model_improvement_participation=True)
        with patch("backend.api.persistence.SETTINGS", enabled_settings), patch("backend.api.routes.is_persistence_configured", return_value=True), patch(
            "backend.api.routes.load_analysis_session",
            return_value=PersistenceResult(stored=True, status="stored", record_id=analysis["id"], record=analysis),
        ), patch("backend.api.routes.persist_feedback_record", side_effect=capture_feedback):
            response = self.client.post(
                "/feedback",
                json={
                    "analysis_session_id": analysis["id"],
                    "prediction_was_correct": "correct",
                    "consent_to_model_improvement": True,
                },
            )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertTrue(response.json()["accepted_for_review"])
        self.assertEqual(captured["row"]["dataset_eligibility_status"], "pending_review")
        self.assertEqual(captured["row"]["review_status"], "candidate")

    def test_retained_evidence_withdrawn_deleted_or_expired_is_not_reviewable(self) -> None:
        base = {
            "storage_status": "stored",
            "evidence_object_path": "user/session/object.webm",
            "retention_expires_at": "2999-01-01T00:00:00Z",
            "evidence_metadata": {
                "user_id": "user",
                "analysis_session_id": "session",
                "checksum_sha256": "b" * 64,
            },
        }
        self.assertFalse(evidence_is_reviewable({**base, "withdrawn_at": "2026-01-01T00:00:00Z"}))
        self.assertFalse(evidence_is_reviewable({**base, "deleted_at": "2026-01-01T00:00:00Z"}))
        self.assertFalse(evidence_is_reviewable({**base, "retention_expires_at": "2000-01-01T00:00:00Z"}))

    def test_analyze_retention_storage_failure_is_reported_not_candidate(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(user_id="00000000-0000-0000-0000-000000000001", authorization_present=True)
        content = self._make_video("retain-failed.mp4", "blue")
        enabled_settings = replace(SETTINGS, allow_model_improvement_participation=True)
        with patch("backend.api.services.SETTINGS", enabled_settings), patch("backend.api.services._run_raw_video_with_timeout", side_effect=_fake_analysis), patch(
            "backend.api.services.synthesize_with_config",
            side_effect=_fake_tts,
        ), patch(
            "backend.api.services.get_evidence_provider"
        ) as provider_factory, patch("backend.api.services.persist_analysis_session") as persist_mock:
            provider_factory.return_value.retain_raw_clip.return_value = EvidenceOutcome(
                retained=False,
                status="failed",
                provider="local_development",
                error_code="storage_failed",
            )
            persist_mock.return_value = PersistenceResult(stored=True, status="stored", record_id="11111111-1111-1111-1111-111111111111")
            response = self.client.post(
                "/analyze",
                data={"retain_evidence": "true"},
                files={"file": ("retain-failed.mp4", content, "video/mp4")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["api_metadata"]["evidence_retention"]["status"], "failed")

    def test_analyze_retention_request_is_disabled_when_model_improvement_off(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(user_id="00000000-0000-0000-0000-000000000001", authorization_present=True)
        content = self._make_video("retain-disabled.mp4", "blue")
        with patch("backend.api.services._run_raw_video_with_timeout", side_effect=_fake_analysis), patch(
            "backend.api.services.synthesize_with_config",
            side_effect=_fake_tts,
        ), patch("backend.api.services.get_evidence_provider") as provider_factory:
            response = self.client.post(
                "/analyze",
                data={"retain_evidence": "true"},
                files={"file": ("retain-disabled.mp4", content, "video/mp4")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["api_metadata"]["evidence_retention"]["status"], "disabled")
        provider_factory.assert_not_called()

    def test_retained_evidence_is_deleted_if_analysis_persistence_fails(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(user_id="00000000-0000-0000-0000-000000000001", authorization_present=True)
        content = self._make_video("orphan.mp4", "blue")
        provider = SimpleNamespace()
        provider.retain_raw_clip = Mock(
            return_value=EvidenceOutcome(
                retained=True,
                status="stored",
                provider="local_development",
                object_path="user/session/object.mp4",
                metadata={
                    "user_id": "00000000-0000-0000-0000-000000000001",
                    "analysis_session_id": "session",
                    "checksum_sha256": "b" * 64,
                    "retention_expires_at": "2999-01-01T00:00:00Z",
                },
            )
        )
        provider.delete = Mock(return_value=EvidenceOutcome(False, "deleted", "local_development", "user/session/object.mp4"))
        enabled_settings = replace(SETTINGS, allow_model_improvement_participation=True)
        with patch("backend.api.services.SETTINGS", enabled_settings), patch("backend.api.services._run_raw_video_with_timeout", side_effect=_fake_analysis), patch(
            "backend.api.services.synthesize_with_config",
            side_effect=_fake_tts,
        ), patch("backend.api.services.get_evidence_provider", return_value=provider), patch(
            "backend.api.services.persist_analysis_session",
            return_value=PersistenceResult(stored=False, status="temporary_failure", error_code="persistence_failed"),
        ):
            response = self.client.post(
                "/analyze",
                data={"retain_evidence": "true"},
                files={"file": ("orphan.mp4", content, "video/mp4")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        provider.delete.assert_called_once_with("user/session/object.mp4")
        self.assertEqual(response.json()["api_metadata"]["evidence_retention"]["status"], "deleted_after_persistence_failure")

    def test_analysis_overload_returns_429_retry_after(self) -> None:
        content = self._make_video("busy.mp4", "blue")
        with patch("backend.api.services._ANALYSIS_SEMAPHORE") as semaphore:
            semaphore.acquire.return_value = False
            response = self.client.post(
                "/analyze",
                files={"file": ("busy.mp4", content, "video/mp4")},
            )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["detail"]["error_code"], "analysis_overloaded")
        self.assertIn("retry-after", {key.lower(): value for key, value in response.headers.items()})

    def test_analysis_timeout_returns_stable_503(self) -> None:
        content = self._make_video("timeout.mp4", "blue")
        with patch("backend.api.services._run_raw_video_with_timeout", side_effect=AnalysisTimeoutError("timed out")):
            response = self.client.post(
                "/analyze",
                files={"file": ("timeout.mp4", content, "video/mp4")},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["error_code"], "analysis_timeout")
        self.assertIn("retry-after", {key.lower(): value for key, value in response.headers.items()})

    def test_worker_failure_returns_safe_category(self) -> None:
        content = self._make_video("worker-failure.mp4", "blue")
        with patch(
            "backend.api.services._run_raw_video_with_timeout",
            side_effect=AnalysisWorkerError("native failure", detail_code="mediapipe_init_failed"),
        ):
            response = self.client.post(
                "/analyze",
                files={"file": ("worker-failure.mp4", content, "video/mp4")},
            )
        self.assertEqual(response.status_code, 503)
        detail = response.json()["detail"]
        self.assertEqual(detail["error_code"], "inference_worker_failed")
        self.assertEqual(detail["failure_category"], "MEDIAPIPE_INIT_FAILED")
        self.assertNotIn("native failure", str(detail))

    def test_general_product_feedback_never_enters_training_queue(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(
            user_id="00000000-0000-0000-0000-000000000001", authorization_present=True
        )
        captured: dict[str, dict] = {}

        def capture_feedback(row: dict) -> PersistenceResult:
            captured["row"] = row
            return PersistenceResult(stored=True, status="stored", record_id=row["id"])

        with patch("backend.api.routes.is_persistence_configured", return_value=True), patch(
            "backend.api.routes.persist_product_feedback_record",
            side_effect=capture_feedback,
        ):
            response = self.client.post(
                "/product-feedback",
                json={
                    "usability_rating": 4,
                    "bug_category": "camera",
                    "feature_request": "offline mode",
                    "notes": "The upload fallback was clear.",
                    "page_context": "camera",
                },
            )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertFalse(response.json()["accepted_for_review"])
        self.assertEqual(captured["row"]["bug_category"], "camera")
        self.assertEqual(captured["row"]["feature_request"], "offline mode")
        self.assertEqual(captured["row"]["status"], "new")


if __name__ == "__main__":
    unittest.main()
