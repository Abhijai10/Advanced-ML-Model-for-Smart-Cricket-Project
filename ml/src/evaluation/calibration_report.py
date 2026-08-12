"""Calibration, reliability, and uncertainty report generation."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

EPSILON = 1e-12


def load_prediction_rows(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"predictions file not found: {p}")
    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if p.suffix.lower() == ".jsonl":
        rows = []
        with p.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{p}:{line_no} must contain a JSON object.")
                rows.append(row)
        return rows
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for key in ("predictions", "samples", "rows"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise ValueError("JSON predictions must be a list of objects or contain predictions/samples/rows.")
        return list(data)
    raise ValueError(f"unsupported predictions extension: {p.suffix}")


def _parse_probability_value(value: Any) -> dict[str, float]:
    if isinstance(value, dict):
        return {str(key): float(val) for key, val in value.items()}
    if isinstance(value, str) and value.strip():
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return {str(key): float(val) for key, val in parsed.items()}
    raise ValueError("probabilities must be an object.")


def extract_probabilities(row: dict[str, Any]) -> dict[str, float]:
    for key in ("probabilities", "class_probabilities"):
        if key in row:
            return _parse_probability_value(row[key])
    prediction = row.get("prediction")
    if isinstance(prediction, dict):
        for key in ("probabilities", "class_probabilities"):
            if key in prediction:
                return _parse_probability_value(prediction[key])
    prob_columns = {
        key.removeprefix("prob_"): float(value)
        for key, value in row.items()
        if key.startswith("prob_") and str(value).strip() != ""
    }
    if prob_columns:
        return prob_columns
    raise ValueError("row is missing probabilities/class_probabilities/prob_* columns.")


def true_label(row: dict[str, Any]) -> str:
    for key in ("true_label", "label", "shot_label", "expected_label"):
        value = str(row.get(key, "")).strip()
        if value:
            return value
    raise ValueError("row is missing true_label/label/shot_label.")


def normalize_probabilities(probabilities: dict[str, float], labels: list[str]) -> dict[str, float]:
    out = {label: float(probabilities.get(label, 0.0)) for label in labels}
    if any(value < 0 for value in out.values()):
        raise ValueError("probabilities must be non-negative.")
    total = sum(out.values())
    if total <= 0:
        raise ValueError("probabilities must sum to a positive value.")
    return {label: value / total for label, value in out.items()}


def _infer_labels(rows: list[dict[str, Any]]) -> list[str]:
    labels = set()
    for row in rows:
        labels.add(true_label(row))
        labels.update(extract_probabilities(row))
    return sorted(labels)


def _class_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    for label in labels:
        tp = sum(t == label and p == label for t, p in zip(y_true, y_pred))
        fp = sum(t != label and p == label for t, p in zip(y_true, y_pred))
        fn = sum(t == label and p != label for t, p in zip(y_true, y_pred))
        support = sum(t == label for t in y_true)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        metrics[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
    return metrics


def _confusion_matrix(y_true: list[str], y_pred: list[str], labels: list[str]) -> list[list[int]]:
    return [
        [sum(t == true_name and p == pred_name for t, p in zip(y_true, y_pred)) for pred_name in labels]
        for true_name in labels
    ]


def _reliability_bins(confidences: list[float], correct: list[bool], bins: int) -> tuple[list[dict[str, float | int]], float, float]:
    if bins <= 0:
        raise ValueError("bins must be positive.")
    total = len(confidences)
    rows = []
    ece = 0.0
    mce = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        members = [
            sample_index
            for sample_index, confidence in enumerate(confidences)
            if confidence >= lower and (confidence <= upper if index == bins - 1 else confidence < upper)
        ]
        count = len(members)
        accuracy = sum(1 for sample_index in members if correct[sample_index]) / count if count else 0.0
        avg_confidence = sum(confidences[sample_index] for sample_index in members) / count if count else 0.0
        gap = abs(accuracy - avg_confidence) if count else 0.0
        ece += (count / total) * gap if total else 0.0
        mce = max(mce, gap)
        rows.append(
            {
                "bin": index,
                "lower": lower,
                "upper": upper,
                "count": count,
                "accuracy": accuracy,
                "average_confidence": avg_confidence,
                "calibration_gap": gap,
            }
        )
    return rows, ece, mce


def _rejection_curve(confidences: list[float], correct: list[bool], thresholds: list[float]) -> list[dict[str, float | int]]:
    total = len(confidences)
    rows = []
    for threshold in thresholds:
        accepted = [index for index, confidence in enumerate(confidences) if confidence >= threshold]
        accepted_count = len(accepted)
        rows.append(
            {
                "confidence_threshold": threshold,
                "accepted_count": accepted_count,
                "rejected_count": total - accepted_count,
                "coverage": accepted_count / total if total else 0.0,
                "accepted_accuracy": sum(1 for index in accepted if correct[index]) / accepted_count if accepted_count else 0.0,
            }
        )
    return rows


def build_calibration_report(
    rows: list[dict[str, Any]],
    *,
    labels: list[str] | None = None,
    bins: int = 10,
    thresholds: list[float] | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("predictions file has no rows.")
    label_order = labels or _infer_labels(rows)
    thresholds = thresholds or [0.0, 0.5, 0.6, 0.7, 0.8, 0.9]
    y_true: list[str] = []
    y_pred: list[str] = []
    confidences: list[float] = []
    correct: list[bool] = []
    nll_values: list[float] = []
    brier_values: list[float] = []
    for row in rows:
        label = true_label(row)
        if label not in label_order:
            raise ValueError(f"true label {label!r} is not present in the evaluation label list.")
        probabilities = normalize_probabilities(extract_probabilities(row), label_order)
        prediction = max(label_order, key=lambda item: probabilities[item])
        confidence = probabilities[prediction]
        y_true.append(label)
        y_pred.append(prediction)
        confidences.append(confidence)
        correct.append(label == prediction)
        nll_values.append(-math.log(max(probabilities.get(label, 0.0), EPSILON)))
        brier_values.append(sum((probabilities[item] - (1.0 if item == label else 0.0)) ** 2 for item in label_order))
    class_metrics = _class_metrics(y_true, y_pred, label_order)
    reliability_bins, ece, mce = _reliability_bins(confidences, correct, bins)
    return {
        "report_type": "smart_cricket_calibration_v1",
        "sample_count": len(rows),
        "labels": label_order,
        "accuracy": sum(correct) / len(correct),
        "macro_f1": sum(float(item["f1"]) for item in class_metrics.values()) / len(class_metrics),
        "negative_log_likelihood": sum(nll_values) / len(nll_values),
        "brier_score_multiclass": sum(brier_values) / len(brier_values),
        "expected_calibration_error": ece,
        "maximum_calibration_error": mce,
        "average_confidence": sum(confidences) / len(confidences),
        "prediction_counts": dict(sorted(Counter(y_pred).items())),
        "class_metrics": class_metrics,
        "confusion_matrix": _confusion_matrix(y_true, y_pred, label_order),
        "reliability_bins": reliability_bins,
        "uncertainty_rejection_curve": _rejection_curve(confidences, correct, thresholds),
        "release_note": "Run this on player-held-out, coach-reviewed predictions before setting production thresholds.",
    }


def write_reliability_svg(report: dict[str, Any], path: str | Path) -> None:
    bins = report.get("reliability_bins")
    if not isinstance(bins, list):
        raise ValueError("report missing reliability_bins")
    width = 520
    height = 420
    margin = 54
    plot = height - 2 * margin
    bars = []
    for item in bins:
        if not isinstance(item, dict):
            continue
        x = margin + float(item["lower"]) * plot
        bar_width = max(2, (float(item["upper"]) - float(item["lower"])) * plot - 2)
        y = margin + (1.0 - float(item["accuracy"])) * plot
        bar_height = height - margin - y
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="#2f80ed" opacity="0.78" />')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Smart Cricket reliability diagram">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <line x1="{margin}" y1="{height - margin}" x2="{height - margin}" y2="{margin}" stroke="#222" stroke-width="2"/>
  <line x1="{margin}" y1="{height - margin}" x2="{height - margin}" y2="{height - margin}" stroke="#222" stroke-width="2"/>
  <line x1="{margin}" y1="{height - margin}" x2="{height - margin}" y2="{margin}" stroke="#d13f31" stroke-width="2" stroke-dasharray="6 6"/>
  {''.join(bars)}
  <text x="{width / 2:.1f}" y="28" text-anchor="middle" font-family="Arial" font-size="18">Reliability Diagram</text>
  <text x="{width / 2:.1f}" y="{height - 12}" text-anchor="middle" font-family="Arial" font-size="13">Confidence</text>
  <text x="18" y="{height / 2:.1f}" text-anchor="middle" font-family="Arial" font-size="13" transform="rotate(-90 18 {height / 2:.1f})">Accuracy</text>
</svg>
'''
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(svg, encoding="utf-8")


def _csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def _float_csv(value: str | None) -> list[float] | None:
    values = _csv(value)
    return [float(item) for item in values] if values is not None else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--labels")
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument("--thresholds")
    parser.add_argument("--reliability-svg")
    args = parser.parse_args(argv)
    try:
        report = build_calibration_report(
            load_prediction_rows(args.input),
            labels=_csv(args.labels),
            bins=args.bins,
            thresholds=_float_csv(args.thresholds),
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        if args.reliability_svg:
            write_reliability_svg(report, args.reliability_svg)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote calibration report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
