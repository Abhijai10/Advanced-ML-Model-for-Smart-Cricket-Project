# Smart Cricket ML Evaluation and Dataset Governance

Smart Cricket now includes evaluation tooling for future player-held-out datasets. These tools do not retrain the model, fabricate player IDs, or create new quality claims. They make the next real evaluation repeatable.

## Player-Disjoint Splits

Use `ml/src/evaluation/player_disjoint_split.py` when a manifest contains player or group identity metadata.

Required fields:

- a stable sample identifier such as `sample_id`, `video_id`, or `file_name`;
- a label field such as `shot_label`, `label`, or `true_label`;
- a player/group field such as `player_id`, `person_id`, `participant_id`, or `group_id`.

Example:

```bash
python -m ml.src.evaluation.player_disjoint_split \
  --input ml/data/annotations/manifest.csv \
  --output ml/data/annotations/manifest_player_disjoint.csv \
  --summary ml/data/annotations/player_disjoint_split_summary.json \
  --group-field player_id \
  --label-field shot_label
```

The command fails when player/group IDs are missing. That is intentional: missing identity metadata is a production blocker, not something the tooling should guess.

## Calibration and Reliability

Use `ml/src/evaluation/calibration_report.py` or the higher-level reproducible entry point `ml/src/evaluation/evaluate_predictions.py` after generating predictions on a player-held-out split.

Supported prediction formats:

- CSV columns such as `prob_cover_drive`, `prob_pull_shot`, and so on;
- JSON object field `probabilities` or `class_probabilities`;
- nested `prediction.class_probabilities`.

Example:

```bash
python -m ml.src.evaluation.evaluate_predictions \
  --predictions ml/artifacts/evaluation/player_holdout_predictions.csv \
  --output-dir ml/artifacts/evaluation \
  --labels cover_drive,defensive_shot,pull_shot,sweep_shot
```

The report includes:

- accuracy and macro F1;
- class-wise precision, recall, F1, and support;
- confusion matrix;
- negative log likelihood;
- multiclass Brier score;
- expected calibration error and maximum calibration error;
- reliability-bin data and reliability SVG;
- confidence-threshold rejection coverage and accepted accuracy.

## Release Interpretation

Passing these tools is necessary, not sufficient. Public production claims still require:

- a larger representative dataset across players, devices, lighting, camera position, skill level, and clothing variation;
- coach-reviewed shot labels and feedback safety decisions;
- player-held-out metrics that pass documented release thresholds;
- calibrated confidence thresholds connected to the API `uncertain` behavior;
- drift monitoring against prediction confidence, class distribution, and feedback disagreement.
