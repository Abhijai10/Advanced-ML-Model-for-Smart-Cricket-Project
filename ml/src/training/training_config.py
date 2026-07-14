"""Controlled Phase 8 experiment configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path


ML_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Phase8TrainingConfig:
    """Single-run configuration for temporal model training."""

    dataset_dir: str = str(ML_ROOT / "data" / "final_temporal")
    sequence_length: int = 60
    input_size: int = 32
    num_classes: int = 4
    label_mapping_path: str = str(ML_ROOT / "data" / "final_temporal" / "temporal_label_mapping.json")

    model_name: str = "bigru"
    hidden_size: int = 128
    num_layers: int = 2
    dropout: float = 0.2
    bidirectional: bool = True
    parameter_count: int = 0

    random_seed: int = 42
    batch_size: int = 8
    max_epochs: int = 80
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    optimizer_name: str = "AdamW"
    gradient_clip_norm: float = 1.0
    early_stopping_patience: int = 12
    min_improvement_delta: float = 1e-4
    checkpoint_metric: str = "validation_macro_f1"
    checkpoint_mode: str = "max"
    num_workers: int = 0
    device_preference: str = "auto"

    experiment_name: str = "phase8_temporal_baseline"
    run_id: str = ""
    output_dir: str = str(ML_ROOT / "artifacts" / "phase8")
    timestamp: str = ""
    dataset_version: str = "phase_6_temporal_v1"
    notes: str = (
        "Conservative Phase 8 baseline for 56 training sequences: small batch, "
        "AdamW with light weight decay, validation early stopping, and gradient clipping."
    )

    def with_runtime(self, *, model_name: str, random_seed: int, run_id: str) -> "Phase8TrainingConfig":
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        bidirectional = model_name in ("bigru", "bilstm")
        return replace(
            self,
            model_name=model_name,
            random_seed=random_seed,
            run_id=run_id,
            timestamp=timestamp,
            bidirectional=bidirectional,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Phase8ExperimentPlan:
    """Locked Phase 8 baseline experiment plan."""

    model_names: tuple[str, ...] = ("bigru", "bilstm")
    seeds: tuple[int, ...] = (42, 123, 2026)
    smoke_model_name: str = "bigru"
    smoke_seed: int = 7
    selection_metric: str = "validation_macro_f1"
    selection_rule: str = (
        "Highest mean validation macro F1 across seeds; tie-breakers are lower "
        "standard deviation, smaller train-validation gap, lower validation loss, "
        "fewer parameters, then simpler model."
    )


DEFAULT_PHASE8_CONFIG = Phase8TrainingConfig()
DEFAULT_PHASE8_PLAN = Phase8ExperimentPlan()
