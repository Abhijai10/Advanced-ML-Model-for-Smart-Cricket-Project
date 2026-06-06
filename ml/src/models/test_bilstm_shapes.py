"""Lightweight shape tests for the Phase 7 BiLSTM classifier."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from models.bilstm_classifier import BiLSTMClassifier  # noqa: E402
from models.model_config import TemporalClassifierConfig  # noqa: E402


class TestBiLSTMClassifierShapes(unittest.TestCase):
    def test_bilstm_output_shape(self) -> None:
        config = TemporalClassifierConfig()
        model = BiLSTMClassifier(config)
        x = torch.randn(4, config.sequence_length, config.input_size)

        logits = model(x)

        self.assertEqual(tuple(logits.shape), (4, config.num_classes))

    def test_disabling_bidirectional_lstm_fails(self) -> None:
        config = TemporalClassifierConfig(lstm_bidirectional=False)

        with self.assertRaises(ValueError):
            BiLSTMClassifier(config)

    def test_incorrect_tensor_rank_fails(self) -> None:
        config = TemporalClassifierConfig()
        model = BiLSTMClassifier(config)
        bad_x = torch.randn(4, config.input_size)

        with self.assertRaises(ValueError):
            model(bad_x)


if __name__ == "__main__":
    unittest.main()
