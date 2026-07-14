"""Small shared utilities for Phase 7 temporal model architecture checks."""

from __future__ import annotations

from typing import Any

import torch


def count_parameters(model: Any, trainable_only: bool = True) -> int:
    """Return the number of model parameters."""
    params = model.parameters()
    if trainable_only:
        return sum(p.numel() for p in params if p.requires_grad)
    return sum(p.numel() for p in params)


def validate_sequence_input(x: Any, sequence_length: int, input_size: int) -> None:
    """Validate rank-3 sequence input shaped [B, T, F]."""
    if not isinstance(x, torch.Tensor):
        raise ValueError(f"Expected torch.Tensor input, got {type(x).__name__}.")
    if x.ndim != 3:
        raise ValueError(f"Expected rank-3 input [B, T, F], got shape {tuple(x.shape)}.")
    if x.shape[0] <= 0:
        raise ValueError(f"Expected non-empty batch dimension, got shape {tuple(x.shape)}.")
    if x.shape[1] != sequence_length:
        raise ValueError(
            f"Expected sequence length {sequence_length}, got {x.shape[1]} "
            f"for shape {tuple(x.shape)}."
        )
    if x.shape[2] != input_size:
        raise ValueError(
            f"Expected input size {input_size}, got {x.shape[2]} "
            f"for shape {tuple(x.shape)}."
        )
    if not torch.is_floating_point(x):
        raise ValueError(f"Expected floating-point tensor, got dtype {x.dtype}.")
    if not torch.isfinite(x).all():
        raise ValueError(f"Expected finite tensor values for shape {tuple(x.shape)}.")


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
