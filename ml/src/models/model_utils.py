"""Small shared utilities for Phase 7 temporal model architecture checks."""

from __future__ import annotations

from typing import Any


def count_parameters(model: Any, trainable_only: bool = True) -> int:
    """Return the number of model parameters."""
    params = model.parameters()
    if trainable_only:
        return sum(p.numel() for p in params if p.requires_grad)
    return sum(p.numel() for p in params)


def validate_sequence_input(x: Any, sequence_length: int, input_size: int) -> None:
    """Validate rank-3 sequence input shaped [B, T, F]."""
    if x.ndim != 3:
        raise ValueError(f"Expected rank-3 input [B, T, F], got shape {tuple(x.shape)}.")
    if x.shape[1] != sequence_length:
        raise ValueError(
            f"Expected sequence length {sequence_length}, got {x.shape[1]}."
        )
    if x.shape[2] != input_size:
        raise ValueError(f"Expected input size {input_size}, got {x.shape[2]}.")


def summarize_model(model: Any, config: Any, model_name: str) -> dict[str, int | str]:
    """Return a compact architecture summary dictionary."""
    return {
        "model_name": model_name,
        "trainable_parameters": count_parameters(model, trainable_only=True),
        "total_parameters": count_parameters(model, trainable_only=False),
        "sequence_length": config.sequence_length,
        "input_size": config.input_size,
        "num_classes": config.num_classes,
    }
