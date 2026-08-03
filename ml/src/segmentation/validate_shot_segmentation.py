"""Validate Phase 9 shot segmentation on finalized temporal sequences."""

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

from segmentation.shot_segmenter import ShotSegmenter  # noqa: E402


ML_ROOT = Path(__file__).resolve().parents[2]
FINAL_TEMPORAL_DIR = ML_ROOT / "data" / "final_temporal"
ARTIFACT_DIR = ML_ROOT / "artifacts" / "phase9"
X_SEQUENCE_PATH = FINAL_TEMPORAL_DIR / "X_sequence.npy"
FEATURE_SCHEMA_PATH = FINAL_TEMPORAL_DIR / "temporal_feature_schema.json"
INDEX_PATH = FINAL_TEMPORAL_DIR / "temporal_dataset_index.csv"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _load_index_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Cannot write empty CSV rows.")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def validate_inputs(X: np.ndarray, feature_columns: list[str], index_rows: list[dict[str, str]]) -> None:
    if X.ndim != 3:
        raise ValueError(f"X_sequence must be rank 3, got shape {X.shape}.")
    if X.shape != (80, 60, 32):
        raise ValueError(f"Expected X_sequence shape (80, 60, 32), got {X.shape}.")
    if len(feature_columns) != 32:
        raise ValueError(f"Expected 32 feature columns, got {len(feature_columns)}.")
    if len(index_rows) != X.shape[0]:
        raise ValueError(f"Index rows {len(index_rows)} != samples {X.shape[0]}.")
    if not np.isfinite(X).all():
        raise ValueError("X_sequence contains NaN or infinite values.")


def run_validation() -> dict[str, Any]:
    X = np.load(X_SEQUENCE_PATH)
    schema = _load_json(FEATURE_SCHEMA_PATH)
    feature_columns = [str(c) for c in schema.get("feature_columns", [])]
    index_rows = _load_index_rows(INDEX_PATH)
    validate_inputs(X, feature_columns, index_rows)

    segmenter = ShotSegmenter()
    summary_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []

    for sample_idx in range(X.shape[0]):
        result = segmenter.segment_sequence(X[sample_idx], feature_columns)
        segment = result.segment
        base = index_rows[sample_idx]
        row = {
            "sample_index": sample_idx,
            "row_index": int(base["row_index"]),
            "video_id": str(base["video_id"]),
            "file_name": str(base["file_name"]),
            "shot_label": str(base["shot_label"]),
            "segment_detected": segment is not None,
            "start_frame": segment.start_frame if segment else "",
            "end_frame": segment.end_frame if segment else "",
            "peak_frame": segment.peak_frame if segment else "",
            "prediction_trigger_frame": segment.prediction_trigger_frame if segment else "",
            "trigger_count": segment.trigger_count if segment else 0,
            "completion_reason": segment.completion_reason if segment else "not_detected",
            "max_energy": result.to_summary_dict()["max_energy"],
            "mean_energy": result.to_summary_dict()["mean_energy"],
        }
        summary_rows.append(row)
        for trace in result.state_trace:
            trace_rows.append(
                {
                    "sample_index": sample_idx,
                    "file_name": str(base["file_name"]),
                    **trace,
                }
            )

    detected = sum(1 for r in summary_rows if r["segment_detected"])
    one_trigger = sum(1 for r in summary_rows if r["trigger_count"] == 1)
    forced = sum(1 for r in summary_rows if r["completion_reason"] == "sequence_end_completion")
    validation_passed = detected == X.shape[0] and one_trigger == X.shape[0]

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(ARTIFACT_DIR / "segmentation_segments.csv", summary_rows)
    _write_csv(ARTIFACT_DIR / "segmentation_state_trace.csv", trace_rows)

    health = {
        "phase": "Phase 9 — Shot Segmentation",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_tensor": str(X_SEQUENCE_PATH),
        "input_shape": list(X.shape),
        "total_sequences": int(X.shape[0]),
        "segments_detected": int(detected),
        "single_trigger_sequences": int(one_trigger),
        "forced_sequence_end_completions": int(forced),
        "validation_passed": bool(validation_passed),
        "thresholds": {
            "start_threshold": 0.28,
            "active_threshold": 0.18,
            "end_threshold": 0.12,
            "smoothing_window": 5,
        },
        "notes": [
            "Phase 9 uses explainable motion-energy thresholds and a state machine.",
            "This phase does not retrain the Phase 8 classifier.",
            "sequence_end_completion is allowed because finalized clips already contain one labeled shot.",
        ],
    }
    _write_json(ARTIFACT_DIR / "segmentation_health.json", health)

    report = ARTIFACT_DIR / "segmentation_debug_report.md"
    with report.open("w", encoding="utf-8") as f:
        f.write("# Phase 9 Segmentation Debug Report\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Input tensor: `{X_SEQUENCE_PATH}`\n")
        f.write(f"- Shape: `{tuple(X.shape)}`\n")
        f.write(f"- Segments detected: `{detected}/{X.shape[0]}`\n")
        f.write(f"- Single-trigger sequences: `{one_trigger}/{X.shape[0]}`\n")
        f.write(f"- Sequence-end completions: `{forced}`\n")
        f.write(f"- Validation passed: `{validation_passed}`\n\n")
        f.write("## State Machine\n\n")
        f.write("`idle → preparation → backswing → swing → follow_through → completed → cooldown`\n\n")
        f.write("## Interpretation\n\n")
        f.write(
            "The current finalized dataset is already clipped to one batting shot per sequence. "
            "The segmenter therefore acts as the prediction gate that emits one final trigger "
            "after the observed motion has enough evidence to be treated as a completed shot.\n\n"
        )
        f.write("## Limitations\n\n")
        f.write("- This is threshold/state-machine segmentation, not a learned segmentation model.\n")
        f.write("- Live-camera timing will need separate latency and buffering validation in later phases.\n")
        f.write("- Sequence-end completion is acceptable for finalized clips, but live streams should prefer explicit stabilization.\n\n")
        f.write("## Outputs\n\n")
        f.write("- `segmentation_segments.csv`\n")
        f.write("- `segmentation_state_trace.csv`\n")
        f.write("- `segmentation_health.json`\n")

    return health


def main() -> int:
    print("──────── Phase 9 Shot Segmentation Validation ────────\n")
    try:
        health = run_validation()
    except (OSError, ValueError, KeyError) as e:
        print(f"FAIL: {e}")
        return 1
    print(f"Input shape: {tuple(health['input_shape'])}")
    print(f"Segments detected: {health['segments_detected']}/{health['total_sequences']}")
    print(f"Single-trigger sequences: {health['single_trigger_sequences']}/{health['total_sequences']}")
    print(f"Sequence-end completions: {health['forced_sequence_end_completions']}")
    print(f"Validation passed: {health['validation_passed']}")
    print(f"Report: {ARTIFACT_DIR / 'segmentation_debug_report.md'}")
    return 0 if health["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
