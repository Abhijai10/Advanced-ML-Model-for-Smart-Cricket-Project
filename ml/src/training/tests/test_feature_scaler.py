"""Tests for train-only temporal feature standardization."""

from __future__ import annotations

import tempfile
import unittest

import numpy as np

from training.feature_scaler import TemporalFeatureScaler


class TemporalFeatureScalerTests(unittest.TestCase):
    def test_fit_transform_standardizes_training_features(self) -> None:
        X_train = np.arange(4 * 60 * 3, dtype=np.float32).reshape(4, 60, 3)
        scaler = TemporalFeatureScaler()
        out = scaler.fit_transform(X_train)
        self.assertEqual(tuple(scaler.mean_.shape), (3,))
        np.testing.assert_allclose(out.mean(axis=(0, 1)), np.zeros(3), atol=1e-6)
        np.testing.assert_allclose(out.std(axis=(0, 1)), np.ones(3), atol=1e-6)

    def test_validation_transform_does_not_refit(self) -> None:
        X_train = np.ones((2, 60, 2), dtype=np.float32)
        X_val = np.full((2, 60, 2), 3.0, dtype=np.float32)
        scaler = TemporalFeatureScaler().fit(X_train)
        original_mean = scaler.mean_.copy()
        _ = scaler.transform(X_val)
        np.testing.assert_array_equal(scaler.mean_, original_mean)

    def test_zero_variance_handling(self) -> None:
        X_train = np.ones((2, 60, 2), dtype=np.float32)
        scaler = TemporalFeatureScaler().fit(X_train)
        np.testing.assert_array_equal(scaler.std_, np.ones(2, dtype=np.float32))
        np.testing.assert_array_equal(scaler.transform(X_train), np.zeros_like(X_train))

    def test_save_load_round_trip(self) -> None:
        X_train = np.random.default_rng(1).normal(size=(3, 60, 4)).astype(np.float32)
        scaler = TemporalFeatureScaler().fit(X_train)
        with tempfile.TemporaryDirectory() as tmp:
            scaler.save(tmp, {"dataset_version": "test"})
            loaded = TemporalFeatureScaler.load(tmp)
            np.testing.assert_array_equal(loaded.mean_, scaler.mean_)
            np.testing.assert_array_equal(loaded.std_, scaler.std_)

    def test_invalid_rank_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "rank-3"):
            TemporalFeatureScaler().fit(np.zeros((3, 2), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
