"""Tests for reviewer/admin feedback candidate workflow."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from backend.api.evidence import EvidenceOutcome
from backend.api.persistence import PersistenceResult
from scripts.review_feedback_candidates import list_candidates, record_decision


def _candidate(**overrides):
    row = {
        "id": "feedback-1",
        "user_id": "user-1",
        "analysis_session_id": "analysis-1",
        "clip_hash": "a" * 64,
        "predicted_shot": "cover_drive",
        "prediction_was_correct": "correct",
        "corrected_shot": None,
        "technique_feedback_rating": 5,
        "tip_flags": ["useful"],
        "notes": "Looks right.",
        "model_version": "phase8-best",
        "pipeline_version": "phase12",
        "feature_contract_version": "smart_cricket_temporal_features_v1",
        "storage_status": "stored",
        "evidence_object_path": "user/analysis/object.webm",
        "retention_expires_at": "2999-01-01T00:00:00Z",
        "evidence_metadata": {
            "storage_provider": "local_development",
            "user_id": "user-1",
            "analysis_session_id": "analysis-1",
            "checksum_sha256": "b" * 64,
        },
        "created_at": "2026-08-12T00:00:00Z",
    }
    row.update(overrides)
    return row


class ReviewFeedbackCandidatesTests(unittest.TestCase):
    def test_list_candidates_filters_unreviewable_rows(self) -> None:
        rows = [
            _candidate(id="reviewable"),
            _candidate(id="expired", retention_expires_at="2000-01-01T00:00:00Z"),
            _candidate(id="metadata-only", evidence_object_path=None),
        ]
        with patch(
            "scripts.review_feedback_candidates.list_feedback_review_candidates",
            return_value=PersistenceResult(stored=True, status="stored", record=rows),
        ):
            result = list_candidates(limit=10, include_access=False, ttl_seconds=300)
        self.assertTrue(result["ok"])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["feedback_id"], "reviewable")
        self.assertTrue(result["candidates"][0]["reviewable_evidence"])

    def test_list_candidates_can_include_short_lived_access(self) -> None:
        provider = Mock()
        provider.reviewer_access_url.return_value = EvidenceOutcome(
            True,
            "stored",
            "local_development",
            "user/analysis/object.webm",
            metadata={"local_path": "/tmp/evidence.webm", "ttl_seconds": 300},
        )
        with patch(
            "scripts.review_feedback_candidates.list_feedback_review_candidates",
            return_value=PersistenceResult(stored=True, status="stored", record=[_candidate()]),
        ), patch("scripts.review_feedback_candidates.get_evidence_provider_by_id", return_value=provider):
            result = list_candidates(limit=10, include_access=True, ttl_seconds=300)
        self.assertTrue(result["ok"])
        provider.reviewer_access_url.assert_called_once_with("user/analysis/object.webm", ttl_seconds=300)
        self.assertEqual(result["candidates"][0]["evidence_access"]["status"], "stored")

    def test_record_approved_decision(self) -> None:
        with patch(
            "scripts.review_feedback_candidates.record_feedback_review_decision",
            return_value=PersistenceResult(stored=True, status="stored", record_id="feedback-1"),
        ) as record:
            result = record_decision(
                feedback_id="feedback-1",
                reviewer_id="00000000-0000-0000-0000-000000000001",
                decision="approve",
                reviewer_label="cover_drive",
                label_quality_score=0.95,
                second_review_required=False,
                disagreement_notes=None,
                rejection_reason=None,
                unsafe_content_flag=False,
                split_assignment="train",
                training_inclusion_version="dataset-2026-08",
            )
        self.assertTrue(result["ok"])
        self.assertTrue(record.call_args.kwargs["approved"])
        self.assertEqual(record.call_args.kwargs["reviewer_label"], "cover_drive")

    def test_reject_requires_reason_and_unsafe_cannot_be_approved(self) -> None:
        with self.assertRaises(ValueError):
            record_decision(
                feedback_id="feedback-1",
                reviewer_id="reviewer",
                decision="reject",
                reviewer_label=None,
                label_quality_score=None,
                second_review_required=False,
                disagreement_notes=None,
                rejection_reason=None,
                unsafe_content_flag=False,
                split_assignment=None,
                training_inclusion_version=None,
            )
        with self.assertRaises(ValueError):
            record_decision(
                feedback_id="feedback-1",
                reviewer_id="reviewer",
                decision="approve",
                reviewer_label="cover_drive",
                label_quality_score=0.9,
                second_review_required=False,
                disagreement_notes=None,
                rejection_reason=None,
                unsafe_content_flag=True,
                split_assignment="train",
                training_inclusion_version="dataset-2026-08",
            )


if __name__ == "__main__":
    unittest.main()
