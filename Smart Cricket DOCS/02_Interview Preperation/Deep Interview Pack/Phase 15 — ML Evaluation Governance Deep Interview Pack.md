# Phase 15 — ML Evaluation Governance Deep Interview Pack

## Why is the current model not production-valid yet?

Short answer: The current model has development metrics, but not enough real-world validation.

Deep answer: The dataset has only 80 samples, the official split is not player-disjoint, confidence thresholds are engineering heuristics, and labels/advice have not been coach-validated. Production validity needs a larger representative dataset, player-held-out evaluation, calibration, and field testing.

## What is player leakage?

Short answer: Player leakage happens when the same player appears in both training and test data.

Deep answer: If the same player's body shape, camera setup, clothing, or motion style appears across splits, the model may learn player-specific patterns instead of general shot mechanics. Smart Cricket now has `player_disjoint_split.py` so future manifests can separate train, validation, and test by player/group ID.

## Why should the split tool fail when player IDs are missing?

Short answer: Guessing player IDs would create fake confidence.

Deep answer: A production evaluation must prove that train and test users are separate. If metadata is missing, the honest engineering behavior is to fail clearly and mark the dataset as incomplete. Filename-based identity guessing could hide leakage.

## What is calibration?

Short answer: Calibration checks whether confidence matches real correctness.

Deep answer: If predictions with 80% confidence are correct about 80% of the time, the model is calibrated. A model can have decent accuracy but poor calibration, which is dangerous for user-facing uncertainty states. Smart Cricket now computes ECE, maximum calibration error, Brier score, and reliability-bin data.

## What is Brier score?

Short answer: Brier score measures how close predicted probabilities are to the true label.

Deep answer: In multiclass classification, it compares the full probability distribution against a one-hot true label. Lower is better. It penalizes confident wrong predictions more than uncertain near-misses.

## How does confidence rejection help?

Short answer: It shows what happens if the app rejects low-confidence predictions.

Deep answer: The evaluation report calculates coverage and accepted accuracy at confidence thresholds. This helps choose an `uncertain` threshold: a higher threshold may improve accepted accuracy but reject more clips.

## What would make the model production-ready?

Short answer: Larger data, player-held-out metrics, calibration, drift monitoring, and coach validation.

Deep answer: The code now has the evaluation tooling, but production readiness depends on real evidence. The model needs a locked evaluation protocol, no player leakage, calibrated confidence thresholds, accepted safety criteria, and a plan for monitoring distribution drift after release.
