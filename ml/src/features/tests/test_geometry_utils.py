"""Regression tests for geometry utility statistics."""

from __future__ import annotations

import unittest

from features.geometry_utils import safe_circular_mean_degrees


class GeometryUtilsTests(unittest.TestCase):
    def test_circular_mean_handles_angle_wraparound(self) -> None:
        mean = safe_circular_mean_degrees([179.0, -179.0])
        self.assertTrue(abs(abs(mean) - 180.0) < 1e-6)

    def test_circular_mean_ignores_invalid_values(self) -> None:
        self.assertEqual(safe_circular_mean_degrees([None, float("nan")]), 0.0)


if __name__ == "__main__":
    unittest.main()
