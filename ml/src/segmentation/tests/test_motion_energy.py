"""Tests for Phase 9 motion-energy extraction."""

from __future__ import annotations

import unittest

import numpy as np

from segmentation.motion_energy import compute_motion_energy_signal, moving_average, validate_feature_sequence


class MotionEnergyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.columns = [f"f{i}" for i in range(32)]
        self.columns[16] = "lead_wrist_velocity"
        self.columns[17] = "trail_wrist_velocity"
        self.columns[20] = "body_center_velocity"
        self.columns[23] = "frame_motion_energy"

    def test_motion_energy_is_finite_and_length_preserving(self) -> None:
        X = np.zeros((60, 32), dtype=np.float32)
        X[10:30, 16] = 2.0
        X[10:30, 23] = 4.0
        signal = compute_motion_energy_signal(X, self.columns)
        self.assertEqual(signal.smoothed_energy.shape, (60,))
        self.assertTrue(np.isfinite(signal.smoothed_energy).all())
        self.assertGreater(signal.smoothed_energy.max(), 0.9)

    def test_moving_average_preserves_length(self) -> None:
        values = np.array([0, 0, 1, 0, 0], dtype=float)
        smoothed = moving_average(values, 3)
        self.assertEqual(smoothed.shape, values.shape)
        self.assertGreater(smoothed[2], 0.0)

    def test_invalid_feature_sequence_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "rank-2"):
            validate_feature_sequence(np.zeros((1, 2, 3), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
