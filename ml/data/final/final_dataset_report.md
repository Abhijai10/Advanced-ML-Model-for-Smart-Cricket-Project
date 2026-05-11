# Smart Cricket — Final Dataset Report (Phase 6.6)

Generated: `2026-05-10T21:30:57Z`

## Dataset source

- **Engineered features CSV (reference):** `/Users/abhijairaghuvanshi/Desktop/PROJECTS/Project 1 - Advanced ML Model for Smart Cricket Project/ml/data/processed/features/features.csv`
- **Final artifact directory:** `/Users/abhijairaghuvanshi/Desktop/PROJECTS/Project 1 - Advanced ML Model for Smart Cricket Project/ml/data/final`

## Summary

| Metric | Value |
|--------|-------|
| Total samples | 80 |
| Number of features | 32 |
| Train / Val / Test sizes | 56 / 12 / 12 |

## Class names (from `label_mapping.json`)

`cover_drive`, `defensive_shot`, `pull_shot`, `sweep_shot`

## Class distribution — full (`y.npy`)

- **cover_drive**: 20
- **defensive_shot**: 20
- **pull_shot**: 20
- **sweep_shot**: 20

## Class distribution — train / validation / test

### Train

- **cover_drive**: 14
- **defensive_shot**: 14
- **pull_shot**: 14
- **sweep_shot**: 14

### Validation

- **cover_drive**: 3
- **defensive_shot**: 3
- **pull_shot**: 3
- **sweep_shot**: 3

### Test

- **cover_drive**: 3
- **defensive_shot**: 3
- **pull_shot**: 3
- **sweep_shot**: 3

## Feature schema summary

- **Target column:** `shot_label`
- **num_features:** `32`
- **Metadata columns (schema):** `[]`
- **Feature columns (count):** 32

## Split strategy

- **Strategy:** `manual deterministic per-class stratified split`
- **random_state:** `42`
- **split_metadata `split_sizes`:**

```json
{
  "train": 56,
  "validation": 12,
  "test": 12
}
```

## Validation status

**PASSED**


## Notes for future phases

- Scaling and normalization should use statistics fit **only on train** (or fold train), then applied to val/test.
- Phase 7+ model training should load this report location as a provenance anchor (`final_dataset_report.md`).
- If new clips are added, re-run feature build, schema, encoder, matrix, splits, and this validator.
