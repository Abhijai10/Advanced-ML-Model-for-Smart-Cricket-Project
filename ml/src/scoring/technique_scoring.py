"""Rule-based technique scoring for temporal cricket shot sequences.

Phase 10 turns a predicted shot plus engineered temporal features into an
interpretable technique score. It does not use classifier confidence as a proxy
for shot quality.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from scoring.score_config import (  # noqa: E402
    COMPONENT_CONFIGS,
    EXPECTED_FEATURE_DIM,
    EXPECTED_NUM_CLASSES,
    EXPECTED_SEQUENCE_LENGTH,
    MIN_TEMPLATE_SAMPLES,
    MIN_TEMPLATE_SPAN,
    OUTSIDE_RANGE_TOLERANCE_MULTIPLIER,
    PHASE10_VERSION,
    TEMPLATE_QUANTILE_HIGH,
    TEMPLATE_QUANTILE_LOW,
    ComponentScoreConfig,
    FeatureScoreSpec,
    component_weight_sum,
)


ML_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ML_ROOT.parent
DATASET_DIR = ML_ROOT / "data" / "final_temporal"
PHASE8_BEST_RUN_DIR = ML_ROOT / "artifacts" / "phase8" / "experiments" / "bigru_seed42"
PHASE10_DIR = ML_ROOT / "artifacts" / "phase10"
TEMPLATE_PATH = PHASE10_DIR / "ideal_template_schema.json"
SCORES_CSV_PATH = PHASE10_DIR / "technique_scores.csv"
REPORT_JSON_PATH = PHASE10_DIR / "technique_score_report.json"
REPORT_MD_PATH = PHASE10_DIR / "technique_score_report.md"
HEALTH_PATH = PHASE10_DIR / "technique_scoring_health.json"
METADATA_PATH = ML_ROOT / "data" / "annotations" / "metadata.csv"


@dataclass(frozen=True)
class FeatureDeviation:
    """Feature-level deviation from the shot template."""

    feature_name: str
    statistic: str
    actual_value: float
    expected_low: float
    expected_high: float
    template_center: float
    deviation: float
    score: float


@dataclass(frozen=True)
class ComponentScore:
    """Interpretable score for one technique component."""

    component_name: str
    score: float
    weight: float
    description: str
    deviations: tuple[FeatureDeviation, ...]


@dataclass(frozen=True)
class TechniqueScoreResult:
    """Complete Phase 10 score output for one shot sequence."""

    technique_match_score: float
    predicted_shot: str
    classifier_confidence: float | None
    component_scores: tuple[ComponentScore, ...]
    deviation_summary: tuple[str, ...]
    recommendations: tuple[str, ...]


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


def _validate_sequence(sequence: np.ndarray) -> None:
    if not isinstance(sequence, np.ndarray):
        raise ValueError(f"Expected numpy.ndarray, got {type(sequence).__name__}.")
    if sequence.ndim != 2:
        raise ValueError(f"Expected one sequence shaped [60,32], got {sequence.shape}.")
    if sequence.shape != (EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM):
        raise ValueError(
            f"Expected sequence shape {(EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM)}, got {sequence.shape}."
        )
    if not np.isfinite(sequence).all():
        raise ValueError("Sequence contains NaN or infinite values.")


def _feature_index(feature_columns: list[str], feature_name: str) -> int:
    if feature_name not in feature_columns:
        raise ValueError(f"Feature {feature_name!r} missing from temporal schema.")
    return feature_columns.index(feature_name)


def _summary_stat(values: np.ndarray, statistic: str) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"Expected non-empty rank-1 values, got shape {arr.shape}.")
    if statistic == "mean":
        return float(arr.mean())
    if statistic == "abs_mean":
        return float(np.abs(arr).mean())
    if statistic == "std":
        return float(arr.std())
    if statistic == "max":
        return float(arr.max())
    if statistic == "max_abs":
        return float(np.abs(arr).max())
    if statistic == "range":
        return float(arr.max() - arr.min())
    if statistic == "final_mean":
        start = max(0, int(arr.size * 2 / 3))
        return float(arr[start:].mean())
    raise ValueError(f"Unsupported scoring statistic: {statistic}")


def summarize_feature(sequence: np.ndarray, feature_columns: list[str], spec: FeatureScoreSpec) -> float:
    """Summarize one temporal feature using the configured statistic."""
    _validate_sequence(sequence)
    idx = _feature_index(feature_columns, spec.feature_name)
    return _summary_stat(sequence[:, idx], spec.statistic)


def _metadata_quality_by_file() -> dict[str, str]:
    if not METADATA_PATH.is_file():
        return {}
    df = pd.read_csv(METADATA_PATH)
    if not {"file_name", "quality"}.issubset(df.columns):
        return {}
    return {str(row["file_name"]): str(row["quality"]) for _, row in df.iterrows()}


def _class_names(label_mapping: dict[str, Any]) -> list[str]:
    index_to_class = label_mapping.get("index_to_class")
    if not isinstance(index_to_class, dict):
        raise ValueError("temporal_label_mapping.json missing index_to_class.")
    return [str(index_to_class[str(i)]) for i in range(len(index_to_class))]


def _template_sample_indices(
    train_index: pd.DataFrame,
    y_train: np.ndarray,
    class_index: int,
    quality_by_file: dict[str, str],
) -> tuple[np.ndarray, str]:
    class_rows = np.where(y_train == class_index)[0]
    good_rows: list[int] = []
    for local_idx in class_rows:
        file_name = str(train_index.iloc[int(local_idx)]["file_name"])
        if quality_by_file.get(file_name) == "good":
            good_rows.append(int(local_idx))
    if len(good_rows) >= MIN_TEMPLATE_SAMPLES:
        return np.asarray(good_rows, dtype=np.int64), "train_split_good_quality_examples"
    return class_rows.astype(np.int64), "train_split_all_examples_fallback"


def build_ideal_templates(
    X_train: np.ndarray,
    y_train: np.ndarray,
    train_index: pd.DataFrame,
    feature_columns: list[str],
    class_names: list[str],
) -> dict[str, Any]:
    """Create shot-specific measurable-feature templates from the training split."""
    if X_train.ndim != 3 or X_train.shape[1:] != (EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM):
        raise ValueError(f"Unexpected X_train shape: {X_train.shape}")
    if y_train.shape != (X_train.shape[0],):
        raise ValueError(f"Unexpected y_train shape: {y_train.shape}")
    if len(train_index) != len(y_train):
        raise ValueError("train_temporal_index.csv row count does not match y_train.")
    if len(class_names) != EXPECTED_NUM_CLASSES:
        raise ValueError(f"Expected {EXPECTED_NUM_CLASSES} classes, got {len(class_names)}.")
    if abs(component_weight_sum() - 1.0) > 1e-9:
        raise ValueError("Technique component weights must sum to 1.0.")

    quality_by_file = _metadata_quality_by_file()
    templates: dict[str, Any] = {}
    for class_index, class_name in enumerate(class_names):
        sample_indices, source = _template_sample_indices(train_index, y_train, class_index, quality_by_file)
        if len(sample_indices) < MIN_TEMPLATE_SAMPLES:
            raise ValueError(f"Class {class_name!r} has only {len(sample_indices)} template samples.")
        shot_template: dict[str, Any] = {
            "class_index": class_index,
            "template_source": source,
            "template_sample_count": int(len(sample_indices)),
            "components": {},
        }
        for component in COMPONENT_CONFIGS:
            component_payload: dict[str, Any] = {
                "weight": component.weight,
                "description": component.description,
                "features": {},
            }
            for spec in component.feature_specs:
                values = np.asarray(
                    [
                        summarize_feature(X_train[int(i)], feature_columns, spec)
                        for i in sample_indices
                    ],
                    dtype=np.float64,
                )
                low = float(np.percentile(values, TEMPLATE_QUANTILE_LOW))
                high = float(np.percentile(values, TEMPLATE_QUANTILE_HIGH))
                center = float(np.median(values))
                if high - low < MIN_TEMPLATE_SPAN:
                    pad = max(abs(center) * 0.05, MIN_TEMPLATE_SPAN)
                    low = center - pad
                    high = center + pad
                component_payload["features"][f"{spec.feature_name}:{spec.statistic}"] = {
                    "feature_name": spec.feature_name,
                    "statistic": spec.statistic,
                    "expected_low": low,
                    "expected_high": high,
                    "template_center": center,
                    "template_std": float(values.std()),
                }
            shot_template["components"][component.name] = component_payload
        templates[class_name] = shot_template

    return {
        "schema_name": "smart_cricket_ideal_technique_template_schema",
        "phase": "Phase 10",
        "version": PHASE10_VERSION,
        "created_at": _utc_now(),
        "dataset_split_used": "train",
        "template_strategy": (
            "Prefer good-quality training examples per shot class; fall back to all training examples "
            "when fewer than three good-quality examples are available."
        ),
        "score_range": [0, 100],
        "component_weight_sum": component_weight_sum(),
        "template_quantiles": {
            "low": TEMPLATE_QUANTILE_LOW,
            "high": TEMPLATE_QUANTILE_HIGH,
        },
        "shot_templates": templates,
        "notes": [
            "Templates are derived only from the train split to avoid using validation/test samples as ideal references.",
            "Classifier confidence is stored separately and is not used as the technique score.",
            "Future versions can replace these v1 templates with coach-reviewed professional reference clips.",
        ],
    }


def _score_from_range(actual: float, low: float, high: float) -> tuple[float, float]:
    if low <= actual <= high:
        return 100.0, 0.0
    span = max(high - low, MIN_TEMPLATE_SPAN)
    deviation = low - actual if actual < low else actual - high
    tolerance = span * OUTSIDE_RANGE_TOLERANCE_MULTIPLIER
    score = max(0.0, 100.0 * (1.0 - deviation / tolerance))
    return float(score), float(deviation)


def score_component(
    sequence: np.ndarray,
    feature_columns: list[str],
    component_config: ComponentScoreConfig,
    component_template: dict[str, Any],
) -> ComponentScore:
    """Compute one component score and feature-level deviations."""
    deviations: list[FeatureDeviation] = []
    for spec in component_config.feature_specs:
        key = f"{spec.feature_name}:{spec.statistic}"
        if key not in component_template["features"]:
            raise ValueError(f"Template missing feature spec {key!r}.")
        tmpl = component_template["features"][key]
        actual = summarize_feature(sequence, feature_columns, spec)
        score, deviation = _score_from_range(
            actual,
            float(tmpl["expected_low"]),
            float(tmpl["expected_high"]),
        )
        deviations.append(
            FeatureDeviation(
                feature_name=spec.feature_name,
                statistic=spec.statistic,
                actual_value=actual,
                expected_low=float(tmpl["expected_low"]),
                expected_high=float(tmpl["expected_high"]),
                template_center=float(tmpl["template_center"]),
                deviation=deviation,
                score=score,
            )
        )
    component_score = float(np.mean([d.score for d in deviations]))
    return ComponentScore(
        component_name=component_config.name,
        score=component_score,
        weight=component_config.weight,
        description=component_config.description,
        deviations=tuple(deviations),
    )


def _deviation_summary(components: Iterable[ComponentScore]) -> tuple[str, ...]:
    all_deviations = [
        d
        for component in components
        for d in component.deviations
        if d.score < 100.0
    ]
    all_deviations.sort(key=lambda d: (d.score, -d.deviation))
    summary: list[str] = []
    seen: set[tuple[str, str, float]] = set()
    for dev in all_deviations:
        dedupe_key = (dev.feature_name, dev.statistic, round(dev.actual_value, 6))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        direction = "below" if dev.actual_value < dev.expected_low else "above"
        summary.append(
            f"{dev.feature_name} ({dev.statistic}) is {direction} the template range "
            f"[{dev.expected_low:.4f}, {dev.expected_high:.4f}] with value {dev.actual_value:.4f}."
        )
        if len(summary) >= 5:
            break
    if not summary:
        summary.append("All measured component features fall within their v1 template ranges.")
    return tuple(summary)


def _recommendations(components: Iterable[ComponentScore]) -> tuple[str, ...]:
    ordered = sorted(components, key=lambda c: c.score)
    recommendations: list[str] = []
    for component in ordered[:3]:
        if component.score >= 85.0:
            continue
        label = component.component_name.replace("_score", "").replace("_", " ")
        recommendations.append(f"Prioritize {label}; it is the weakest measured component.")
    if not recommendations:
        recommendations.append("Maintain current movement pattern; v1 component scores are consistently strong.")
    return tuple(recommendations)


def score_sequence(
    sequence: np.ndarray,
    *,
    predicted_shot: str,
    feature_columns: list[str],
    templates: dict[str, Any],
    classifier_confidence: float | None = None,
) -> TechniqueScoreResult:
    """Return total and component technique scores for one predicted shot."""
    _validate_sequence(sequence)
    shot_templates = templates.get("shot_templates")
    if not isinstance(shot_templates, dict) or predicted_shot not in shot_templates:
        raise ValueError(f"No technique template found for predicted shot {predicted_shot!r}.")
    shot_template = shot_templates[predicted_shot]
    components: list[ComponentScore] = []
    for component_config in COMPONENT_CONFIGS:
        component_template = shot_template["components"][component_config.name]
        components.append(
            score_component(sequence, feature_columns, component_config, component_template)
        )
    weighted = sum(component.score * component.weight for component in components)
    return TechniqueScoreResult(
        technique_match_score=float(round(weighted, 4)),
        predicted_shot=predicted_shot,
        classifier_confidence=classifier_confidence,
        component_scores=tuple(components),
        deviation_summary=_deviation_summary(components),
        recommendations=_recommendations(components),
    )


def _result_to_dict(result: TechniqueScoreResult) -> dict[str, Any]:
    return {
        "technique_match_score": result.technique_match_score,
        "predicted_shot": result.predicted_shot,
        "classifier_confidence": result.classifier_confidence,
        "component_scores": {
            component.component_name: {
                "score": component.score,
                "weight": component.weight,
                "description": component.description,
                "deviations": [asdict(dev) for dev in component.deviations],
            }
            for component in result.component_scores
        },
        "deviation_summary": list(result.deviation_summary),
        "recommendations": list(result.recommendations),
    }


def _flat_score_row(base: dict[str, Any], result: TechniqueScoreResult) -> dict[str, Any]:
    row = dict(base)
    row["technique_match_score"] = result.technique_match_score
    row["classifier_confidence"] = result.classifier_confidence
    for component in result.component_scores:
        row[component.component_name] = round(component.score, 4)
    row["weakest_component"] = min(result.component_scores, key=lambda c: c.score).component_name
    row["primary_recommendation"] = result.recommendations[0]
    row["deviation_summary"] = " | ".join(result.deviation_summary)
    return row


def _load_predictions(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Missing selected-model predictions: {path}")
    df = pd.read_csv(path)
    required = {
        "row_index",
        "file_name",
        "true_label_name",
        "predicted_label_name",
        "confidence",
        "correct",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Prediction CSV missing columns: {sorted(missing)}")
    return df


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value!r}")


def generate_phase10_artifacts() -> dict[str, Any]:
    """Build templates, score selected-model test predictions, and write artifacts."""
    PHASE10_DIR.mkdir(parents=True, exist_ok=True)
    schema = _load_json(DATASET_DIR / "temporal_feature_schema.json")
    label_mapping = _load_json(DATASET_DIR / "temporal_label_mapping.json")
    feature_columns = list(schema.get("feature_columns", []))
    if len(feature_columns) != EXPECTED_FEATURE_DIM:
        raise ValueError("Temporal feature schema must contain 32 feature columns.")
    class_names = _class_names(label_mapping)

    X_train = np.load(DATASET_DIR / "X_train_sequence.npy")
    y_train = np.load(DATASET_DIR / "y_train_sequence.npy")
    X_test = np.load(DATASET_DIR / "X_test_sequence.npy")
    y_test = np.load(DATASET_DIR / "y_test_sequence.npy")
    if X_test.ndim != 3 or X_test.shape[1:] != (EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM):
        raise ValueError(f"Unexpected X_test shape: {X_test.shape}")
    if y_test.shape != (X_test.shape[0],):
        raise ValueError(f"Unexpected y_test shape: {y_test.shape}")
    train_index = pd.read_csv(DATASET_DIR / "train_temporal_index.csv")
    test_index = pd.read_csv(DATASET_DIR / "test_temporal_index.csv")
    if len(test_index) != len(y_test):
        raise ValueError("test_temporal_index.csv row count does not match y_test.")

    templates = build_ideal_templates(X_train, y_train, train_index, feature_columns, class_names)
    _write_json(TEMPLATE_PATH, templates)

    predictions = _load_predictions(PHASE8_BEST_RUN_DIR / "predictions" / "test_predictions.csv")
    if len(predictions) != len(y_test):
        raise ValueError("Selected-model test prediction row count does not match y_test.")

    rows: list[dict[str, Any]] = []
    detailed_samples: list[dict[str, Any]] = []
    for i, pred_row in predictions.reset_index(drop=True).iterrows():
        expected_row_index = int(test_index.iloc[int(i)]["row_index"])
        actual_row_index = int(pred_row["row_index"])
        if actual_row_index != expected_row_index:
            raise ValueError(
                f"Prediction/index mismatch at test row {i}: {actual_row_index} != {expected_row_index}."
            )
        predicted_shot = str(pred_row["predicted_label_name"])
        result = score_sequence(
            X_test[int(i)],
            predicted_shot=predicted_shot,
            feature_columns=feature_columns,
            templates=templates,
            classifier_confidence=float(pred_row["confidence"]),
        )
        base = {
            "split": "test",
            "test_sample_index": int(i),
            "row_index": actual_row_index,
            "file_name": str(pred_row["file_name"]),
            "true_label_name": str(pred_row["true_label_name"]),
            "predicted_label_name": predicted_shot,
            "prediction_correct": _as_bool(pred_row["correct"]),
        }
        rows.append(_flat_score_row(base, result))
        detailed_samples.append({**base, "score_result": _result_to_dict(result)})

    fieldnames = list(rows[0].keys())
    with SCORES_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    scores = np.asarray([row["technique_match_score"] for row in rows], dtype=np.float64)
    component_means = {
        component.name: float(np.mean([row[component.name] for row in rows]))
        for component in COMPONENT_CONFIGS
    }
    weakest_counts = dict(Counter(row["weakest_component"] for row in rows))
    report = {
        "phase": "Phase 10",
        "version": PHASE10_VERSION,
        "created_at": _utc_now(),
        "input_contract": {
            "split_scored": "test",
            "samples_scored": len(rows),
            "sequence_shape": [EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM],
            "prediction_source": str(PHASE8_BEST_RUN_DIR / "predictions" / "test_predictions.csv"),
            "template_source": str(TEMPLATE_PATH),
        },
        "score_summary": {
            "mean_technique_match_score": float(scores.mean()),
            "min_technique_match_score": float(scores.min()),
            "max_technique_match_score": float(scores.max()),
            "component_mean_scores": component_means,
            "weakest_component_counts": weakest_counts,
        },
        "scoring_philosophy": [
            "Technique match score is computed from measurable biomechanical feature deviations.",
            "Classifier confidence is included for traceability but does not contribute to the score.",
            "Component scores are returned so Phase 11 can generate specific feedback.",
        ],
        "samples": detailed_samples,
    }
    _write_json(REPORT_JSON_PATH, report)

    health = {
        "phase": "Phase 10",
        "version": PHASE10_VERSION,
        "created_at": _utc_now(),
        "templates_created": len(templates["shot_templates"]),
        "components_per_template": len(COMPONENT_CONFIGS),
        "samples_scored": len(rows),
        "score_range_valid": bool(np.all((scores >= 0.0) & (scores <= 100.0))),
        "all_component_scores_valid": bool(
            all(0.0 <= row[component.name] <= 100.0 for row in rows for component in COMPONENT_CONFIGS)
        ),
        "classifier_confidence_used_as_score": False,
        "validation_passed": bool(len(rows) == len(y_test) and np.all((scores >= 0.0) & (scores <= 100.0))),
        "output_files": {
            "ideal_template_schema": str(TEMPLATE_PATH),
            "technique_scores_csv": str(SCORES_CSV_PATH),
            "technique_score_report_json": str(REPORT_JSON_PATH),
            "technique_score_report_md": str(REPORT_MD_PATH),
            "technique_scoring_health": str(HEALTH_PATH),
        },
    }
    _write_json(HEALTH_PATH, health)
    _write_markdown_report(report, health)
    return health


def _write_markdown_report(report: dict[str, Any], health: dict[str, Any]) -> None:
    summary = report["score_summary"]
    with REPORT_MD_PATH.open("w", encoding="utf-8") as f:
        f.write("# Phase 10 Technique Scoring Report\n\n")
        f.write("## Validation Status\n\n")
        f.write(f"- Validation passed: `{health['validation_passed']}`\n")
        f.write(f"- Samples scored: `{health['samples_scored']}`\n")
        f.write(f"- Templates created: `{health['templates_created']}`\n")
        f.write("- Classifier confidence used as technique score: `False`\n\n")
        f.write("## Score Summary\n\n")
        f.write(f"- Mean technique match score: `{summary['mean_technique_match_score']:.4f}`\n")
        f.write(f"- Minimum technique match score: `{summary['min_technique_match_score']:.4f}`\n")
        f.write(f"- Maximum technique match score: `{summary['max_technique_match_score']:.4f}`\n\n")
        f.write("## Component Mean Scores\n\n")
        for name, value in summary["component_mean_scores"].items():
            f.write(f"- `{name}`: `{value:.4f}`\n")
        f.write("\n## Weakest Component Counts\n\n")
        for name, count in sorted(summary["weakest_component_counts"].items()):
            f.write(f"- `{name}`: `{count}`\n")
        f.write("\n## Interpretation Notes\n\n")
        f.write(
            "- Scores are template-match indicators, not biomechanical truth labels.\n"
            "- V1 templates are train-split-derived references because professional reference clips are not yet available.\n"
            "- Phase 11 should use component scores and deviation summaries to generate specific coaching feedback.\n"
        )


def main() -> int:
    health = generate_phase10_artifacts()
    print("Phase 10 Technique Scoring")
    print(f"templates created: {health['templates_created']}")
    print(f"components per template: {health['components_per_template']}")
    print(f"samples scored: {health['samples_scored']}")
    print(f"score range valid: {health['score_range_valid']}")
    print(f"validation passed: {health['validation_passed']}")
    print(f"template path: {TEMPLATE_PATH}")
    print(f"report path: {REPORT_JSON_PATH}")
    return 0 if health["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
