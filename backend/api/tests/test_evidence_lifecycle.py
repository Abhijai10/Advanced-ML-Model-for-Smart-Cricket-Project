"""Regression tests for evidence lifecycle and provider-aware deletion."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.config import SETTINGS
from backend.api.evidence import EvidenceOutcome, delete_evidence_for_record
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
