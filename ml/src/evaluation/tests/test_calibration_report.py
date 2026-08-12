from __future__ import annotations

import csv
import json

import pytest

from ml.src.evaluation.calibration_report import build_calibration_report, load_prediction_rows, write_reliability_svg


def _rows() -> list[dict[str, object]]:
    return [
        {"true_label": "cover_drive", "probabilities": {"cover_drive": 0.8, "pull_shot": 0.2}},
        {"true_label": "pull_shot", "probabilities": {"cover_drive": 0.3, "pull_shot": 0.7}},
        {"true_label": "pull_shot", "probabilities": {"cover_drive": 0.6, "pull_shot": 0.4}},
    ]


def test_calibration_report_includes_release_metrics() -> None:
    report = build_calibration_report(_rows(), labels=["cover_drive", "pull_shot"], bins=5, thresholds=[0.5, 0.7])

    assert report["sample_count"] == 3
    assert report["accuracy"] == pytest.approx(2 / 3)
    assert report["brier_score_multiclass"] == pytest.approx((0.08 + 0.18 + 0.72) / 3)
    assert report["confusion_matrix"] == [[1, 0], [1, 1]]
    assert len(report["reliability_bins"]) == 5
    assert report["uncertainty_rejection_curve"][1]["confidence_threshold"] == 0.7
    assert report["class_metrics"]["pull_shot"]["support"] == 2


def test_csv_probability_columns_are_supported(tmp_path) -> None:
    path = tmp_path / "predictions.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["true_label", "prob_cover_drive", "prob_pull_shot"])
        writer.writeheader()
        writer.writerow({"true_label": "cover_drive", "prob_cover_drive": "0.9", "prob_pull_shot": "0.1"})

    report = build_calibration_report(load_prediction_rows(path), labels=["cover_drive", "pull_shot"])

    assert report["accuracy"] == 1.0
    assert report["prediction_counts"] == {"cover_drive": 1}


def test_probability_json_string_and_svg(tmp_path) -> None:
    report = build_calibration_report(
        [{"true_label": "cover_drive", "probabilities": json.dumps({"cover_drive": 1.0})}],
        labels=["cover_drive"],
    )
    svg_path = tmp_path / "reliability.svg"
    write_reliability_svg(report, svg_path)

    assert report["negative_log_likelihood"] == pytest.approx(0.0)
    assert "<svg" in svg_path.read_text(encoding="utf-8")


def test_missing_probabilities_fails_loudly() -> None:
    with pytest.raises(ValueError, match="missing probabilities"):
        build_calibration_report([{"true_label": "cover_drive"}])


def test_unknown_true_label_fails_when_labels_are_explicit() -> None:
    with pytest.raises(ValueError, match="not present in the evaluation label list"):
        build_calibration_report(
            [{"true_label": "sweep_shot", "probabilities": {"cover_drive": 0.5, "pull_shot": 0.5}}],
            labels=["cover_drive", "pull_shot"],
        )
