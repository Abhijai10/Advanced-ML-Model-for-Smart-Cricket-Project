"""Validate Phase 12 offline inference outputs and write health artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from inference.analysis_pipeline import analyze_sequence, load_dataset_sequence  # noqa: E402
from inference.inference_config import (  # noqa: E402
    DEFAULT_SAMPLE_INDEX,
    INFERENCE_HEALTH_PATH,
    INFERENCE_REPORT_PATH,
    PHASE12_VERSION,
    SAMPLE_OUTPUT_PATH,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def _validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "predicted_shot",
        "shot_confidence",
        "technique_match_score",
        "detected_issues",
        "coaching_tips",
        "detailed_feedback",
        "spoken_feedback",
        "debug_metadata",
    }
    missing = required.difference(payload)
    if missing:
        errors.append(f"Missing required output keys: {sorted(missing)}")
    if not 0.0 <= float(payload.get("shot_confidence", -1.0)) <= 1.0:
        errors.append("shot_confidence must be in [0,1].")
    if not 0.0 <= float(payload.get("technique_match_score", -1.0)) <= 100.0:
        errors.append("technique_match_score must be in [0,100].")
    if not str(payload.get("spoken_feedback", "")).strip():
        errors.append("spoken_feedback must be non-empty.")
    if not isinstance(payload.get("debug_metadata"), dict) or not payload["debug_metadata"]:
        errors.append("debug_metadata must be a non-empty object.")
    return errors


def _write_report(health: dict[str, Any], payload: dict[str, Any]) -> None:
    with INFERENCE_REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Phase 12 Offline Inference Report\n\n")
        f.write("## Validation Status\n\n")
        f.write(f"- Validation passed: `{health['validation_passed']}`\n")
        f.write(f"- Sample index: `{health['sample_index']}`\n")
        f.write(f"- Output schema stable: `{health['output_schema_stable']}`\n")
        f.write(f"- Segmentation completed: `{payload['segmentation']['completed']}`\n\n")
        f.write("## Sample Result\n\n")
        f.write(f"- Predicted shot: `{payload['predicted_shot']}`\n")
        f.write(f"- Shot confidence: `{payload['shot_confidence']:.4f}`\n")
        f.write(f"- Technique match score: `{payload['technique_match_score']:.4f}`\n")
        f.write(f"- Detected issues: `{len(payload['detected_issues'])}`\n")
        f.write(f"- Spoken feedback: {payload['spoken_feedback']}\n\n")
        f.write("## Engineering Notes\n\n")
        f.write(
            "- Phase 12 v1 orchestrates validated temporal sequences rather than API uploads.\n"
            "- Phase 13 should call this pipeline instead of duplicating ML logic.\n"
            "- Raw video upload handling, API transport, and voice output remain later roadmap phases.\n"
        )


def generate_phase12_artifacts(sample_index: int = DEFAULT_SAMPLE_INDEX) -> dict[str, Any]:
    sequence, metadata = load_dataset_sequence(sample_index=sample_index)
    result = analyze_sequence(sequence, metadata)
    payload = result.to_dict()
    errors = _validate_payload(payload)
    _write_json(SAMPLE_OUTPUT_PATH, payload)
    health = {
        "phase": "Phase 12",
        "version": PHASE12_VERSION,
        "created_at": _utc_now(),
        "sample_index": sample_index,
        "input_mode": "final_temporal_dataset_sequence",
        "output_schema_stable": not errors,
        "validation_errors": errors,
        "validation_passed": not errors,
        "output_files": {
            "sample_output": str(SAMPLE_OUTPUT_PATH),
            "inference_health": str(INFERENCE_HEALTH_PATH),
            "inference_report": str(INFERENCE_REPORT_PATH),
        },
    }
    _write_json(INFERENCE_HEALTH_PATH, health)
    _write_report(health, payload)
    return health


def main() -> int:
    health = generate_phase12_artifacts()
    if not health["validation_passed"]:
        print("FAIL: Phase 12 offline inference validation failed.")
        for error in health["validation_errors"]:
            print(f"- {error}")
        return 1
    print("PASS: Phase 12 offline inference artifacts are valid.")
    print(f"Sample index: {health['sample_index']}")
    print(f"Sample output path: {health['output_files']['sample_output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
