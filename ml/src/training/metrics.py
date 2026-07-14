"""Metric computation for temporal shot classification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support


def load_class_names(label_mapping_path: str | Path) -> list[str]:
    with Path(label_mapping_path).open(encoding="utf-8") as f:
        mapping = json.load(f)
    index_to_class = mapping.get("index_to_class")
    if not isinstance(index_to_class, dict):
        raise ValueError("label mapping missing index_to_class")
    return [str(index_to_class[str(i)]) for i in sorted(int(k) for k in index_to_class)]


def _plain_float(value: float) -> float:
    return float(value)


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str],
) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=np.int64)
    y_pred = np.asarray(y_pred, dtype=np.int64)
    labels = list(range(len(class_names)))
    if y_true.shape != y_pred.shape:
        raise ValueError(f"y_true shape {y_true.shape} != y_pred shape {y_pred.shape}")

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    accuracy = float(np.mean(y_true == y_pred)) if y_true.size else 0.0
    macro = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="macro", zero_division=0
    )
    weighted = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="weighted", zero_division=0
    )
    per = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )

    per_class: dict[str, dict[str, float | int]] = {}
    for i, name in enumerate(class_names):
        support = int(per[3][i])
        class_total = int(cm[i, :].sum())
        per_class[name] = {
            "precision": _plain_float(per[0][i]),
            "recall": _plain_float(per[1][i]),
            "f1": _plain_float(per[2][i]),
            "support": support,
            "accuracy": _plain_float(cm[i, i] / class_total) if class_total else 0.0,
        }

    return {
        "accuracy": accuracy,
        "macro_precision": _plain_float(macro[0]),
        "macro_recall": _plain_float(macro[1]),
        "macro_f1": _plain_float(macro[2]),
        "weighted_precision": _plain_float(weighted[0]),
        "weighted_recall": _plain_float(weighted[1]),
        "weighted_f1": _plain_float(weighted[2]),
        "per_class": per_class,
        "confusion_matrix": cm.astype(int).tolist(),
        "class_names": class_names,
    }


def save_metrics(path: str | Path, metrics: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
