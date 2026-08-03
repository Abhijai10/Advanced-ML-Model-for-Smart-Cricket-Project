"""Tests for Phase 10 technique scoring."""

from __future__ import annotations

import unittest

import numpy as np

from scoring.score_config import COMPONENT_CONFIGS, EXPECTED_FEATURE_DIM, EXPECTED_SEQUENCE_LENGTH
from scoring.technique_scoring import build_ideal_templates, score_sequence


FEATURE_COLUMNS = [f"feature_{i}" for i in range(EXPECTED_FEATURE_DIM)]
for name, index in {
    "lead_elbow_angle": 0,
    "trail_elbow_angle": 1,
    "lead_knee_angle": 2,
    "trail_knee_angle": 3,
    "hip_rotation_angle": 7,
    "head_over_base_offset": 9,
    "head_to_lead_knee_alignment": 10,
    "shoulder_hip_separation": 11,
    "stance_width": 12,
    "body_center_offset_x": 13,
    "body_center_offset_y": 14,
    "upper_body_balance_offset": 15,
    "hip_rotation_velocity": 22,
    "front_foot_commitment_signal": 24,
    "weight_transfer_signal": 26,
    "follow_through_height_signal": 27,
    "follow_through_extension_signal": 28,
    "lead_elbow_extension_signal": 29,
    "bat_side_wrist_height_signal": 30,
    "stance_to_swing_progress_signal": 31,
}.items():
    FEATURE_COLUMNS[index] = name


class TechniqueScoringTests(unittest.TestCase):
    def _templates(self) -> dict:
        X = np.ones((56, EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM), dtype=np.float32) * 0.5
        y = np.repeat(np.arange(4), 14).astype(np.int64)
        import pandas as pd

        train_index = pd.DataFrame({"file_name": [f"sample_{i}.mov" for i in range(56)]})
        return build_ideal_templates(
            X,
            y,
            train_index,
            FEATURE_COLUMNS,
            ["cover_drive", "defensive_shot", "pull_shot", "sweep_shot"],
        )

    def test_component_weights_sum_to_one(self) -> None:
        self.assertAlmostEqual(sum(component.weight for component in COMPONENT_CONFIGS), 1.0)

    def test_score_sequence_returns_valid_score_range(self) -> None:
        templates = self._templates()
        sequence = np.ones((EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM), dtype=np.float32) * 0.5
        result = score_sequence(
            sequence,
            predicted_shot="cover_drive",
            feature_columns=FEATURE_COLUMNS,
            templates=templates,
            classifier_confidence=0.25,
        )
        self.assertGreaterEqual(result.technique_match_score, 0.0)
        self.assertLessEqual(result.technique_match_score, 100.0)
        self.assertEqual(result.classifier_confidence, 0.25)
        self.assertEqual(len(result.component_scores), len(COMPONENT_CONFIGS))

    def test_unknown_predicted_shot_fails(self) -> None:
        templates = self._templates()
        sequence = np.ones((EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM), dtype=np.float32)
        with self.assertRaises(ValueError):
            score_sequence(
                sequence,
                predicted_shot="reverse_sweep",
                feature_columns=FEATURE_COLUMNS,
                templates=templates,
            )

    def test_bad_sequence_shape_fails(self) -> None:
        templates = self._templates()
        with self.assertRaises(ValueError):
            score_sequence(
                np.ones((EXPECTED_SEQUENCE_LENGTH, EXPECTED_FEATURE_DIM + 1), dtype=np.float32),
                predicted_shot="cover_drive",
                feature_columns=FEATURE_COLUMNS,
                templates=templates,
            )


if __name__ == "__main__":
    unittest.main()
