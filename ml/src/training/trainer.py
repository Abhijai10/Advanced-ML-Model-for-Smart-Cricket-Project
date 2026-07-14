"""Reusable supervised trainer for Phase 8 temporal classifiers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from .checkpointing import EarlyStopping, save_checkpoint
from .metrics import compute_classification_metrics


def _current_lr(optimizer: torch.optim.Optimizer) -> float:
    return float(optimizer.param_groups[0]["lr"])


class TemporalTrainer:
    """Train and validate a temporal classifier."""

    def __init__(
        self,
        *,
        model: nn.Module,
        model_name: str,
        config: Any,
        device: torch.device,
        class_names: list[str],
        run_dir: Path,
        scaler_reference: str,
        label_mapping: dict[str, Any],
        dataset_version: str,
        git_commit_sha: str,
    ) -> None:
        self.model = model.to(device)
        self.model_name = model_name
        self.config = config
        self.device = device
        self.class_names = class_names
        self.run_dir = run_dir
        self.scaler_reference = scaler_reference
        self.label_mapping = label_mapping
        self.dataset_version = dataset_version
        self.git_commit_sha = git_commit_sha
        self.criterion = nn.CrossEntropyLoss()

    def train(
        self,
        train_loader: torch.utils.data.DataLoader,
        val_loader: torch.utils.data.DataLoader,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        optimizer = self._make_optimizer()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="max", factor=0.5, patience=4
        )
        stopper = EarlyStopping(
            self.config.early_stopping_patience,
            self.config.min_improvement_delta,
            self.config.checkpoint_mode,
        )

        history: list[dict[str, Any]] = []
        best_payload: dict[str, Any] | None = None
        best_path = self.run_dir / "checkpoints" / "best.pt"
        final_path = self.run_dir / "checkpoints" / "final.pt"

        for epoch in range(1, self.config.max_epochs + 1):
            start = time.time()
            train_stats = self.train_epoch(train_loader, optimizer)
            val_stats = self.evaluate_epoch(val_loader)
            val_metrics = compute_classification_metrics(
                val_stats["labels"], val_stats["predictions"], self.class_names
            )
            checkpoint_value = float(val_metrics["macro_f1"])
            improved, should_stop = stopper.update(checkpoint_value, epoch)
            scheduler.step(checkpoint_value)

            row = {
                "epoch": epoch,
                "training_loss": train_stats["loss"],
                "validation_loss": val_stats["loss"],
                "training_accuracy": train_stats["accuracy"],
                "validation_accuracy": val_metrics["accuracy"],
                "validation_macro_f1": val_metrics["macro_f1"],
                "learning_rate": _current_lr(optimizer),
                "epoch_duration": time.time() - start,
                "best_checkpoint": improved,
            }
            history.append(row)

            payload = self._checkpoint_payload(
                optimizer=optimizer,
                scheduler=scheduler,
                epoch=epoch,
                best_metric=stopper.best_value if stopper.best_value is not None else checkpoint_value,
                history=history,
            )
            if improved:
                best_payload = payload
                save_checkpoint(best_path, payload)
            if should_stop:
                break

        if best_payload is None:
            raise RuntimeError("No best checkpoint was saved.")
        save_checkpoint(final_path, self._checkpoint_payload(
            optimizer=optimizer,
            scheduler=scheduler,
            epoch=history[-1]["epoch"],
            best_metric=float(best_payload["best_metric"]),
            history=history,
        ))
        return history, best_payload

    def _make_optimizer(self) -> torch.optim.Optimizer:
        if self.config.optimizer_name.lower() == "adamw":
            return torch.optim.AdamW(
                self.model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
            )
        return torch.optim.Adam(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

    def train_epoch(
        self,
        loader: torch.utils.data.DataLoader,
        optimizer: torch.optim.Optimizer,
    ) -> dict[str, float]:
        if len(loader.dataset) == 0:
            raise ValueError("Empty training DataLoader.")
        self.model.train()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        for x, y in loader:
            x, y = x.to(self.device), y.to(self.device)
            optimizer.zero_grad(set_to_none=True)
            logits = self.model(x)
            if logits.shape != (x.shape[0], self.config.num_classes):
                raise ValueError(f"Invalid model output shape {tuple(logits.shape)}")
            loss = self.criterion(logits, y)
            if not torch.isfinite(loss):
                raise RuntimeError(f"Non-finite training loss: {loss.item()}")
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(
                self.model.parameters(), self.config.gradient_clip_norm
            )
            if not torch.isfinite(grad_norm):
                raise RuntimeError(f"Non-finite gradient norm: {grad_norm}")
            optimizer.step()
            batch_size = int(y.shape[0])
            total_loss += float(loss.item()) * batch_size
            total_correct += int((logits.argmax(dim=1) == y).sum().item())
            total_samples += batch_size
        return {
            "loss": total_loss / total_samples,
            "accuracy": total_correct / total_samples,
        }

    def evaluate_epoch(self, loader: torch.utils.data.DataLoader) -> dict[str, Any]:
        if len(loader.dataset) == 0:
            raise ValueError("Empty evaluation DataLoader.")
        self.model.eval()
        total_loss = 0.0
        total_samples = 0
        labels: list[int] = []
        predictions: list[int] = []
        logits_out: list[np.ndarray] = []
        with torch.no_grad():
            for x, y in loader:
                x, y = x.to(self.device), y.to(self.device)
                logits = self.model(x)
                if logits.shape != (x.shape[0], self.config.num_classes):
                    raise ValueError(f"Invalid model output shape {tuple(logits.shape)}")
                loss = self.criterion(logits, y)
                if not torch.isfinite(loss):
                    raise RuntimeError(f"Non-finite evaluation loss: {loss.item()}")
                batch_size = int(y.shape[0])
                total_loss += float(loss.item()) * batch_size
                total_samples += batch_size
                pred = logits.argmax(dim=1)
                labels.extend(y.cpu().numpy().astype(int).tolist())
                predictions.extend(pred.cpu().numpy().astype(int).tolist())
                logits_out.append(logits.cpu().numpy())
        return {
            "loss": total_loss / total_samples,
            "labels": np.asarray(labels, dtype=np.int64),
            "predictions": np.asarray(predictions, dtype=np.int64),
            "logits": np.concatenate(logits_out, axis=0),
        }

    def _checkpoint_payload(
        self,
        *,
        optimizer: torch.optim.Optimizer,
        scheduler: Any,
        epoch: int,
        best_metric: float,
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
            "model_config": self.config.to_dict(),
            "training_config": self.config.to_dict(),
            "epoch": int(epoch),
            "best_metric": float(best_metric),
            "feature_scaler_reference": self.scaler_reference,
            "label_mapping": self.label_mapping,
            "dataset_version": self.dataset_version,
            "random_seed": self.config.random_seed,
            "training_history_summary": history[-1] if history else {},
            "model_name": self.model_name,
            "recurrent_directionality": "bidirectional" if self.config.bidirectional else "unidirectional",
            "git_commit_sha": self.git_commit_sha,
        }
