"""Tests for checkpoint save/load helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from training.checkpointing import load_checkpoint, save_checkpoint


class CheckpointingTests(unittest.TestCase):
    def test_save_load_round_trip_and_state_restore(self) -> None:
        model = torch.nn.Linear(3, 2)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "best.pt"
            payload = {
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "model_name": "unit",
                "epoch": 2,
                "best_metric": 0.75,
                "metadata": {"seed": 42},
            }
            save_checkpoint(path, payload)
            loaded = load_checkpoint(path)
            self.assertEqual(loaded["epoch"], 2)
            self.assertEqual(loaded["metadata"]["seed"], 42)
            restored = torch.nn.Linear(3, 2)
            restored.load_state_dict(loaded["model_state_dict"])
            for a, b in zip(model.parameters(), restored.parameters()):
                self.assertTrue(torch.equal(a, b))

    def test_missing_checkpoint_failure(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_checkpoint("/tmp/does-not-exist-phase8.pt")

    def test_best_model_checkpoint_loads_with_safe_weights_only_mode(self) -> None:
        path = Path("ml/artifacts/phase8/best_model/checkpoint.pt")
        loaded = load_checkpoint(path)
        self.assertEqual(loaded["model_name"], "bigru")
        self.assertIn("model_state_dict", loaded)


if __name__ == "__main__":
    unittest.main()
