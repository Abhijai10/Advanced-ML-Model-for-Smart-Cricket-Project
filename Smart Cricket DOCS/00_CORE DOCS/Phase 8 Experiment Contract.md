# Phase 8 Experiment Contract

This document locks the rules for Phase 8 — Temporal Model Training & Evaluation. It is not a training report and does not contain model results.

## A. Dataset Usage

- Official temporal dataset location: `ml/data/final_temporal/`
- Official full tensor: `X_sequence.npy` with shape `(80, 60, 32)`
- Official encoded labels: `y_sequence.npy` with shape `(80,)`
- Official development split:
  - `X_train_sequence.npy`: `(56, 60, 32)`
  - `X_val_sequence.npy`: `(12, 60, 32)`
  - `X_test_sequence.npy`: `(12, 60, 32)`
- Current split is deterministic and class-balanced: 56 train, 12 validation, 12 test.
- Test set must remain untouched during model selection, hyperparameter selection, and early stopping.
- The existing 56/12/12 split is an in-distribution development evaluation split.
- Unseen-player generalization has not been proven by the current split and must be evaluated separately.

## B. Feature Preprocessing

- Fit feature scaling on `X_train_sequence.npy` only.
- Transform validation and test tensors using training-fitted statistics only.
- Scale independently per feature dimension across training samples and timesteps.
- Save scaler statistics for inference so live or held-out samples use the same transformation.
- Do not fit preprocessing statistics on validation or test data.

## C. Reproducibility

- Set a Python random seed.
- Set a NumPy random seed.
- Set a PyTorch random seed.
- Use deterministic behavior where reasonably possible for the selected device.
- Report device name and device type.
- Report Python, NumPy, PyTorch, and scikit-learn versions.
- Record the dataset manifest version from `temporal_dataset_manifest.json`.
- Capture the exact `TemporalClassifierConfig` used for each run.

## D. Training Baseline

- Use `CrossEntropyLoss` for the first shot-classification baseline.
- Use Adam or AdamW as the initial optimizer.
- Start with a conservative learning rate.
- Use a small batch size suitable for only 56 training samples.
- Do not expand the architecture before baseline results exist.
- Consider gradient clipping for recurrent models.
- Base early stopping only on validation behavior.
- Select the best checkpoint using a defined validation metric.

## E. Evaluation

Report at minimum:

- accuracy
- macro precision
- macro recall
- macro F1
- per-class precision, recall, and F1
- confusion matrix
- training loss
- validation loss
- generalization gap
- multiple-seed stability

Do not tune on the test set.

## F. Model Comparison

- Report bidirectional configuration explicitly.
- Do not label the default model only as "GRU" if it is configured bidirectionally.
- Compare GRU, BiGRU, and BiLSTM configurations accurately.
- Compare parameter count and overfitting behavior, not only highest accuracy.

## G. Generalization Protocol

- Retain the current split for development.
- Define a future player-held-out evaluation before claiming unseen-player generalization.
- Recommended future protocol: leave-one-player-out evaluation across `playerA` through `playerD`, or another documented group-aware protocol.
- Do not implement the full cross-validation training pipeline until the roadmap explicitly calls for it.

## H. Known Feature Semantics

- Current velocity features are normalized displacement per standardized sequence step, not physical metres per second.
- `stance_to_swing_progress_signal` is an explicit normalized time-position feature.
- `lead_wrist_acceleration` is currently an acceleration-like proxy and not true second-order acceleration.
- Four highly correlated feature pairs are known from `temporal_feature_health.json`.
- Do not remove features before the first controlled baseline unless a blocker is proven.
- Feature ablation may be performed after baseline training.

## I. Small-Data Safeguards

- Total samples: 80.
- Development-training samples: 56.
- Current recurrent models contain hundreds of thousands of parameters.
- Overfitting risk is high.
- Training accuracy alone is not meaningful.
- Validation variance and multiple random seeds matter.

## J. Phase 8 Boundaries

Phase 8 will build:

- temporal training pipeline
- feature scaling fitted on train only
- baseline GRU/BiGRU/BiLSTM training runs
- validation tracking
- checkpoint selection
- final evaluation report

Phase 8 will not claim:

- unseen-player generalization without a player-held-out protocol
- production-readiness from one deterministic development split
- feature superiority without controlled ablation or baseline comparison

Phase 8 should not build unrelated production APIs, coaching feedback engines, or deployment systems.
