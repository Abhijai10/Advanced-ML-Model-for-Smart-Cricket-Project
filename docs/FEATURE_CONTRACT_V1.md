# Smart Cricket Feature Contract v1

The current deployed checkpoint uses a frozen tensor contract:

- sequence shape: `60 x 32`
- feature schema: `ml/data/final_temporal/temporal_feature_schema.json`
- checkpoint: `ml/artifacts/phase8/best_model/checkpoint.pt`
- feature contract version: `smart_cricket_temporal_features_v1`

Do not reorder, rename, remove, or silently change the semantics of these 32 features for the existing checkpoint. Any feature tensor change requires a new schema version, rebuilt tensors, train-only scaler refit, retrained checkpoint, model card update, and player-held-out evaluation.

## Known v1 Semantic Compatibility Note

`lead_wrist_acceleration` is a backwards-compatible v1 name with imperfect semantics. The value currently computed in `ml/src/features/temporal_frame_features.py` is:

```text
abs(lead_wrist_velocity - trail_wrist_velocity)
```

That is an acceleration-like wrist-motion asymmetry proxy, not true second-order acceleration over time. The name is preserved in v1 only because the trained model expects the existing 32-column tensor.

## v2 Migration Requirement

A future v2 feature contract should either:

- rename the current value to a semantically accurate name such as `wrist_velocity_asymmetry`; or
- compute true lead-wrist acceleration from positions at `t-2`, `t-1`, and `t`.

That change must be released as a new feature schema and model version. User-facing docs and evaluation reports must clearly distinguish v1 scores from any v2 model.
