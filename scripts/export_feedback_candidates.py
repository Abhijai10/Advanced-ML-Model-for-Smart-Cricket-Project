"""Export adjudicated feedback candidates for human review manifests.

This script intentionally excludes raw feedback rows that are metadata-only,
unreviewed, expired, withdrawn, deleted, or missing protected evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


def fetch_candidates(limit: int) -> list[dict[str, Any]]:
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for candidate export.")

    query = urllib.parse.urlencode(
        {
            "select": "*",
            "accepted_for_review": "eq.true",
            "consent_to_model_improvement": "eq.true",
            "review_status": "eq.approved",
            "dataset_eligibility_status": "eq.eligible",
            "storage_status": "eq.stored",
            "withdrawn_at": "is.null",
            "deleted_at": "is.null",
            "order": "created_at.asc",
            "limit": str(limit),
        }
    )
    request = urllib.request.Request(
        f"{supabase_url.rstrip('/')}/rest/v1/analysis_feedback?{query}",
        headers={
            "apikey": service_key,
            "authorization": f"Bearer {service_key}",
            "accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("Unexpected Supabase response shape.")
    return payload


def filter_reviewable(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    reviewable: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("accepted_for_review") or not row.get("evidence_object_path"):
            continue
        if not row.get("reviewer_id") or not row.get("reviewer_label"):
            continue
        expires_at = row.get("retention_expires_at")
        if isinstance(expires_at, str):
            try:
                if datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= now:
                    continue
            except ValueError:
                continue
        reviewable.append(row)
    return reviewable


def write_csv(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "user_id",
        "analysis_session_id",
        "clip_hash",
        "predicted_shot",
        "prediction_was_correct",
        "corrected_shot",
        "technique_feedback_rating",
        "tip_flags",
        "model_version",
        "pipeline_version",
        "feature_contract_version",
        "checkpoint_sha256",
        "consent_version",
        "consented_at",
        "storage_status",
        "evidence_object_path",
        "dataset_eligibility_status",
        "reviewer_id",
        "reviewer_label",
        "second_review_required",
        "disagreement_notes",
        "rejection_reason",
        "unsafe_content_flag",
        "split_assignment",
        "training_inclusion_version",
        "provenance_completeness_score",
        "label_quality_score",
        "request_id",
        "created_at",
        "notes",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: json.dumps(row.get(field)) if isinstance(row.get(field), (dict, list)) else row.get(field) for field in fields})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output", type=Path, default=Path("exports/feedback_candidates.csv"))
    args = parser.parse_args()
    rows = filter_reviewable(fetch_candidates(args.limit))
    write_csv(rows, args.output)
    print(f"Exported {len(rows)} feedback candidate(s) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
