#!/usr/bin/env python3
"""Delete expired retained Smart Cricket evidence using stored provider metadata."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.evidence import delete_evidence_for_record  # noqa: E402
from backend.api.persistence import (  # noqa: E402
    list_evidence_cleanup_candidates,
    mark_analysis_withdrawn_or_deleted,
    mark_feedback_withdrawn_or_deleted,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def cleanup_expired_evidence(*, dry_run: bool, limit: int) -> dict:
    listed = list_evidence_cleanup_candidates(now_iso=_iso_now(), limit=limit)
    if not listed.stored:
        return {"ok": False, "status": listed.status, "error_code": listed.error_code, "dry_run": dry_run}
    records = listed.record if isinstance(listed.record, list) else []
    results = []
    for record in records:
        analysis_id = str(record.get("id") or "")
        user_id = str(record.get("user_id") or "")
        if not analysis_id or not user_id:
            results.append({"analysis_session_id": analysis_id, "status": "skipped", "error_code": "missing_identity"})
            continue
        if dry_run:
            results.append({"analysis_session_id": analysis_id, "status": "dry_run"})
            continue
        outcome = delete_evidence_for_record(record)
        deleted = outcome.status in {"deleted", "already_deleted", "not_found"}
        analysis_update = mark_analysis_withdrawn_or_deleted(
            analysis_session_id=analysis_id,
            user_id=user_id,
            deleted=deleted,
            deletion_pending=not deleted,
            deletion_error_code=None if deleted else outcome.error_code or outcome.status,
            evidence_metadata=record.get("evidence_metadata") if isinstance(record.get("evidence_metadata"), dict) else None,
        )
        feedback_update = mark_feedback_withdrawn_or_deleted(
            analysis_session_id=analysis_id,
            user_id=user_id,
            deleted=deleted,
            deletion_pending=not deleted,
        )
        results.append(
            {
                "analysis_session_id": analysis_id,
                "delete_status": outcome.status,
                "storage_status": "deleted" if deleted else "deletion_pending",
                "analysis_update": analysis_update.status,
                "feedback_update": feedback_update.status,
                "error_code": outcome.error_code,
            }
        )
    return {"ok": True, "dry_run": dry_run, "candidate_count": len(records), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Actually delete evidence and mark database rows.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of cleanup candidates to process.")
    args = parser.parse_args()
    result = cleanup_expired_evidence(dry_run=not args.execute, limit=args.limit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
