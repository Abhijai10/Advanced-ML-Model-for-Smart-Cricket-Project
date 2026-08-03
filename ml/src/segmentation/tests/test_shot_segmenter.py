"""Tests for Phase 9 shot segmenter."""

from __future__ import annotations

import unittest

import numpy as np

from segmentation.shot_segmenter import ShotSegmenter


class ShotSegmenterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.columns = [f"f{i}" for i in range(32)]
        self.columns[16] = "lead_wrist_velocity"
        self.columns[17] = "trail_wrist_velocity"
        self.columns[20] = "body_center_velocity"
        self.columns[23] = "frame_motion_energy"

    def test_segmenter_detects_one_synthetic_shot(self) -> None:
        X = np.zeros((60, 32), dtype=np.float32)
        X[8:28, 16] = 1.0
        X[8:28, 23] = 3.0
        result = ShotSegmenter().segment_sequence(X, self.columns)
        self.assertIsNotNone(result.segment)
        assert result.segment is not None
        self.assertEqual(result.segment.trigger_count, 1)
        self.assertGreaterEqual(result.segment.end_frame, result.segment.start_frame)

    def test_no_motion_returns_no_segment_without_force_start(self) -> None:
        X = np.zeros((60, 32), dtype=np.float32)
        result = ShotSegmenter().segment_sequence(X, self.columns)
        self.assertIsNone(result.segment)


if __name__ == "__main__":
    unittest.main()
