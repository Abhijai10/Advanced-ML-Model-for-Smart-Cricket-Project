"""Final Phase 7 architecture validation for temporal classifiers."""

from __future__ import annotations

import sys
from pathlib import Path

import torch

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from models.bilstm_classifier import BiLSTMClassifier  # noqa: E402
from models.gru_classifier import GRUClassifier  # noqa: E402
from models.model_config import DEFAULT_TEMPORAL_CONFIG  # noqa: E402
from models.model_utils import summarize_model, validate_sequence_input  # noqa: E402


def _validate_model(model_name: str, model: torch.nn.Module, x: torch.Tensor) -> list[str]:
    errors: list[str] = []
    config = DEFAULT_TEMPORAL_CONFIG

    try:
        validate_sequence_input(x, config.sequence_length, config.input_size)
        output = model(x)
    except (RuntimeError, ValueError) as e:
        return [f"{model_name}: forward validation failed: {e}"]

    expected_shape = (x.shape[0], config.num_classes)
    if tuple(output.shape) != expected_shape:
        errors.append(
            f"{model_name}: expected output shape {expected_shape}, got {tuple(output.shape)}."
        )

    summary = summarize_model(model, config, model_name)
    print(f"Model: {model_name}")
    print(f"  trainable parameters: {summary['trainable_parameters']}")
    print(f"  total parameters:     {summary['total_parameters']}")
    print(f"  input shape:          {tuple(x.shape)}")
    print(f"  output shape:         {tuple(output.shape)}")
    print()
    return errors


def main() -> int:
    config = DEFAULT_TEMPORAL_CONFIG
    print("──────── Temporal Architecture Validation (Phase 7.6) ────────\n")
    print("Config:")
    print(f"  sequence_length: {config.sequence_length}")
    print(f"  input_size:      {config.input_size}")
    print(f"  num_classes:     {config.num_classes}")
    print(f"  hidden_size:     {config.hidden_size}")
    print(f"  num_layers:      {config.num_layers}")
    print(f"  dropout:         {config.dropout}")
    print()

    x = torch.randn(4, config.sequence_length, config.input_size)
    models = [
        ("GRUClassifier", GRUClassifier(config)),
        ("BiLSTMClassifier", BiLSTMClassifier(config)),
    ]

    errors: list[str] = []
    for model_name, model in models:
        errors.extend(_validate_model(model_name, model, x))

    if errors:
        print("FAIL: Temporal architecture validation failed.")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: Temporal architectures accept [B, 60, 32] and return [B, 4].")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
