# Phase 8 Training and Evaluation Report

## Executive Summary

Phase 8 trained bidirectional GRU and BiLSTM temporal shot classifiers on the official sample-stratified development split. Model selection used validation macro F1 only; the test split was evaluated after selecting the winning model.

## Dataset Contract

- Input: `[B, 60, 32]`
- Output logits: `[B, 4]`
- Classes: cover_drive, defensive_shot, pull_shot, sweep_shot

## Split Protocol and Limitation

The 56/12/12 split is deterministic and class-balanced, but not person-disjoint. The player-overlap audit found no exact sample leakage and all four players appearing across splits. Results do not prove unseen-player generalization.

## Feature Scaling

Feature means and standard deviations were fitted on `X_train_sequence.npy` only, per feature over samples and timesteps.

## Reproducibility Controls

Each run sets Python, NumPy, and PyTorch seeds, records environment metadata, stores the Git SHA, and uses deterministic DataLoader generators. Bitwise determinism can still vary across CPU, CUDA, and MPS backends.

## Models and Seed Strategy

Models trained: `bigru`, `bilstm`. Seeds: 42, 123, 2026.

## Training Configuration

Optimizer: AdamW; loss: CrossEntropyLoss; gradient clipping: enabled; scheduler: ReduceLROnPlateau; checkpoint metric: validation macro F1; test set excluded from model selection.

## Per-Seed Validation Results

- `bigru` seed `42`: val macro F1=0.8375, val accuracy=0.8333, best epoch=14
- `bigru` seed `123`: val macro F1=0.8310, val accuracy=0.8333, best epoch=9
- `bigru` seed `2026`: val macro F1=0.8375, val accuracy=0.8333, best epoch=14
- `bilstm` seed `42`: val macro F1=0.7542, val accuracy=0.7500, best epoch=15
- `bilstm` seed `123`: val macro F1=0.7595, val accuracy=0.7500, best epoch=18
- `bilstm` seed `2026`: val macro F1=0.6571, val accuracy=0.6667, best epoch=12

## Aggregate Model Comparison

- `bigru`: mean val macro F1=0.8353, std=0.0031, params=421892
- `bilstm`: mean val macro F1=0.7236, std=0.0471, params=562180

## Best Model

Selected model: `bigru` using mean validation macro F1.

## Final Holdout Test Metrics

- Accuracy: `0.6667`
- Macro precision: `0.7083`
- Macro recall: `0.6667`
- Macro F1: `0.6762`
- Weighted F1: `0.6762`

## Per-Class Metrics

- `cover_drive`: precision=1.0000, recall=0.6667, f1=0.8000, support=3
- `defensive_shot`: precision=0.6667, recall=0.6667, f1=0.6667, support=3
- `pull_shot`: precision=0.6667, recall=0.6667, f1=0.6667, support=3
- `sweep_shot`: precision=0.5000, recall=0.6667, f1=0.5714, support=3

## Confusion Matrix Interpretation

- `sweep_shot` predicted as `pull_shot`: 1
- `pull_shot` predicted as `defensive_shot`: 1
- `defensive_shot` predicted as `sweep_shot`: 1
- `cover_drive` predicted as `sweep_shot`: 1

## What Phase 8 Proves / Does Not Prove

Phase 8 proves the locked GRU/BiLSTM architectures can be trained end-to-end on the finalized temporal tensors with validation-based checkpointing and traceable evaluation artifacts. It does not prove production readiness, real-time inference behavior, or unseen-player generalization.

## Known Limitations

- Small dataset: 80 total samples, 56 training samples.
- Current split is not person-disjoint.
- Velocity features are normalized displacement per standardized sequence step, not physical metres/second.
- `lead_wrist_acceleration` is an acceleration-like proxy.
- Four highly correlated feature pairs are known.

## Person-Held-Out Evaluation Status

A person-held-out protocol was prepared as a documented future evaluation path, but no LOPO metric was reported because the four-player dataset requires a separately locked non-leaky validation policy.

## Future Recommendations

- Plan Phase 9 shot segmentation without changing the Phase 8 checkpoint selection record.
- Add a locked group-aware unseen-player evaluation protocol before making generalization claims.
- Expand the dataset before increasing architecture complexity.

## Artifact Locations

- Experiments: `/Users/abhijairaghuvanshi/Desktop/PROJECTS/Project 1 - Advanced ML Model for Smart Cricket Project/ml/artifacts/phase8/experiments`
- Comparison: `/Users/abhijairaghuvanshi/Desktop/PROJECTS/Project 1 - Advanced ML Model for Smart Cricket Project/ml/artifacts/phase8/comparisons`
- Best model: `/Users/abhijairaghuvanshi/Desktop/PROJECTS/Project 1 - Advanced ML Model for Smart Cricket Project/ml/artifacts/phase8/best_model`

## Reproduction Commands

```bash
ml/venv/bin/python ml/src/training/train_temporal_models.py --full
```
