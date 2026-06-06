"""Lightweight shape tests for the Phase 7 GRU classifier."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from models.gru_classifier import GRUClassifier  # noqa: E402
from models.model_config import TemporalClassifierConfig  # noqa: E402


class TestGRUClassifierShapes(unittest.TestCase):
    def test_bidirectional_gru_output_shape(self) -> None:
        config = TemporalClassifierConfig()
        model = GRUClassifier(config)
        x = torch.randn(4, config.sequence_length, config.input_size)

        logits = model(x)

        self.assertEqual(tuple(logits.shape), (4, config.num_classes))

    def test_unidirectional_gru_output_shape(self) -> None:
        config = TemporalClassifierConfig(gru_bidirectional=False)
        model = GRUClassifier(config)
        x = torch.randn(4, config.sequence_length, config.input_size)

        logits = model(x)

        self.assertEqual(tuple(logits.shape), (4, config.num_classes))

    def test_incorrect_tensor_rank_fails(self) -> None:
        config = TemporalClassifierConfig()
        model = GRUClassifier(config)
        bad_x = torch.randn(4, config.input_size)

        with self.assertRaises(ValueError):
            model(bad_x)


if __name__ == "__main__":
    unittest.main()
