"""Tests for Phase 11 feedback generation."""

from __future__ import annotations

import unittest

from feedback.feedback_engine import generate_feedback_for_sample
from feedback.feedback_rules import direction_text, severity_from_score


def _sample() -> dict:
    return {
        "file_name": "cover_drive_test.mov",
        "true_label_name": "cover_drive",
        "prediction_correct": True,
        "score_result": {
            "technique_match_score": 68.5,
            "predicted_shot": "cover_drive",
            "classifier_confidence": 0.91,
            "component_scores": {
                "head_stability_score": {
                    "score": 40.0,
                    "deviations": [
                        {
                            "feature_name": "head_over_base_offset",
                            "statistic": "abs_mean",
                            "actual_value": 0.35,
                            "expected_low": 0.1,
                            "expected_high": 0.2,
                            "deviation": 0.15,
                            "score": 20.0,
                        }
                    ],
                },
                "follow_through_score": {
                    "score": 92.0,
                    "deviations": [
                        {
                            "feature_name": "follow_through_extension_signal",
                            "statistic": "final_mean",
                            "actual_value": 1.0,
                            "expected_low": 0.8,
                            "expected_high": 1.2,
                            "deviation": 0.0,
                            "score": 100.0,
                        }
                    ],
                },
            },
        },
    }


class FeedbackEngineTests(unittest.TestCase):
    def test_severity_from_score(self) -> None:
        self.assertEqual(severity_from_score(20.0), "high")
        self.assertEqual(severity_from_score(50.0), "medium")
        self.assertEqual(severity_from_score(70.0), "low")

    def test_direction_text(self) -> None:
        self.assertEqual(direction_text(0.1, 0.2, 0.4), "below")
        self.assertEqual(direction_text(0.5, 0.2, 0.4), "above")
        self.assertEqual(direction_text(0.3, 0.2, 0.4), "inside")

    def test_feedback_contains_required_layers(self) -> None:
        output = generate_feedback_for_sample(_sample())
        self.assertEqual(output.predicted_shot, "cover_drive")
        self.assertTrue(output.detected_issues)
        self.assertTrue(output.coaching_tips)
        self.assertIn("68.5/100", output.detailed_feedback)
        self.assertIn("out of 100", output.spoken_feedback)
        self.assertTrue(output.debug_metadata)

    def test_high_score_without_issues_uses_maintenance_tip(self) -> None:
        sample = _sample()
        sample["score_result"]["technique_match_score"] = 96.0
        for component in sample["score_result"]["component_scores"].values():
            component["score"] = 96.0
            for deviation in component["deviations"]:
                deviation["score"] = 100.0
                deviation["deviation"] = 0.0
        output = generate_feedback_for_sample(sample)
        self.assertFalse(output.detected_issues)
        self.assertIn("Maintain this movement pattern", output.coaching_tips[0])

    def test_prediction_correct_string_false_is_parsed(self) -> None:
        sample = _sample()
        sample["prediction_correct"] = "False"
        output = generate_feedback_for_sample(sample)
        self.assertFalse(output.debug_metadata["prediction_correct"])


if __name__ == "__main__":
    unittest.main()
