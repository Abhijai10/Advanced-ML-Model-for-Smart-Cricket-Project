"""Tests for Phase 8 temporal Dataset/DataLoader helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from training.temporal_dataset import TemporalCricketDataset, create_dataloader


class TemporalDatasetTests(unittest.TestCase):
    def _make_dataset(self, X: np.ndarray | None = None, y: np.ndarray | None = None) -> TemporalCricketDataset:
        if X is None:
            X = np.zeros((4, 60, 32), dtype=np.float32)
        if y is None:
            y = np.array([0, 1, 2, 3], dtype=np.int64)
        return TemporalCricketDataset(".", "train", X_override=X, y_override=y)

    def test_sample_retrieval_shape_and_dtype(self) -> None:
        dataset = self._make_dataset()
        x, y = dataset[0]
        self.assertEqual(tuple(x.shape), (60, 32))
        self.assertEqual(x.dtype, torch.float32)
        self.assertEqual(y.dtype, torch.long)

    def test_dataloader_shuffle_is_train_only(self) -> None:
        dataset = self._make_dataset()
        loader = create_dataloader(dataset, batch_size=2, seed=42)
        batch_x, batch_y = next(iter(loader))
        self.assertEqual(tuple(batch_x.shape), (2, 60, 32))
        self.assertEqual(tuple(batch_y.shape), (2,))

    def test_invalid_rank_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "rank 3"):
            self._make_dataset(X=np.zeros((4, 32), dtype=np.float32))

    def test_label_range_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "labels must be"):
            self._make_dataset(y=np.array([0, 1, 2, 4], dtype=np.int64))

    def test_nan_failure(self) -> None:
        X = np.zeros((4, 60, 32), dtype=np.float32)
        X[0, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "NaN"):
            self._make_dataset(X=X)

    def test_missing_file_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                TemporalCricketDataset(Path(tmp), "train")


if __name__ == "__main__":
    unittest.main()
