#!/usr/bin/env python3
"""Reviewer/admin helper for Smart Cricket feedback candidates."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.evidence import evidence_is_reviewable, get_evidence_provider_by_id, provider_id_for_record  # noqa: E402
from backend.api.persistence import list_feedback_review_candidates, record_feedback_review_decision  # noqa: E402


SUPPORTED_LABELS = {"cover_drive", "defensive_shot", "pull_shot", "sweep_shot"}
SPLITS = {"train", "validation", "test", "holdout"}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _candidate_view(row: dict[str, Any], *, include_access: bool, ttl_seconds: int) -> dict[str, Any]:
    view = {
        "feedback_id": row.get("id"),
        "analysis_session_id": row.get("analysis_session_id"),
        "user_id": row.get("user_id"),
        "clip_hash": row.get("clip_hash"),
        "predicted_shot": row.get("predicted_shot"),
        "prediction_was_correct": row.get("prediction_was_correct"),
        "corrected_shot": row.get("corrected_shot"),
        "technique_feedback_rating": row.get("technique_feedback_rating"),
        "tip_flags": row.get("tip_flags") or [],
        "notes": row.get("notes"),
        "model_version": row.get("model_version"),
        "pipeline_version": row.get("pipeline_version"),
        "feature_contract_version": row.get("feature_contract_version"),
        "storage_provider": provider_id_for_record(row),
        "retention_expires_at": row.get("retention_expires_at"),
        "created_at": row.get("created_at"),
        "reviewable_evidence": evidence_is_reviewable(row),
    }
    if include_access and view["reviewable_evidence"]:
        provider = get_evidence_provider_by_id(view["storage_provider"])
        outcome = provider.reviewer_access_url(str(row.get("evidence_object_path")), ttl_seconds=ttl_seconds)
        view["evidence_access"] = {
            "status": outcome.status,
            "provider": outcome.provider,
            "metadata": outcome.metadata or {},
            "error_code": outcome.error_code,
        }
    return view


def list_candidates(*, limit: int, include_access: bool, ttl_seconds: int) -> dict[str, Any]:
    result = list_feedback_review_candidates(now_iso=_iso_now(), limit=limit)
    if not result.stored:
        return {"ok": False, "status": result.status, "error_code": result.error_code}
    rows = result.record if isinstance(result.record, list) else []
    candidates = [
        _candidate_view(row, include_access=include_access, ttl_seconds=ttl_seconds)
        for row in rows
        if evidence_is_reviewable(row)
    ]
    return {"ok": True, "candidate_count": len(candidates), "candidates": candidates}


def record_decision(
    *,
    feedback_id: str,
    reviewer_id: str,
    decision: str,
    reviewer_label: str | None,
    label_quality_score: float | None,
    second_review_required: bool,
    disagreement_notes: str | None,
    rejection_reason: str | None,
    unsafe_content_flag: bool,
    split_assignment: str | None,
    training_inclusion_version: str | None,
) -> dict[str, Any]:
    approved = decision == "approve"
    if decision not in {"approve", "reject"}:
        raise ValueError("decision must be approve or reject")
    if approved and reviewer_label not in SUPPORTED_LABELS:
        raise ValueError("approved feedback requires a supported reviewer label")
    if label_quality_score is not None and not 0 <= label_quality_score <= 1:
        raise ValueError("label quality score must be between 0 and 1")
    if split_assignment is not None and split_assignment not in SPLITS:
        raise ValueError("split assignment must be train, validation, test, or holdout")
    if unsafe_content_flag and approved:
        raise ValueError("unsafe feedback cannot be approved for dataset eligibility")
    if not approved and not rejection_reason:
        raise ValueError("rejected feedback requires a rejection reason")
    outcome = record_feedback_review_decision(
        feedback_id=feedback_id,
        reviewer_id=reviewer_id,
        reviewer_label=reviewer_label,
        label_quality_score=label_quality_score,
        second_review_required=second_review_required,
        disagreement_notes=disagreement_notes,
        rejection_reason=rejection_reason,
        unsafe_content_flag=unsafe_content_flag,
        split_assignment=split_assignment,
        training_inclusion_version=training_inclusion_version,
        approved=approved,
    )
    return {
        "ok": outcome.stored,
        "status": outcome.status,
        "feedback_id": feedback_id,
        "record_id": outcome.record_id,
        "error_code": outcome.error_code,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List pending review candidates.")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.add_argument("--include-access", action="store_true", help="Include short-lived reviewer evidence access.")
    list_parser.add_argument("--ttl-seconds", type=int, default=300)

    decision_parser = subparsers.add_parser("decision", help="Record a reviewer decision.")
    decision_parser.add_argument("--feedback-id", required=True)
    decision_parser.add_argument("--reviewer-id", required=True)
    decision_parser.add_argument("--decision", required=True, choices=["approve", "reject"])
    decision_parser.add_argument("--reviewer-label")
    decision_parser.add_argument("--label-quality-score", type=float)
    decision_parser.add_argument("--second-review-required", action="store_true")
    decision_parser.add_argument("--disagreement-notes")
    decision_parser.add_argument("--rejection-reason")
    decision_parser.add_argument("--unsafe-content-flag", action="store_true")
    decision_parser.add_argument("--split-assignment", choices=sorted(SPLITS))
    decision_parser.add_argument("--training-inclusion-version")

    args = parser.parse_args()
    try:
        if args.command == "list":
            result = list_candidates(limit=args.limit, include_access=args.include_access, ttl_seconds=args.ttl_seconds)
        else:
            result = record_decision(
                feedback_id=args.feedback_id,
                reviewer_id=args.reviewer_id,
                decision=args.decision,
                reviewer_label=args.reviewer_label,
                label_quality_score=args.label_quality_score,
                second_review_required=args.second_review_required,
                disagreement_notes=args.disagreement_notes,
                rejection_reason=args.rejection_reason,
                unsafe_content_flag=args.unsafe_content_flag,
                split_assignment=args.split_assignment,
                training_inclusion_version=args.training_inclusion_version,
            )
    except ValueError as exc:
        result = {"ok": False, "status": "invalid_request", "error": str(exc)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
