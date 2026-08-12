"""Regression tests for evidence lifecycle and provider-aware deletion."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import urllib.error

from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.config import SETTINGS
from backend.api.evidence import EvidenceOutcome, SupabaseEvidenceProvider, delete_evidence_for_record
from backend.api.persistence import PersistenceResult
from backend.api.services import AuthContext, enforce_auth


class EvidenceLifecycleTests(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_local_evidence_deletion_uses_stored_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            object_path = "user/session/object.webm"
            evidence_file = root / object_path
            evidence_file.parent.mkdir(parents=True)
            evidence_file.write_bytes(b"video")
            evidence_file.with_suffix(".webm.metadata.json").write_text("{}", encoding="utf-8")
            record = {
                "storage_status": "stored",
                "evidence_object_path": object_path,
                "evidence_metadata": {"storage_provider": "local_development"},
            }
            with patch("backend.api.evidence.SETTINGS", replace(SETTINGS, evidence_local_storage_dir=str(root))):
                outcome = delete_evidence_for_record(record)
            self.assertEqual(outcome.status, "deleted")
            self.assertFalse(evidence_file.exists())

    def test_supabase_evidence_deletion_uses_stored_provider(self) -> None:
        record = {
            "storage_status": "stored",
            "evidence_object_path": "user/session/object.webm",
            "evidence_metadata": {"storage_provider": "supabase_storage"},
        }
        with patch(
            "backend.api.evidence.SupabaseEvidenceProvider.delete",
            return_value=EvidenceOutcome(False, "deleted", "supabase_storage", "user/session/object.webm"),
        ) as delete_mock:
            outcome = delete_evidence_for_record(record)
        delete_mock.assert_called_once_with("user/session/object.webm")
        self.assertEqual(outcome.status, "deleted")

    def test_supabase_reviewer_access_uses_signed_url_and_caps_ttl(self) -> None:
        settings = replace(
            SETTINGS,
            supabase_url="https://project.supabase.co",
            supabase_service_role_key="service-secret",
            evidence_supabase_bucket="smart-cricket-evidence",
        )

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self) -> bytes:
                return b'{"signedURL": "/storage/v1/object/sign/smart-cricket-evidence/user/session/object.webm?token=abc"}'

        with patch("backend.api.evidence.SETTINGS", settings), patch(
            "backend.api.evidence.urllib.request.urlopen",
            return_value=FakeResponse(),
        ) as urlopen:
            outcome = SupabaseEvidenceProvider().reviewer_access_url("user/session/object.webm", ttl_seconds=999)

        request = urlopen.call_args.args[0]
        self.assertEqual(outcome.status, "stored")
        self.assertEqual(outcome.metadata["ttl_seconds"], 300)
        self.assertEqual(outcome.metadata["access_type"], "supabase_storage_signed_url")
        self.assertTrue(outcome.metadata["signed_url"].startswith("https://project.supabase.co/storage/v1/object/sign/"))
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.headers["Authorization"], "Bearer service-secret")
        self.assertIn(b'"expiresIn": 300', request.data)

    def test_supabase_reviewer_access_rejects_traversal(self) -> None:
        settings = replace(
            SETTINGS,
            supabase_url="https://project.supabase.co",
            supabase_service_role_key="service-secret",
            evidence_supabase_bucket="smart-cricket-evidence",
        )
        with patch("backend.api.evidence.SETTINGS", settings):
            outcome = SupabaseEvidenceProvider().reviewer_access_url("../object.webm")

        self.assertEqual(outcome.status, "failed")
        self.assertEqual(outcome.error_code, "invalid_evidence_path")

    def test_supabase_delete_rejects_traversal_without_http_call(self) -> None:
        settings = replace(
            SETTINGS,
            supabase_url="https://project.supabase.co",
            supabase_service_role_key="service-secret",
            evidence_supabase_bucket="smart-cricket-evidence",
        )
        with patch("backend.api.evidence.SETTINGS", settings), patch(
            "backend.api.evidence.urllib.request.urlopen",
        ) as urlopen:
            outcome = SupabaseEvidenceProvider().delete("user/../object.webm")

        self.assertEqual(outcome.status, "failed")
        self.assertEqual(outcome.error_code, "invalid_evidence_path")
        urlopen.assert_not_called()

    def test_supabase_reviewer_access_reports_http_failure(self) -> None:
        settings = replace(
            SETTINGS,
            supabase_url="https://project.supabase.co",
            supabase_service_role_key="service-secret",
            evidence_supabase_bucket="smart-cricket-evidence",
        )
        error = urllib.error.HTTPError(
            "https://project.supabase.co/storage/v1/object/sign/bucket/object",
            403,
            "Forbidden",
            {},
            BytesIO(b"forbidden"),
        )
        with patch("backend.api.evidence.SETTINGS", settings), patch(
            "backend.api.evidence.urllib.request.urlopen",
            side_effect=error,
        ):
            outcome = SupabaseEvidenceProvider().reviewer_access_url("user/session/object.webm")

        self.assertEqual(outcome.status, "temporary_failure")
        self.assertEqual(outcome.error_code, "supabase_storage_http_403")

    def test_unknown_evidence_provider_is_not_deleted_by_current_config(self) -> None:
        record = {
            "storage_status": "stored",
            "evidence_object_path": "user/session/object.webm",
            "evidence_metadata": {"storage_provider": "legacy_bucket"},
        }
        outcome = delete_evidence_for_record(record)
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(outcome.error_code, "unknown_evidence_provider")

    def test_already_deleted_record_is_idempotent(self) -> None:
        record = {
            "storage_status": "deleted",
            "deleted_at": "2026-08-12T00:00:00Z",
            "evidence_object_path": "user/session/object.webm",
            "evidence_metadata": {"storage_provider": "local_development"},
        }
        outcome = delete_evidence_for_record(record)
        self.assertEqual(outcome.status, "already_deleted")

    def test_withdrawal_marks_deletion_pending_when_physical_delete_fails(self) -> None:
        app.dependency_overrides[enforce_auth] = lambda: AuthContext(
            user_id="00000000-0000-0000-0000-000000000001",
            authorization_present=True,
        )
        client = TestClient(app)
        analysis = {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "storage_status": "stored",
            "evidence_object_path": "user/session/object.webm",
            "evidence_metadata": {"storage_provider": "legacy_bucket"},
        }
        with patch(
            "backend.api.routes.load_analysis_session",
            return_value=PersistenceResult(stored=True, status="stored", record_id=analysis["id"], record=analysis),
        ), patch(
            "backend.api.routes.mark_analysis_withdrawn_or_deleted",
            return_value=PersistenceResult(stored=True, status="stored", record_id=analysis["id"]),
        ) as mark_analysis, patch(
            "backend.api.routes.mark_feedback_withdrawn_or_deleted",
            return_value=PersistenceResult(stored=False, status="not_found", error_code="record_not_found"),
        ):
            response = client.post(f"/analysis/{analysis['id']}/withdraw-consent")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "withdrawn_deletion_pending")
        self.assertFalse(response.json()["evidence_deleted"])
        self.assertTrue(mark_analysis.call_args.kwargs["deletion_pending"])


if __name__ == "__main__":
    unittest.main()
