"""Validate Phase 13 API integration and write API artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app  # noqa: E402
from backend.api.services import PHASE13_VERSION  # noqa: E402


PHASE13_DIR = PROJECT_ROOT / "ml" / "artifacts" / "phase13"
SAMPLE_API_RESPONSE_PATH = PHASE13_DIR / "sample_api_response.json"
API_HEALTH_PATH = PHASE13_DIR / "api_health.json"
API_REPORT_PATH = PHASE13_DIR / "api_validation_report.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def _validate_response(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "predicted_shot",
        "shot_confidence",
        "technique_match_score",
        "coaching_tips",
        "detailed_feedback",
        "spoken_feedback",
        "debug_metadata",
        "api_metadata",
    }
    missing = required.difference(payload)
    if missing:
        errors.append(f"Missing response keys: {sorted(missing)}")
    if not 0.0 <= float(payload.get("shot_confidence", -1.0)) <= 1.0:
        errors.append("shot_confidence must be in [0,1].")
    if not 0.0 <= float(payload.get("technique_match_score", -1.0)) <= 100.0:
        errors.append("technique_match_score must be in [0,100].")
    if not str(payload.get("spoken_feedback", "")).strip():
        errors.append("spoken_feedback must be non-empty.")
    return errors


def _write_report(health: dict[str, Any], sample: dict[str, Any]) -> None:
    with API_REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Phase 13 API Integration Report\n\n")
        f.write("## Validation Status\n\n")
        f.write(f"- Validation passed: `{health['validation_passed']}`\n")
        f.write(f"- Health endpoint passed: `{health['health_endpoint_passed']}`\n")
        f.write(f"- Analyze endpoint passed: `{health['analyze_endpoint_passed']}`\n")
        f.write(f"- Error handling passed: `{health['error_handling_passed']}`\n\n")
        f.write("## Sample API Response\n\n")
        f.write(f"- Predicted shot: `{sample['predicted_shot']}`\n")
        f.write(f"- Shot confidence: `{sample['shot_confidence']:.4f}`\n")
        f.write(f"- Technique match score: `{sample['technique_match_score']:.4f}`\n")
        f.write(f"- Coaching tips: `{len(sample['coaching_tips'])}`\n")
        f.write(f"- Spoken feedback: {sample['spoken_feedback']}\n\n")
        f.write("## Engineering Notes\n\n")
        f.write(
            "- The API layer calls the Phase 12 pipeline and does not duplicate ML logic.\n"
            "- Phase 13 v1 validates upload transport using known finalized dataset video filenames.\n"
            "- Arbitrary raw-video preprocessing is intentionally left for later hardening.\n"
        )


def generate_phase13_artifacts() -> dict[str, Any]:
    client = TestClient(app)
    health_response = client.get("/health")
    health_payload = health_response.json()

    analyze_response = client.post(
        "/analyze",
        files={"file": ("cover_drive_average_02.mov", b"phase13-test-video-bytes", "video/quicktime")},
    )
    sample_payload = analyze_response.json()

    bad_response = client.post(
        "/analyze",
        files={"file": ("unknown_video.mov", b"phase13-test-video-bytes", "video/quicktime")},
    )

    errors = []
    errors.extend(_validate_response(sample_payload) if analyze_response.status_code == 200 else [str(sample_payload)])
    health_passed = health_response.status_code == 200 and health_payload.get("status") == "ok"
    analyze_passed = analyze_response.status_code == 200 and not errors
    error_passed = bad_response.status_code == 422

    _write_json(SAMPLE_API_RESPONSE_PATH, sample_payload)
    health = {
        "phase": "Phase 13",
        "version": PHASE13_VERSION,
        "created_at": _utc_now(),
        "health_endpoint_passed": health_passed,
        "analyze_endpoint_passed": analyze_passed,
        "error_handling_passed": error_passed,
        "sample_status_code": analyze_response.status_code,
        "error_status_code": bad_response.status_code,
        "validation_errors": errors,
        "validation_passed": bool(health_passed and analyze_passed and error_passed and not errors),
        "output_files": {
            "sample_api_response": str(SAMPLE_API_RESPONSE_PATH),
            "api_health": str(API_HEALTH_PATH),
            "api_validation_report": str(API_REPORT_PATH),
        },
    }
    _write_json(API_HEALTH_PATH, health)
    _write_report(health, sample_payload)
    return health


def main() -> int:
    health = generate_phase13_artifacts()
    if not health["validation_passed"]:
        print("FAIL: Phase 13 API validation failed.")
        for error in health["validation_errors"]:
            print(f"- {error}")
        return 1
    print("PASS: Phase 13 API integration artifacts are valid.")
    print(f"Sample API response: {health['output_files']['sample_api_response']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
