"""Fast tests for one Phase 8 training/evaluation step."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import torch

from models.gru_classifier import GRUClassifier
from models.model_config import TemporalClassifierConfig
from training.temporal_dataset import TemporalCricketDataset, create_dataloader
from training.trainer import TemporalTrainer
from training.training_config import Phase8TrainingConfig


class TrainingStepTests(unittest.TestCase):
    def _trainer(self, tmp: str) -> tuple[TemporalTrainer, torch.utils.data.DataLoader]:
        rng = np.random.default_rng(5)
        X = rng.normal(size=(8, 60, 32)).astype(np.float32)
        y = np.array([0, 1, 2, 3, 0, 1, 2, 3], dtype=np.int64)
        dataset = TemporalCricketDataset(".", "train", X_override=X, y_override=y)
        loader = create_dataloader(dataset, batch_size=4, seed=5)
        model_config = TemporalClassifierConfig(hidden_size=8, num_layers=1, dropout=0.0)
        model = GRUClassifier(model_config)
        config = Phase8TrainingConfig(
            hidden_size=8,
            num_layers=1,
            dropout=0.0,
            max_epochs=1,
            batch_size=4,
            gradient_clip_norm=0.5,
            run_id="unit",
        )
        trainer = TemporalTrainer(
            model=model,
            model_name="bigru",
            config=config,
            device=torch.device("cpu"),
            class_names=["cover_drive", "defensive_shot", "pull_shot", "sweep_shot"],
            run_dir=Path(tmp),
            scaler_reference="unit",
            label_mapping={},
            dataset_version="unit",
            git_commit_sha="unit",
        )
        return trainer, loader

    def test_one_training_step_updates_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trainer, loader = self._trainer(tmp)
            optimizer = torch.optim.AdamW(trainer.model.parameters(), lr=1e-3)
            before = [p.detach().clone() for p in trainer.model.parameters()]
            stats = trainer.train_epoch(loader, optimizer)
            self.assertTrue(np.isfinite(stats["loss"]))
            after = list(trainer.model.parameters())
            self.assertTrue(any(not torch.equal(a, b) for a, b in zip(before, after)))

    def test_validation_no_grad_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trainer, loader = self._trainer(tmp)
            stats = trainer.evaluate_epoch(loader)
            self.assertTrue(np.isfinite(stats["loss"]))
            self.assertEqual(stats["logits"].shape, (8, 4))
            self.assertFalse(torch.is_grad_enabled() and trainer.model.training)

    def test_unknown_optimizer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trainer, _loader = self._trainer(tmp)
            trainer.config = replace(trainer.config, optimizer_name="AdmaTypo")
            with self.assertRaises(ValueError):
                trainer._make_optimizer()


if __name__ == "__main__":
    unittest.main()
