"""Training-only feature standardization for temporal tensors."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


class TemporalFeatureScaler:
    """Feature-wise standardization for tensors shaped [N, T, F]."""

    def __init__(self, epsilon: float = 1e-6) -> None:
        self.epsilon = float(epsilon)
        self.mean_: np.ndarray | None = None
        self.std_: np.ndarray | None = None

    def fit(self, X_train: np.ndarray) -> "TemporalFeatureScaler":
        self._validate_X(X_train)
        self.mean_ = X_train.mean(axis=(0, 1), dtype=np.float64).astype(np.float32)
        std = X_train.std(axis=(0, 1), dtype=np.float64).astype(np.float32)
        self.std_ = np.where(std < self.epsilon, 1.0, std).astype(np.float32)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        self._validate_X(X)
        if self.mean_ is None or self.std_ is None:
            raise ValueError("Scaler must be fitted before transform.")
        out = ((X.astype(np.float32, copy=False) - self.mean_[None, None, :]) / self.std_[None, None, :]).astype(np.float32)
        if not np.isfinite(out).all():
            raise ValueError("Transformed tensor contains non-finite values.")
        return out

    def fit_transform(self, X_train: np.ndarray) -> np.ndarray:
        return self.fit(X_train).transform(X_train)

    @staticmethod
    def _validate_X(X: np.ndarray) -> None:
        if X.ndim != 3:
            raise ValueError(f"Expected rank-3 tensor [N,T,F], got shape {X.shape}")
        if not np.isfinite(X).all():
            raise ValueError("Tensor contains non-finite values.")

    def save(self, directory: str | Path, metadata: dict[str, Any]) -> None:
        if self.mean_ is None or self.std_ is None:
            raise ValueError("Cannot save an unfitted scaler.")
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        np.save(path / "feature_mean.npy", self.mean_)
        np.save(path / "feature_std.npy", self.std_)
        payload = {
            "epsilon": self.epsilon,
            "mean_shape": list(self.mean_.shape),
            "std_shape": list(self.std_.shape),
            "fitting_split": "train",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            **metadata,
        }
        with (path / "scaler_metadata.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    @classmethod
    def load(cls, directory: str | Path) -> "TemporalFeatureScaler":
        path = Path(directory)
        with (path / "scaler_metadata.json").open(encoding="utf-8") as f:
            metadata = json.load(f)
        scaler = cls(epsilon=float(metadata.get("epsilon", 1e-6)))
        scaler.mean_ = np.load(path / "feature_mean.npy").astype(np.float32)
        scaler.std_ = np.load(path / "feature_std.npy").astype(np.float32)
        return scaler
