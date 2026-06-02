"""Phase 5.5 Step 5 — Validate temporal features and flag weak feature signals.

Reads the rank-3 temporal tensor and schema, then writes analysis sidecars only.
Does not modify tensors, remove features, split data, or train models.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

_ML_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = _ML_ROOT / "data" / "final_temporal"
X_SEQUENCE_PATH = INPUT_DIR / "X_sequence.npy"
Y_LABELS_RAW_PATH = INPUT_DIR / "y_labels_raw.csv"
SCHEMA_PATH = INPUT_DIR / "temporal_feature_schema.json"

REPORT_PATH = INPUT_DIR / "temporal_feature_validation_report.md"
STATISTICS_CSV_PATH = INPUT_DIR / "temporal_feature_statistics.csv"
HEALTH_JSON_PATH = INPUT_DIR / "temporal_feature_health.json"

REQUIRED_FRAMES = 60
REQUIRED_FEATURES = 32

# Thresholds are intentionally conservative: this step reports concerns only.
DEAD_RANGE_EPS = 1e-12
NEAR_DEAD_VARIANCE_THRESHOLD = 1e-8
NEAR_DEAD_MEAN_DELTA_THRESHOLD = 1e-6
NEAR_ZERO_ABS_THRESHOLD = 1e-8
NOISY_DELTA_TO_RANGE_THRESHOLD = 0.35
NOISY_STD_TO_RANGE_THRESHOLD = 0.30
NOISY_STD_DELTA_TO_RANGE_THRESHOLD = 0.20
HIGH_CORRELATION_THRESHOLD = 0.95


def _load_schema() -> tuple[list[str], dict[str, str]]:
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"Missing temporal feature schema: {SCHEMA_PATH}")

    with SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)

    feature_names = schema.get("feature_columns")
    if not isinstance(feature_names, list) or len(feature_names) != REQUIRED_FEATURES:
        raise ValueError(
            "temporal_feature_schema.json must define exactly "
            f"{REQUIRED_FEATURES} feature_columns."
        )

    names = [str(name) for name in feature_names]
    if len(set(names)) != len(names):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise ValueError(f"Duplicate temporal feature names: {duplicates}")

    groups = schema.get("feature_groups")
    feature_to_group: dict[str, str] = {name: "unknown" for name in names}
    if isinstance(groups, dict):
        for group_name, group_features in groups.items():
            if not isinstance(group_features, list):
                continue
            for name in group_features:
                key = str(name)
                if key in feature_to_group:
                    feature_to_group[key] = str(group_name)

    return names, feature_to_group


def _load_labels(expected_samples: int) -> list[str]:
    if not Y_LABELS_RAW_PATH.is_file():
        raise FileNotFoundError(f"Missing raw label CSV: {Y_LABELS_RAW_PATH}")

    labels: list[str] = []
    with Y_LABELS_RAW_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "shot_label" not in reader.fieldnames:
            raise ValueError("y_labels_raw.csv must contain a shot_label column.")
        for row in reader:
            labels.append(str(row.get("shot_label", "")).strip())

    if len(labels) != expected_samples:
        raise ValueError(
            f"Label row count {len(labels)} != sample count {expected_samples}."
        )
    if any(label == "" for label in labels):
        raise ValueError("y_labels_raw.csv contains empty shot_label value(s).")
    return labels


def _load_and_validate_tensor() -> np.ndarray:
    if not X_SEQUENCE_PATH.is_file():
        raise FileNotFoundError(f"Missing temporal tensor: {X_SEQUENCE_PATH}")

    X = np.load(X_SEQUENCE_PATH)
    if X.ndim != 3:
        raise ValueError(f"X_sequence.npy must be rank 3, got rank {X.ndim}.")
    if X.shape[1] != REQUIRED_FRAMES:
        raise ValueError(
            f"X_sequence.npy time dimension must be {REQUIRED_FRAMES}, got {X.shape[1]}."
        )
    if X.shape[2] != REQUIRED_FEATURES:
        raise ValueError(
            f"X_sequence.npy feature dimension must be {REQUIRED_FEATURES}, got {X.shape[2]}."
        )
    if np.isnan(X).any():
        raise ValueError("X_sequence.npy contains NaN value(s).")
    if np.isinf(X).any():
        raise ValueError("X_sequence.npy contains infinite value(s).")
    if not np.isfinite(X).all():
        raise ValueError("X_sequence.npy contains non-finite value(s).")

    return X


def _safe_float(value: Any) -> float:
    x = float(value)
    return x if math.isfinite(x) else 0.0


def _status_and_notes(
    *,
    variance: float,
    value_range: float,
    mean_delta: float,
    std: float,
) -> tuple[str, list[str]]:
    notes: list[str] = []

    is_dead = variance == 0.0 or value_range <= DEAD_RANGE_EPS
    if is_dead:
        notes.append("dead: zero variance or effectively zero global range")
        return "dead", notes

    is_near_dead = (
        variance <= NEAR_DEAD_VARIANCE_THRESHOLD
        or mean_delta <= NEAR_DEAD_MEAN_DELTA_THRESHOLD
    )
    is_noisy_delta = (
        value_range > DEAD_RANGE_EPS
        and (mean_delta / value_range) >= NOISY_DELTA_TO_RANGE_THRESHOLD
    )
    is_noisy_unstable = (
        value_range > DEAD_RANGE_EPS
        and (std / value_range) >= NOISY_STD_TO_RANGE_THRESHOLD
        and (mean_delta / value_range) >= NOISY_STD_DELTA_TO_RANGE_THRESHOLD
    )

    if is_near_dead:
        notes.append("near-dead: very small variance or temporal delta")
    if is_noisy_delta:
        notes.append("noisy: frame-to-frame delta is high relative to range")
    if is_noisy_unstable:
        notes.append("noisy: high spread with unstable temporal behavior")

    if is_near_dead:
        return "near_dead", notes
    if is_noisy_delta or is_noisy_unstable:
        return "noisy", notes
    return "healthy", notes


def _compute_feature_rows(
    X: np.ndarray,
    labels: list[str],
    feature_names: list[str],
    feature_to_group: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    label_array = np.array(labels)
    classes = sorted(set(labels))

    for idx, name in enumerate(feature_names):
        values = X[:, :, idx].astype(np.float64, copy=False)
        flat = values.reshape(-1)
        deltas = np.abs(np.diff(values, axis=1))

        mean = _safe_float(np.mean(flat))
        std = _safe_float(np.std(flat))
        min_value = _safe_float(np.min(flat))
        max_value = _safe_float(np.max(flat))
        value_range = _safe_float(max_value - min_value)
        variance = _safe_float(np.var(flat))
        mean_delta = _safe_float(np.mean(deltas)) if deltas.size else 0.0
        near_zero_pct = _safe_float(np.mean(np.abs(flat) <= NEAR_ZERO_ABS_THRESHOLD) * 100.0)

        health_status, notes = _status_and_notes(
            variance=variance,
            value_range=value_range,
            mean_delta=mean_delta,
            std=std,
        )

        row: dict[str, Any] = {
            "feature_name": name,
            "feature_index": idx,
            "feature_group": feature_to_group.get(name, "unknown"),
            "mean": mean,
            "std": std,
            "min": min_value,
            "max": max_value,
            "range": value_range,
            "variance": variance,
            "mean_abs_temporal_delta": mean_delta,
            "near_zero_percentage": near_zero_pct,
            "health_status": health_status,
            "notes": "; ".join(notes),
        }

        for class_name in classes:
            class_values = values[label_array == class_name, :].reshape(-1)
            row[f"class_mean__{class_name}"] = _safe_float(np.mean(class_values))
            row[f"class_std__{class_name}"] = _safe_float(np.std(class_values))

        rows.append(row)

    return rows


def _compute_high_correlations(
    X: np.ndarray,
    feature_names: list[str],
) -> list[dict[str, Any]]:
    flat = X.reshape(-1, X.shape[2]).astype(np.float64, copy=False)
    corr = np.corrcoef(flat, rowvar=False)

    pairs: list[dict[str, Any]] = []
    for i in range(len(feature_names)):
        for j in range(i + 1, len(feature_names)):
            value = float(corr[i, j])
            if not math.isfinite(value):
                continue
            if abs(value) > HIGH_CORRELATION_THRESHOLD:
                pairs.append(
                    {
                        "feature_a": feature_names[i],
                        "feature_b": feature_names[j],
                        "feature_a_index": i,
                        "feature_b_index": j,
                        "correlation": value,
                    }
                )

    pairs.sort(key=lambda item: abs(float(item["correlation"])), reverse=True)
    return pairs


def _write_statistics_csv(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("No feature statistics rows to write.")

    base_fields = [
        "feature_name",
        "feature_index",
        "feature_group",
        "mean",
        "std",
        "min",
        "max",
        "range",
        "variance",
        "mean_abs_temporal_delta",
        "near_zero_percentage",
        "health_status",
        "notes",
    ]
    extra_fields = [key for key in rows[0].keys() if key not in base_fields]
    fieldnames = base_fields + extra_fields

    with STATISTICS_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _thresholds_payload() -> dict[str, float]:
    return {
        "dead_range_epsilon": DEAD_RANGE_EPS,
        "near_dead_variance_threshold": NEAR_DEAD_VARIANCE_THRESHOLD,
        "near_dead_mean_abs_temporal_delta_threshold": NEAR_DEAD_MEAN_DELTA_THRESHOLD,
        "near_zero_absolute_value_threshold": NEAR_ZERO_ABS_THRESHOLD,
        "noisy_delta_to_range_threshold": NOISY_DELTA_TO_RANGE_THRESHOLD,
        "noisy_std_to_range_threshold": NOISY_STD_TO_RANGE_THRESHOLD,
        "noisy_std_delta_to_range_threshold": NOISY_STD_DELTA_TO_RANGE_THRESHOLD,
        "high_correlation_abs_threshold": HIGH_CORRELATION_THRESHOLD,
    }


def _build_recommendations(
    dead: list[str],
    near_dead: list[str],
    noisy: list[str],
    correlated_pairs: list[dict[str, Any]],
) -> list[str]:
    recommendations: list[str] = []
    if dead:
        recommendations.append(
            "Review dead features before model training; they add no signal in the current tensor."
        )
    if near_dead:
        recommendations.append(
            "Inspect near-dead features against pose extraction logic and cricket semantics before pruning."
        )
    if noisy:
        recommendations.append(
            "Keep noisy features for now, but compare model performance with smoothing or normalization."
        )
    if correlated_pairs:
        recommendations.append(
            "Audit highly correlated pairs during feature selection; retain both only if temporal semantics differ."
        )
    if not (dead or near_dead):
        recommendations.append(
            "No dead or near-dead blockers found; proceed to temporal model experiments with monitoring."
        )
    return recommendations


def _write_health_json(
    rows: list[dict[str, Any]],
    correlated_pairs: list[dict[str, Any]],
    recommendations: list[str],
) -> None:
    status_counts = Counter(str(row["health_status"]) for row in rows)
    dead = [str(row["feature_name"]) for row in rows if row["health_status"] == "dead"]
    near_dead = [
        str(row["feature_name"]) for row in rows if row["health_status"] == "near_dead"
    ]
    noisy = [str(row["feature_name"]) for row in rows if row["health_status"] == "noisy"]

    payload = {
        "total_features": len(rows),
        "healthy_features": int(status_counts.get("healthy", 0)),
        "dead_features": dead,
        "near_dead_features": near_dead,
        "noisy_features": noisy,
        "highly_correlated_pairs": correlated_pairs,
        "thresholds_used": _thresholds_payload(),
        "recommendations": recommendations,
    }

    with HEALTH_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _feature_lines(names: list[str]) -> list[str]:
    if not names:
        return ["- None"]
    return [f"- `{name}`" for name in names]


def _correlation_lines(pairs: list[dict[str, Any]]) -> list[str]:
    if not pairs:
        return ["- None"]
    return [
        "- "
        f"`{pair['feature_a']}` <-> `{pair['feature_b']}`: "
        f"{float(pair['correlation']):.6f}"
        for pair in pairs
    ]


def _write_report(
    *,
    X: np.ndarray,
    labels: list[str],
    rows: list[dict[str, Any]],
    correlated_pairs: list[dict[str, Any]],
    recommendations: list[str],
) -> None:
    status_counts = Counter(str(row["health_status"]) for row in rows)
    dead = [str(row["feature_name"]) for row in rows if row["health_status"] == "dead"]
    near_dead = [
        str(row["feature_name"]) for row in rows if row["health_status"] == "near_dead"
    ]
    noisy = [str(row["feature_name"]) for row in rows if row["health_status"] == "noisy"]
    class_counts = Counter(labels)

    lines: list[str] = [
        "# Temporal Feature Validation Report",
        "",
        "## Dataset Shape",
        "",
        f"- X_sequence shape: `{tuple(X.shape)}`",
        f"- Samples: `{X.shape[0]}`",
        f"- Time steps: `{X.shape[1]}`",
        f"- Features: `{X.shape[2]}`",
        f"- Label distribution: `{dict(sorted(class_counts.items()))}`",
        "",
        "## Validation Status",
        "",
        "- Rank check: passed",
        "- Expected shape `[samples, 60, 32]`: passed",
        "- NaN check: passed",
        "- Infinite value check: passed",
        "- Label count check: passed",
        "",
        "## Thresholds Used",
        "",
    ]

    for key, value in _thresholds_payload().items():
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(
        [
            "",
            "## Feature Health Summary",
            "",
            f"- Total features: `{len(rows)}`",
            f"- Healthy features: `{status_counts.get('healthy', 0)}`",
            f"- Dead features: `{len(dead)}`",
            f"- Near-dead features: `{len(near_dead)}`",
            f"- Potentially noisy features: `{len(noisy)}`",
            f"- Highly correlated pairs: `{len(correlated_pairs)}`",
            "",
            "## Dead Features",
            "",
            *_feature_lines(dead),
            "",
            "## Near-Dead Features",
            "",
            *_feature_lines(near_dead),
            "",
            "## Potentially Noisy Features",
            "",
            *_feature_lines(noisy),
            "",
            "## Highly Correlated Feature Pairs",
            "",
            *_correlation_lines(correlated_pairs),
            "",
            "## Interpretation Notes",
            "",
            "- Dead and near-dead flags indicate weak observed variation in the current dataset, not automatic removal decisions.",
            "- Noisy flags are temporal stability warnings; they should be checked against video quality, pose jitter, and normalization choices.",
            "- High correlation can be legitimate when two biomechanical signals encode related movement, but it may reduce model efficiency.",
            "- Per-class mean and standard deviation values are included in the statistics CSV for class-separability review.",
            "",
            "## Recommendations",
            "",
        ]
    )

    lines.extend(f"- {item}" for item in recommendations)
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print("──────── validate_temporal_features (Phase 5.5 Step 5) ────────\n")

    try:
        X = _load_and_validate_tensor()
        feature_names, feature_to_group = _load_schema()
        if len(feature_names) != X.shape[2]:
            raise ValueError(
                f"Schema feature count {len(feature_names)} != tensor feature dim {X.shape[2]}."
            )
        labels = _load_labels(X.shape[0])

        rows = _compute_feature_rows(X, labels, feature_names, feature_to_group)
        correlated_pairs = _compute_high_correlations(X, feature_names)

        dead = [str(row["feature_name"]) for row in rows if row["health_status"] == "dead"]
        near_dead = [
            str(row["feature_name"]) for row in rows if row["health_status"] == "near_dead"
        ]
        noisy = [
            str(row["feature_name"]) for row in rows if row["health_status"] == "noisy"
        ]
        recommendations = _build_recommendations(
            dead, near_dead, noisy, correlated_pairs
        )

        _write_statistics_csv(rows)
        _write_health_json(rows, correlated_pairs, recommendations)
        _write_report(
            X=X,
            labels=labels,
            rows=rows,
            correlated_pairs=correlated_pairs,
            recommendations=recommendations,
        )

    except (OSError, ValueError, FileNotFoundError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    status_counts = Counter(str(row["health_status"]) for row in rows)
    print(f"X shape:                    {tuple(X.shape)}")
    print(f"Total features:             {len(rows)}")
    print(f"Healthy features:           {status_counts.get('healthy', 0)}")
    print(f"Dead features:              {status_counts.get('dead', 0)}")
    print(f"Near-dead features:         {status_counts.get('near_dead', 0)}")
    print(f"Potentially noisy features: {status_counts.get('noisy', 0)}")
    print(f"High correlation pairs:     {len(correlated_pairs)}")
    print("Output paths:")
    print(f"  - {REPORT_PATH}")
    print(f"  - {STATISTICS_CSV_PATH}")
    print(f"  - {HEALTH_JSON_PATH}")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
