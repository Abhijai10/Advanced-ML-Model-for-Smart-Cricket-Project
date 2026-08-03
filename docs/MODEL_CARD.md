# Smart Cricket Model Card

## Model

- Selected model: bidirectional GRU (`bigru`)
- Input: 60-frame sequence, 32 engineered temporal pose features per frame
- Output classes: cover drive, defensive shot, pull shot, sweep shot
- Checkpoint: `ml/artifacts/phase8/best_model/checkpoint.pt`

## Reported Development Metrics

- Holdout test accuracy: `0.6667`
- Holdout macro F1: `0.6762`

These metrics are from the current small, deterministic, class-balanced development dataset. They are useful for engineering validation, not proof of field-ready coaching accuracy.

## Intended Use

The model is intended for cricket-shot demo analysis and iterative coaching-feedback research. It can support portfolio demonstrations and controlled local testing.

## Limitations

- The current dataset is small.
- The official split is not player-disjoint.
- Pose quality, camera angle, distance, lighting, occlusion, and clothing can materially affect predictions.
- Technique scores are rule-based template matches, not certified biomechanical assessments.
- Coach review is still needed before presenting feedback as authoritative.

## Required Before Strong Production Claims

- Player/group-held-out evaluation.
- Larger and more diverse video collection.
- Calibration and uncertainty thresholds.
- Explicit `uncertain` or insufficient-quality output for poor pose/video inputs.
- Field testing with coaches and players.

## Current Uncertainty Handling

API responses include `analysis_quality.status`:

- `ok` when confidence and pose-frame thresholds pass;
- `uncertain` when model confidence is below the configured threshold;
- `insufficient_quality` when too few clean pose frames are available.

These thresholds are engineering safeguards, not calibrated clinical or coaching guarantees.
