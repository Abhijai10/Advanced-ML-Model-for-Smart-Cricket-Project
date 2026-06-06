"""BiLSTM classifier for cricket shot motion sequences.

Cricket shots are temporal movements, so a BiLSTM can read pose-feature
sequences across stance, swing, and follow-through before classifying the shot.
"""

from __future__ import annotations

import torch
from torch import nn

from .model_config import DEFAULT_TEMPORAL_CONFIG, TemporalClassifierConfig


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
        if x.ndim != 3:
            raise ValueError(f"Expected input rank 3 [B, T, F], got shape {tuple(x.shape)}.")

        # LSTM output keeps one hidden representation per timestep.
        out, _hidden = self.lstm(x)

        # Use the final timestep representation for shot classification.
        last_timestep = out[:, -1, :]
        return self.classifier(last_timestep)
