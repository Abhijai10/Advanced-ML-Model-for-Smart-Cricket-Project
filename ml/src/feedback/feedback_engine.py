"""Generate human-readable coaching feedback from Phase 10 scoring outputs."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from feedback.feedback_rules import fallback_tip_from_weakest_component, select_detected_issues  # noqa: E402
from feedback.feedback_schema import FeedbackOutput  # noqa: E402
from feedback.feedback_templates import COMPONENT_LABELS, score_band_label  # noqa: E402


ML_ROOT = Path(__file__).resolve().parents[2]
PHASE10_REPORT_PATH = ML_ROOT / "artifacts" / "phase10" / "technique_score_report.json"
PHASE11_DIR = ML_ROOT / "artifacts" / "phase11"
SAMPLE_OUTPUTS_PATH = PHASE11_DIR / "sample_feedback_outputs.json"
FEEDBACK_CSV_PATH = PHASE11_DIR / "feedback_outputs.csv"
FEEDBACK_REPORT_PATH = PHASE11_DIR / "feedback_report.md"
FEEDBACK_HEALTH_PATH = PHASE11_DIR / "feedback_health.json"
PHASE11_VERSION = "phase_11_feedback_engine_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def _validate_phase10_report(report: dict[str, Any]) -> None:
    if report.get("phase") != "Phase 10":
        raise ValueError("Feedback engine expects a Phase 10 technique score report.")
    samples = report.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Phase 10 report must contain non-empty samples.")
    for sample in samples:
        score_result = sample.get("score_result")
        if not isinstance(score_result, dict):
            raise ValueError("Every sample must contain score_result.")
        if "component_scores" not in score_result:
            raise ValueError("Every score_result must contain component_scores.")
        score = float(score_result.get("technique_match_score", -1.0))
        if not 0.0 <= score <= 100.0:
            raise ValueError(f"Technique score outside 0-100: {score}")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, np.bool_):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value!r}")


def _top_component_names(component_scores: dict[str, Any], limit: int = 2) -> list[str]:
    ordered = sorted(component_scores.items(), key=lambda item: float(item[1]["score"]), reverse=True)
    return [COMPONENT_LABELS.get(name, name.replace("_score", "").replace("_", " ")) for name, _ in ordered[:limit]]


def _weak_component_names(component_scores: dict[str, Any], limit: int = 2) -> list[str]:
    ordered = sorted(component_scores.items(), key=lambda item: float(item[1]["score"]))
    return [COMPONENT_LABELS.get(name, name.replace("_score", "").replace("_", " ")) for name, _ in ordered[:limit]]


def _build_detailed_feedback(
    *,
    predicted_shot: str,
    technique_score: float,
    component_scores: dict[str, Any],
    tips: tuple[str, ...],
) -> str:
    band = score_band_label(technique_score)
    strong = ", ".join(_top_component_names(component_scores))
    weak = ", ".join(_weak_component_names(component_scores))
    return (
        f"Your {predicted_shot.replace('_', ' ')} technique match score is {technique_score:.1f}/100, "
        f"which is currently in the {band} band. Stronger measured areas include {strong}. "
        f"The main areas to work on are {weak}. "
        f"Primary coaching focus: {tips[0]}"
    )


def _build_spoken_feedback(predicted_shot: str, technique_score: float, tips: tuple[str, ...]) -> str:
    shot = predicted_shot.replace("_", " ")
    return (
        f"{shot} scored {technique_score:.0f} out of 100. "
        f"{tips[0]} "
        "Focus on one adjustment at a time and repeat the movement with control."
    )


def generate_feedback_for_sample(sample: dict[str, Any]) -> FeedbackOutput:
    """Generate complete coaching feedback for one Phase 10 scored sample."""
    score_result = sample["score_result"]
    component_scores = score_result["component_scores"]
    technique_score = float(score_result["technique_match_score"])
    issues = select_detected_issues(component_scores)
    if issues:
        tips = tuple(issue.coaching_tip for issue in issues)
    else:
        tips = (
            fallback_tip_from_weakest_component(component_scores, technique_score),
            "Keep the movement smooth and repeatable.",
        )
    predicted_shot = str(score_result["predicted_shot"])
    debug_metadata = {
        "feedback_version": PHASE11_VERSION,
        "source_phase": "Phase 10",
        "issue_rule_threshold": 75.0,
        "num_component_scores": len(component_scores),
        "num_detected_issues": len(issues),
        "score_band": score_band_label(technique_score),
        "prediction_correct": _as_bool(sample.get("prediction_correct")),
        "note": "Feedback is generated from measurable template deviations and should not be treated as a certified coaching diagnosis.",
    }
    return FeedbackOutput(
        file_name=str(sample["file_name"]),
        predicted_shot=predicted_shot,
        true_label_name=str(sample["true_label_name"]),
        technique_match_score=technique_score,
        classifier_confidence=score_result.get("classifier_confidence"),
        detected_issues=issues,
        coaching_tips=tips,
        detailed_feedback=_build_detailed_feedback(
            predicted_shot=predicted_shot,
            technique_score=technique_score,
            component_scores=component_scores,
            tips=tips,
        ),
        spoken_feedback=_build_spoken_feedback(predicted_shot, technique_score, tips),
        debug_metadata=debug_metadata,
    )


def _validate_feedback_outputs(outputs: list[FeedbackOutput]) -> None:
    if not outputs:
        raise ValueError("No feedback outputs generated.")
    for output in outputs:
        if not output.spoken_feedback.strip():
            raise ValueError(f"Missing spoken feedback for {output.file_name}.")
        if not output.detailed_feedback.strip():
            raise ValueError(f"Missing detailed feedback for {output.file_name}.")
        if not output.coaching_tips:
            raise ValueError(f"Missing coaching tips for {output.file_name}.")
        if not 0.0 <= output.technique_match_score <= 100.0:
            raise ValueError(f"Invalid score for {output.file_name}.")
        for issue in output.detected_issues:
            if not issue.feature_name or not issue.coaching_tip:
                raise ValueError(f"Invalid issue generated for {output.file_name}.")


def _write_feedback_csv(outputs: list[FeedbackOutput]) -> None:
    rows = []
    for output in outputs:
        rows.append(
            {
                "file_name": output.file_name,
                "predicted_shot": output.predicted_shot,
                "true_label_name": output.true_label_name,
                "technique_match_score": output.technique_match_score,
                "classifier_confidence": output.classifier_confidence,
                "num_detected_issues": len(output.detected_issues),
                "primary_tip": output.coaching_tips[0],
                "spoken_feedback": output.spoken_feedback,
            }
        )
    FEEDBACK_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown_report(outputs: list[FeedbackOutput], health: dict[str, Any]) -> None:
    scores = np.asarray([output.technique_match_score for output in outputs], dtype=np.float64)
    with FEEDBACK_REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Phase 11 Feedback Engine Report\n\n")
        f.write("## Validation Status\n\n")
        f.write(f"- Validation passed: `{health['validation_passed']}`\n")
        f.write(f"- Samples processed: `{health['samples_processed']}`\n")
        f.write(f"- Spoken feedback present: `{health['spoken_feedback_present']}`\n")
        f.write(f"- Issues linked to features: `{health['issues_linked_to_features']}`\n\n")
        f.write("## Feedback Summary\n\n")
        f.write(f"- Mean source technique score: `{scores.mean():.4f}`\n")
        f.write(f"- Minimum source technique score: `{scores.min():.4f}`\n")
        f.write(f"- Maximum source technique score: `{scores.max():.4f}`\n")
        f.write(f"- Total detected issues: `{sum(len(output.detected_issues) for output in outputs)}`\n\n")
        f.write("## Sample Spoken Feedback\n\n")
        for output in outputs[:5]:
            f.write(f"- `{output.file_name}`: {output.spoken_feedback}\n")
        f.write("\n## Interpretation Notes\n\n")
        f.write(
            "- Feedback is generated from Phase 10 measurable deviations and component scores.\n"
            "- The engine avoids saying a shot is simply bad; it explains what to improve and why.\n"
            "- Spoken feedback is short enough for future TTS, while detailed feedback is better for reports or UI.\n"
        )


def generate_phase11_artifacts() -> dict[str, Any]:
    """Generate feedback outputs and validation health from Phase 10 report."""
    PHASE11_DIR.mkdir(parents=True, exist_ok=True)
    report = _load_json(PHASE10_REPORT_PATH)
    _validate_phase10_report(report)
    outputs = [generate_feedback_for_sample(sample) for sample in report["samples"]]
    _validate_feedback_outputs(outputs)

    sample_payload = {
        "phase": "Phase 11",
        "version": PHASE11_VERSION,
        "created_at": _utc_now(),
        "input_report": str(PHASE10_REPORT_PATH),
        "feedback_philosophy": [
            "Feedback is linked to measurable component scores and feature deviations.",
            "Detailed feedback explains what went wrong, why it matters, and how to improve.",
            "Spoken feedback is concise and TTS-friendly for future Phase 14 voice output.",
        ],
        "outputs": [output.to_dict() for output in outputs],
    }
    _write_json(SAMPLE_OUTPUTS_PATH, sample_payload)
    _write_feedback_csv(outputs)

    issues = [issue for output in outputs for issue in output.detected_issues]
    health = {
        "phase": "Phase 11",
        "version": PHASE11_VERSION,
        "created_at": _utc_now(),
        "samples_processed": len(outputs),
        "detected_issue_count": len(issues),
        "samples_with_spoken_feedback": sum(1 for output in outputs if output.spoken_feedback.strip()),
        "spoken_feedback_present": all(output.spoken_feedback.strip() for output in outputs),
        "detailed_feedback_present": all(output.detailed_feedback.strip() for output in outputs),
        "tips_present": all(output.coaching_tips for output in outputs),
        "issues_linked_to_features": all(issue.feature_name for issue in issues),
        "debug_metadata_present": all(output.debug_metadata for output in outputs),
        "validation_passed": True,
        "output_files": {
            "sample_feedback_outputs": str(SAMPLE_OUTPUTS_PATH),
            "feedback_outputs_csv": str(FEEDBACK_CSV_PATH),
            "feedback_report": str(FEEDBACK_REPORT_PATH),
            "feedback_health": str(FEEDBACK_HEALTH_PATH),
        },
    }
    health["validation_passed"] = bool(
        health["samples_processed"] == 12
        and health["spoken_feedback_present"]
        and health["detailed_feedback_present"]
        and health["tips_present"]
        and health["issues_linked_to_features"]
        and health["debug_metadata_present"]
    )
    _write_json(FEEDBACK_HEALTH_PATH, health)
    _write_markdown_report(outputs, health)
    return health


def main() -> int:
    health = generate_phase11_artifacts()
    print("Phase 11 Feedback Engine")
    print(f"samples processed: {health['samples_processed']}")
    print(f"detected issues: {health['detected_issue_count']}")
    print(f"spoken feedback present: {health['spoken_feedback_present']}")
    print(f"validation passed: {health['validation_passed']}")
    print(f"sample output path: {SAMPLE_OUTPUTS_PATH}")
    return 0 if health["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
