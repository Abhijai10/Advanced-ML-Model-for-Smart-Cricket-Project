# Phase 8 Failure Analysis

Selected run: `bigru_seed42`

## Confused Class Pairs

- `sweep_shot` predicted as `pull_shot`: 1
- `pull_shot` predicted as `defensive_shot`: 1
- `defensive_shot` predicted as `sweep_shot`: 1
- `cover_drive` predicted as `sweep_shot`: 1

## Per-Class Notes

- `cover_drive`: precision=1.0000, recall=0.6667, f1=0.8000, support=3
- `defensive_shot`: precision=0.6667, recall=0.6667, f1=0.6667, support=3
- `pull_shot`: precision=0.6667, recall=0.6667, f1=0.6667, support=3
- `sweep_shot`: precision=0.5000, recall=0.6667, f1=0.5714, support=3

## Low-Confidence / High-Confidence Error Notes

- `sweep_shot_bad_02.mov`: true `sweep_shot`, predicted `pull_shot`, confidence=0.9886, person=playerB, quality=bad
- `defensive_shot_good_02.mov`: true `defensive_shot`, predicted `sweep_shot`, confidence=0.6852, person=playerA, quality=good
- `cover_drive_good_02.mov`: true `cover_drive`, predicted `sweep_shot`, confidence=0.6303, person=playerA, quality=good
- `pull_shot_good_05.mov`: true `pull_shot`, predicted `defensive_shot`, confidence=0.4673, person=playerC, quality=good

Misclassifications by person:
- `playerA`: 2
- `playerC`: 1
- `playerB`: 1

Misclassifications by quality:
- `good`: 3
- `bad`: 1

Machine-readable misclassified samples: `/Users/abhijairaghuvanshi/Desktop/PROJECTS/Project 1 - Advanced ML Model for Smart Cricket Project/ml/artifacts/phase8/misclassified_samples.csv`

## Scientific Caution

Errors are classification observations only. They do not prove a biomechanical cause without a separate feature-level analysis.
The official split is sample-stratified and not person-disjoint, so these metrics represent in-distribution development performance.
