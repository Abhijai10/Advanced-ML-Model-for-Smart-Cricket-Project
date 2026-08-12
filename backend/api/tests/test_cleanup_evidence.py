"""Tests for the retained-evidence cleanup operator script."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.api.evidence import EvidenceOutcome
from backend.api.persistence import PersistenceResult
from scripts.cleanup_evidence import cleanup_expired_evidence


class EvidenceCleanupScriptTests(unittest.TestCase):
    def test_dry_run_lists_candidates_without_deleting(self) -> None:
        candidate = {"id": "analysis-1", "user_id": "user-1", "evidence_object_path": "user/analysis/object.webm"}
        with patch(
            "scripts.cleanup_evidence.list_evidence_cleanup_candidates",
            return_value=PersistenceResult(stored=True, status="stored", record=[candidate]),
        ), patch("scripts.cleanup_evidence.delete_evidence_for_record") as delete_mock:
            result = cleanup_expired_evidence(dry_run=True, limit=10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["results"][0]["status"], "dry_run")
        delete_mock.assert_not_called()

    def test_execute_deletes_and_disables_feedback_eligibility(self) -> None:
        candidate = {
            "id": "analysis-1",
            "user_id": "user-1",
            "evidence_object_path": "user/analysis/object.webm",
            "evidence_metadata": {"storage_provider": "local_development"},
        }
        with patch(
            "scripts.cleanup_evidence.list_evidence_cleanup_candidates",
            return_value=PersistenceResult(stored=True, status="stored", record=[candidate]),
        ), patch(
            "scripts.cleanup_evidence.delete_evidence_for_record",
            return_value=EvidenceOutcome(False, "deleted", "local_development", "user/analysis/object.webm"),
        ), patch(
            "scripts.cleanup_evidence.mark_analysis_withdrawn_or_deleted",
            return_value=PersistenceResult(stored=True, status="stored", record_id="analysis-1"),
        ) as mark_analysis, patch(
            "scripts.cleanup_evidence.mark_feedback_withdrawn_or_deleted",
            return_value=PersistenceResult(stored=True, status="stored", record_id="feedback-1"),
        ) as mark_feedback:
            result = cleanup_expired_evidence(dry_run=False, limit=10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["results"][0]["storage_status"], "deleted")
        self.assertTrue(mark_analysis.call_args.kwargs["deleted"])
        self.assertTrue(mark_feedback.call_args.kwargs["deleted"])


if __name__ == "__main__":
    unittest.main()
