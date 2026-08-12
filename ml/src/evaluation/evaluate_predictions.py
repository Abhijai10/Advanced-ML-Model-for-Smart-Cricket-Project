"""Reproducible Smart Cricket prediction evaluation entry point."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .calibration_report import build_calibration_report, load_prediction_rows, write_reliability_svg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", required=True, help="CSV, JSON, or JSONL predictions with true labels and probabilities.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--labels", default="cover_drive,defensive_shot,pull_shot,sweep_shot")
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument("--thresholds", default="0.5,0.6,0.7,0.8,0.9")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    try:
        labels = [item.strip() for item in args.labels.split(",") if item.strip()]
        thresholds = [float(item.strip()) for item in args.thresholds.split(",") if item.strip()]
        report = build_calibration_report(
            load_prediction_rows(args.predictions),
            labels=labels,
            bins=args.bins,
            thresholds=thresholds,
        )
        run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report.update(
            {
                "evaluation_entry_point": "python -m ml.src.evaluation.evaluate_predictions",
                "run_id": run_id,
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "predictions_path": str(Path(args.predictions)),
                "model_quality_claim": "No production model-quality claim is made unless this report is run on player-held-out, coach-reviewed data.",
            }
        )
        output_dir = Path(args.output_dir) / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "evaluation_report.json"
        svg_path = output_dir / "reliability_diagram.svg"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        write_reliability_svg(report, svg_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote evaluation report: {report_path}")
    print(f"Wrote reliability diagram: {svg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
