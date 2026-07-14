"""Tests for Phase 8 classification metrics."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from training.metrics import compute_classification_metrics, load_class_names


CLASS_NAMES = ["cover_drive", "defensive_shot", "pull_shot", "sweep_shot"]


class MetricsTests(unittest.TestCase):
    def test_perfect_predictions(self) -> None:
        y = np.array([0, 1, 2, 3])
        metrics = compute_classification_metrics(y, y, CLASS_NAMES)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["macro_f1"], 1.0)
        self.assertEqual(np.asarray(metrics["confusion_matrix"]).shape, (4, 4))

    def test_mixed_predictions(self) -> None:
        metrics = compute_classification_metrics(
            np.array([0, 1, 2, 3]),
            np.array([0, 1, 1, 3]),
            CLASS_NAMES,
        )
        self.assertLess(metrics["macro_f1"], 1.0)
        self.assertEqual(metrics["per_class"]["pull_shot"]["recall"], 0.0)

    def test_absent_predicted_class(self) -> None:
        metrics = compute_classification_metrics(
            np.array([0, 1, 2, 3]),
            np.array([0, 0, 0, 0]),
            CLASS_NAMES,
        )
        self.assertEqual(metrics["per_class"]["sweep_shot"]["precision"], 0.0)
        self.assertEqual(np.asarray(metrics["confusion_matrix"]).shape, (4, 4))

    def test_class_name_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mapping.json"
            path.write_text(
                json.dumps({"index_to_class": {str(i): name for i, name in enumerate(CLASS_NAMES)}}),
                encoding="utf-8",
            )
            self.assertEqual(load_class_names(path), CLASS_NAMES)


if __name__ == "__main__":
    unittest.main()
