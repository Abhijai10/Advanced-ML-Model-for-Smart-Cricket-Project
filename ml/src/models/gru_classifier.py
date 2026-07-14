"""GRU classifier for cricket shot sequences.

Cricket shots unfold over time, so a temporal model can learn stance, swing,
and follow-through patterns from full pose-feature sequences.
"""

from __future__ import annotations

import torch
from torch import nn

from .model_config import DEFAULT_TEMPORAL_CONFIG, TemporalClassifierConfig
from .model_utils import validate_sequence_input


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
        validate_sequence_input(x, self.config.sequence_length, self.config.input_size)

        _out, h_n = self.gru(x)

        # h_n layout is [num_layers * num_directions, batch, hidden_size].
        # For a bidirectional final layer, -2 is forward and -1 is backward.
        if self.config.gru_bidirectional:
            final_forward = h_n[-2]
            final_backward = h_n[-1]
            readout = torch.cat((final_forward, final_backward), dim=1)
        else:
            # For a unidirectional GRU, -1 is the final layer's final hidden state.
            readout = h_n[-1]

        return self.classifier(readout)
