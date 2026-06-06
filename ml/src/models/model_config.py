"""Phase 7 temporal model configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemporalClassifierConfig:
    """Configuration for Phase 7 temporal shot classifiers."""

    # Dataset/model contract: Phase 7 models consume rank-3 temporal sequences.
    # sequence_length and input_size are fixed by X_train_sequence: (56, 60, 32).
    sequence_length: int = 60
    input_size: int = 32

    # num_classes is fixed by the temporal label mapping: four shot categories.
    num_classes: int = 4

    # Architecture defaults for first GRU/BiLSTM experiments.
    hidden_size: int = 128
    num_layers: int = 2
    dropout: float = 0.2

    # Model behavior defaults for sequence encoders.
    gru_bidirectional: bool = True
    lstm_bidirectional: bool = True


DEFAULT_TEMPORAL_CONFIG = TemporalClassifierConfig()
