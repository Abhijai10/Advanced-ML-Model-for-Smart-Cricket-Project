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

Future manifests with player/group identity metadata can be split with
`ml/src/evaluation/player_disjoint_split.py`. The utility writes a manifest with
a `split` column plus a JSON summary proving whether train, validation, and test
are group-disjoint. It intentionally fails when player/group IDs are missing.

## Known Gaps

- More players, camera positions, lighting conditions, and skill levels are needed.
- Player/group metadata should be completed and used for held-out evaluation.
- Scaler fitting must remain train-only.
- Data-quality labels should include pose visibility, motion completeness, and camera framing.

## Next Dataset Work

- Run player-disjoint split generation once the next consented manifest includes player IDs.
- Report per-player and per-class metrics from player-held-out predictions.
- Add uncertainty thresholds and insufficient-quality labels.
- Keep dataset shape/count validation data-driven for larger datasets.
