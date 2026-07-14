"""Tiny orchestration smoke test for Phase 8 run setup."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from training.train_temporal_models import run_single_experiment
from training.training_config import DEFAULT_PHASE8_CONFIG


class ExperimentSmokeTests(unittest.TestCase):
    def test_short_smoke_experiment_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = DEFAULT_PHASE8_CONFIG.__class__(
                **{
                    **DEFAULT_PHASE8_CONFIG.to_dict(),
                    "output_dir": tmp,
                    "max_epochs": 1,
                    "early_stopping_patience": 1,
                    "hidden_size": 8,
                    "num_layers": 1,
                    "dropout": 0.0,
                }
            ).with_runtime(model_name="bigru", random_seed=11, run_id="unit_smoke")
            summary = run_single_experiment(cfg, smoke=True)
            run_dir = Path(summary["run_dir"])
            self.assertTrue((run_dir / "config.json").exists())
            self.assertTrue((run_dir / "checkpoints" / "best.pt").exists())
            self.assertTrue((run_dir / "metrics" / "validation_metrics.json").exists())


if __name__ == "__main__":
    unittest.main()
