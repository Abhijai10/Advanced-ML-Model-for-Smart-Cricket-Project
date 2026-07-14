"""PyTorch Dataset and DataLoader helpers for temporal Smart Cricket tensors."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset


SPLIT_FILES = {
    "train": ("X_train_sequence.npy", "y_train_sequence.npy"),
    "validation": ("X_val_sequence.npy", "y_val_sequence.npy"),
    "test": ("X_test_sequence.npy", "y_test_sequence.npy"),
}


class TemporalCricketDataset(Dataset):
    """Dataset for one temporal split."""

    def __init__(
        self,
        dataset_dir: str | Path,
        split: str,
        *,
        sequence_length: int = 60,
        input_size: int = 32,
        num_classes: int = 4,
        X_override: np.ndarray | None = None,
        y_override: np.ndarray | None = None,
    ) -> None:
        if split not in SPLIT_FILES:
            raise ValueError(f"Unknown split {split!r}; expected one of {sorted(SPLIT_FILES)}")
        self.dataset_dir = Path(dataset_dir)
        self.split = split
        x_name, y_name = SPLIT_FILES[split]

        X = X_override if X_override is not None else np.load(self._required_path(x_name))
        y = y_override if y_override is not None else np.load(self._required_path(y_name))
        self._validate_arrays(X, y, sequence_length, input_size, num_classes)

        self.X = torch.as_tensor(X.astype(np.float32, copy=False), dtype=torch.float32)
        self.y = torch.as_tensor(y.astype(np.int64, copy=False), dtype=torch.long)
        self.metadata = {
            "split": split,
            "num_samples": int(self.X.shape[0]),
            "sequence_length": int(self.X.shape[1]),
            "input_size": int(self.X.shape[2]),
        }

    def _required_path(self, filename: str) -> Path:
        path = self.dataset_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing temporal split file: {path}")
        return path

    @staticmethod
    def _validate_arrays(
        X: np.ndarray,
        y: np.ndarray,
        sequence_length: int,
        input_size: int,
        num_classes: int,
    ) -> None:
        if X.ndim != 3:
            raise ValueError(f"X must be rank 3 [N,T,F], got shape {X.shape}")
        if y.ndim != 1:
            raise ValueError(f"y must be rank 1 [N], got shape {y.shape}")
        if X.shape[0] != y.shape[0]:
            raise ValueError(f"X samples {X.shape[0]} != y labels {y.shape[0]}")
        if X.shape[1] != sequence_length:
            raise ValueError(f"Expected sequence length {sequence_length}, got {X.shape[1]}")
        if X.shape[2] != input_size:
            raise ValueError(f"Expected feature dimension {input_size}, got {X.shape[2]}")
        if not np.isfinite(X).all():
            raise ValueError("X contains NaN or infinite values")
        if not np.issubdtype(y.dtype, np.integer):
            raise ValueError(f"y must be integer-compatible, got dtype {y.dtype}")
        if y.size and (int(y.min()) < 0 or int(y.max()) >= num_classes):
            raise ValueError(f"y labels must be in [0, {num_classes - 1}]")

    def __len__(self) -> int:
        return int(self.X.shape[0])

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.X[index], self.y[index]


def create_dataloader(
    dataset: TemporalCricketDataset,
    *,
    batch_size: int,
    seed: int,
    num_workers: int = 0,
) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=dataset.split == "train",
        num_workers=num_workers,
        generator=generator,
    )
