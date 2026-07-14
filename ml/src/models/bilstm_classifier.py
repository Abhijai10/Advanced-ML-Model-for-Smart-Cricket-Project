"""BiLSTM classifier for cricket shot motion sequences.

Cricket shots are temporal movements, so a BiLSTM can read pose-feature
sequences across stance, swing, and follow-through before classifying the shot.
"""

from __future__ import annotations

import torch
from torch import nn

from .model_config import DEFAULT_TEMPORAL_CONFIG, TemporalClassifierConfig
from .model_utils import validate_sequence_input


class BiLSTMClassifier(nn.Module):
    """Phase 7 BiLSTM classifier for inputs shaped [batch, time, features]."""

    def __init__(
        self,
        config: TemporalClassifierConfig = DEFAULT_TEMPORAL_CONFIG,
    ) -> None:
        super().__init__()
        if not config.lstm_bidirectional:
            raise ValueError("BiLSTMClassifier requires config.lstm_bidirectional=True.")

        self.config = config
        self.lstm = nn.LSTM(
            input_size=config.input_size,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            dropout=config.dropout,
            bidirectional=True,
            batch_first=True,
        )

        self.classifier = nn.Linear(
            config.hidden_size * 2,
            config.num_classes,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return class logits for a batch of temporal cricket sequences."""
        validate_sequence_input(x, self.config.sequence_length, self.config.input_size)

        _out, (h_n, _c_n) = self.lstm(x)

        # h_n layout is [num_layers * num_directions, batch, hidden_size].
        # BiLSTM is always bidirectional here: -2 is forward and -1 is backward.
        final_forward = h_n[-2]
        final_backward = h_n[-1]
        readout = torch.cat((final_forward, final_backward), dim=1)
        return self.classifier(readout)
