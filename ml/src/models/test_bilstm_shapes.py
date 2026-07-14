"""Lightweight shape tests for the Phase 7 BiLSTM classifier."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch
from torch import nn

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from models.bilstm_classifier import BiLSTMClassifier  # noqa: E402
from models.model_config import TemporalClassifierConfig  # noqa: E402


class FakeLSTM(nn.Module):
    """Return controlled output and hidden state for readout semantics tests."""

    def __init__(self, config: TemporalClassifierConfig) -> None:
        super().__init__()
        self.config = config

    def forward(
        self,
        x: torch.Tensor,
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        batch = x.shape[0]
        out = torch.full(
            (batch, self.config.sequence_length, self.config.hidden_size * 2),
            -99.0,
            dtype=x.dtype,
            device=x.device,
        )
        h_n = torch.zeros(
            self.config.num_layers * 2,
            batch,
            self.config.hidden_size,
            dtype=x.dtype,
            device=x.device,
        )
        c_n = torch.zeros_like(h_n)
        h_n[-2] = 11.0
        h_n[-1] = 13.0
        return out, (h_n, c_n)


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

    def test_multi_layer_hidden_state_readout_works(self) -> None:
        config = TemporalClassifierConfig(num_layers=3)
        model = BiLSTMClassifier(config)
        x = torch.randn(4, config.sequence_length, config.input_size)

        logits = model(x)

        self.assertEqual(tuple(logits.shape), (4, config.num_classes))

    def test_incorrect_sequence_length_fails(self) -> None:
        config = TemporalClassifierConfig()
        model = BiLSTMClassifier(config)
        bad_x = torch.randn(4, config.sequence_length - 1, config.input_size)

        with self.assertRaises(ValueError):
            model(bad_x)

    def test_incorrect_feature_dimension_fails(self) -> None:
        config = TemporalClassifierConfig()
        model = BiLSTMClassifier(config)
        bad_x = torch.randn(4, config.sequence_length, config.input_size + 1)

        with self.assertRaises(ValueError):
            model(bad_x)

    def test_non_floating_input_fails(self) -> None:
        config = TemporalClassifierConfig()
        model = BiLSTMClassifier(config)
        bad_x = torch.ones(4, config.sequence_length, config.input_size, dtype=torch.long)

        with self.assertRaises(ValueError):
            model(bad_x)

    def test_non_finite_input_fails(self) -> None:
        config = TemporalClassifierConfig()
        model = BiLSTMClassifier(config)
        bad_x = torch.randn(4, config.sequence_length, config.input_size)
        bad_x[0, 0, 0] = float("nan")

        with self.assertRaises(ValueError):
            model(bad_x)

    def test_classifier_uses_hidden_states_not_last_output(self) -> None:
        config = TemporalClassifierConfig(hidden_size=2, num_layers=2)
        model = BiLSTMClassifier(config)
        model.lstm = FakeLSTM(config)
        model.classifier = nn.Identity()
        x = torch.randn(4, config.sequence_length, config.input_size)

        readout = model(x)

        expected = torch.tensor([11.0, 11.0, 13.0, 13.0]).repeat(4, 1)
        self.assertTrue(torch.equal(readout, expected))


if __name__ == "__main__":
    unittest.main()
