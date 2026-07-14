"""Checkpoint save/load helpers for Phase 8 models."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import torch


def save_checkpoint(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        torch.save(payload, tmp_path)
        os.replace(tmp_path, path)
    except OSError as e:
        raise OSError(f"Failed to save checkpoint to {path}: {e}") from e
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def load_checkpoint(path: str | Path, map_location: str | torch.device = "cpu") -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {path}")
    payload = torch.load(path, map_location=map_location, weights_only=False)
    if not isinstance(payload, dict):
        raise ValueError(f"Checkpoint payload must be a dict: {path}")
    for key in ("model_state_dict", "model_name", "epoch", "best_metric"):
        if key not in payload:
            raise ValueError(f"Checkpoint missing required key {key!r}: {path}")
    return payload


class EarlyStopping:
    """Validation-metric early stopping state."""

    def __init__(self, patience: int, min_delta: float, mode: str) -> None:
        if mode not in ("max", "min"):
            raise ValueError("mode must be 'max' or 'min'")
        self.patience = int(patience)
        self.min_delta = float(min_delta)
        self.mode = mode
        self.best_value: float | None = None
        self.best_epoch: int = 0
        self.bad_epochs = 0

    def update(self, value: float, epoch: int) -> tuple[bool, bool]:
        improved = False
        if self.best_value is None:
            improved = True
        elif self.mode == "max":
            improved = value > self.best_value + self.min_delta
        else:
            improved = value < self.best_value - self.min_delta

        if improved:
            self.best_value = float(value)
            self.best_epoch = int(epoch)
            self.bad_epochs = 0
        else:
            self.bad_epochs += 1
        return improved, self.bad_epochs >= self.patience
