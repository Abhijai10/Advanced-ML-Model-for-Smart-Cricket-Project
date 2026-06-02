# Temporal Dataset Report

Generated: `2026-05-31T17:45:55.187540Z`

# Dataset Summary

- X_sequence shape: `(80, 60, 32)`
- y_sequence shape: `(80,)`
- Sequence length: `60`
- Feature dimension: `32`
- Number of classes: `4`
- Class names: `cover_drive`, `defensive_shot`, `pull_shot`, `sweep_shot`

# Split Summary

- X_train_sequence shape: `(56, 60, 32)`
- y_train_sequence shape: `(56,)`
- X_val_sequence shape: `(12, 60, 32)`
- y_val_sequence shape: `(12,)`
- X_test_sequence shape: `(12, 60, 32)`
- y_test_sequence shape: `(12,)`

## Class Distribution - Full

- **cover_drive**: 20
- **defensive_shot**: 20
- **pull_shot**: 20
- **sweep_shot**: 20

## Class Distribution - Train

- **cover_drive**: 14
- **defensive_shot**: 14
- **pull_shot**: 14
- **sweep_shot**: 14

## Class Distribution - Validation

- **cover_drive**: 3
- **defensive_shot**: 3
- **pull_shot**: 3
- **sweep_shot**: 3

## Class Distribution - Test

- **cover_drive**: 3
- **defensive_shot**: 3
- **pull_shot**: 3
- **sweep_shot**: 3

# Validation Checks

| Check | Status |
|---|---|
| tensor integrity | PASS |
| split integrity | PASS |
| metadata integrity | PASS |
| schema integrity | PASS |
| index traceability | PASS |
| class balance | PASS |

Overall validation: **PASS**

# Engineering Notes

- Rank-3 tensors preserve the temporal contract expected by sequence models: `[samples, time_steps, features]`.
- Full-sequence splitting prevents frames from the same batting clip leaking across train, validation, and test.
- Deterministic splitting makes model comparisons reproducible across Phase 7 experiments.
- Index traceability keeps every split row tied back to the original video metadata and pose sequence path.

# Future Dependency Notes

- Phase 7 temporal training should load these split tensors directly and treat this report as the dataset integrity gate.
- The inference pipeline depends on the same schema, label mapping, sequence length, and feature order validated here.
