# Smart Cricket Dataset Card

## Dataset

- Current temporal tensor: `ml/data/final_temporal/X_sequence.npy`
- Current shape: `(80, 60, 32)`
- Samples: 80 finalized cricket batting clips
- Classes: 4 shot categories
- Feature schema: `ml/data/final_temporal/temporal_feature_schema.json`

## Split

The current split is deterministic and class-balanced:

- Train: 56 samples
- Validation: 12 samples
- Test: 12 samples

This split is not player-disjoint. It should not be used as evidence of unseen-player generalization.

## Known Gaps

- More players, camera positions, lighting conditions, and skill levels are needed.
- Player/group metadata should be completed and used for held-out evaluation.
- Scaler fitting must remain train-only.
- Data-quality labels should include pose visibility, motion completeness, and camera framing.

## Next Dataset Work

- Add player IDs and group-aware split generation.
- Report per-player and per-class metrics.
- Add uncertainty thresholds and insufficient-quality labels.
- Keep dataset shape/count validation data-driven for larger datasets.
