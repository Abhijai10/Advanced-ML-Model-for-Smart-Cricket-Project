"""GRU classifier for cricket shot sequences.

Cricket shots unfold over time, so a temporal model can learn stance, swing,
and follow-through patterns from full pose-feature sequences.
"""

from __future__ import annotations

import torch
from torch import nn

from .model_config import DEFAULT_TEMPORAL_CONFIG, TemporalClassifierConfig


class GRUClassifier(nn.Module):
    """Phase 7 GRU classifier for inputs shaped [batch, time, features]."""

    def __init__(
        self,
        config: TemporalClassifierConfig = DEFAULT_TEMPORAL_CONFIG,
    ) -> None:
        super().__init__()
        self.config = config

        self.gru = nn.GRU(
            input_size=config.input_size,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            dropout=config.dropout,
            bidirectional=config.gru_bidirectional,
            batch_first=True,
        )

        directions = 2 if config.gru_bidirectional else 1
        self.classifier = nn.Linear(
            config.hidden_size * directions,
            config.num_classes,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return class logits for a batch of temporal cricket sequences."""
        if x.ndim != 3:
            raise ValueError(f"Expected input rank 3 [B, T, F], got shape {tuple(x.shape)}.")

        # GRU output keeps one hidden representation per timestep.
        out, _hidden = self.gru(x)

        # Use the final timestep representation for shot classification.
        last_timestep = out[:, -1, :]
        return self.classifier(last_timestep)
