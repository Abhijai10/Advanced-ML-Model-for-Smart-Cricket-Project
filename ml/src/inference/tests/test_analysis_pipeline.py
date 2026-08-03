"""Tests for Phase 12 offline inference pipeline."""

from __future__ import annotations

import unittest

import numpy as np

from inference.analysis_pipeline import analyze_sequence, load_dataset_sequence
from inference.inference_config import EXPECTED_FEATURE_DIM, EXPECTED_SEQUENCE_LENGTH


class AnalysisPipelineTests(unittest.TestCase):
    def test_dataset_sample_produces_complete_result(self) -> None:
        sequence, metadata = load_dataset_sequence(sample_index=1)
        result = analyze_sequence(sequence, metadata).to_dict()
        self.assertIn("predicted_shot", result)
        self.assertIn("technique_match_score", result)
        self.assertIn("spoken_feedback", result)
        self.assertTrue(result["spoken_feedback"])
        self.assertGreaterEqual(result["shot_confidence"], 0.0)
        self.assertLessEqual(result["shot_confidence"], 1.0)
        self.assertGreaterEqual(result["technique_match_score"], 0.0)
        self.assertLessEqual(result["technique_match_score"], 100.0)

    def test_bad_sequence_shape_fails(self) -> None:
        bad = np.zeros((EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM + 1), dtype=np.float32)
        with self.assertRaises(ValueError):
            analyze_sequence(bad, {"file_name": "bad.npy"})

    def test_unknown_file_name_fails(self) -> None:
        with self.assertRaises(ValueError):
            load_dataset_sequence(file_name="not_in_dataset.mov")


if __name__ == "__main__":
    unittest.main()
