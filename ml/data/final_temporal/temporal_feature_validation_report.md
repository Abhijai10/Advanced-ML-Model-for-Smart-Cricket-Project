# Temporal Feature Validation Report

## Dataset Shape

- X_sequence shape: `(80, 60, 32)`
- Samples: `80`
- Time steps: `60`
- Features: `32`
- Label distribution: `{'cover_drive': 20, 'defensive_shot': 20, 'pull_shot': 20, 'sweep_shot': 20}`

## Validation Status

- Rank check: passed
- Expected shape `[samples, 60, 32]`: passed
- NaN check: passed
- Infinite value check: passed
- Label count check: passed

## Thresholds Used

- `dead_range_epsilon`: `1e-12`
- `near_dead_variance_threshold`: `1e-08`
- `near_dead_mean_abs_temporal_delta_threshold`: `1e-06`
- `near_zero_absolute_value_threshold`: `1e-08`
- `noisy_delta_to_range_threshold`: `0.35`
- `noisy_std_to_range_threshold`: `0.3`
- `noisy_std_delta_to_range_threshold`: `0.2`
- `high_correlation_abs_threshold`: `0.95`

## Feature Health Summary

- Total features: `32`
- Healthy features: `32`
- Dead features: `0`
- Near-dead features: `0`
- Potentially noisy features: `0`
- Highly correlated pairs: `4`

## Dead Features

- None

## Near-Dead Features

- None

## Potentially Noisy Features

- None

## Highly Correlated Feature Pairs

- `hip_rotation_angle` <-> `shoulder_hip_separation`: -1.000000
- `body_center_offset_x` <-> `upper_body_balance_offset`: 1.000000
- `lead_elbow_angle` <-> `lead_elbow_extension_signal`: 1.000000
- `trunk_lean` <-> `body_center_offset_y`: 0.987064

## Interpretation Notes

- Dead and near-dead flags indicate weak observed variation in the current dataset, not automatic removal decisions.
- Noisy flags are temporal stability warnings; they should be checked against video quality, pose jitter, and normalization choices.
- High correlation can be legitimate when two biomechanical signals encode related movement, but it may reduce model efficiency.
- Per-class mean and standard deviation values are included in the statistics CSV for class-separability review.

## Recommendations

- Audit highly correlated pairs during feature selection; retain both only if temporal semantics differ.
- No dead or near-dead blockers found; proceed to temporal model experiments with monitoring.
