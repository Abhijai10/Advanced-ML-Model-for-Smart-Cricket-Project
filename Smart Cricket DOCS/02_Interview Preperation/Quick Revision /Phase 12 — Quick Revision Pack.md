# Phase 12 — Quick Revision Pack

# Question

What did Phase 12 add to the Smart Cricket system?

## Quick Answer

It added the offline inference pipeline.
The pipeline connects prediction, segmentation, technique scoring, and feedback.
Output is one stable JSON result.

# Question

Why does Phase 12 use finalized temporal sequences instead of raw video upload?

## Quick Answer

Phase 12 is ML orchestration, not API transport.
It analyzes the locked `[60,32]` temporal feature contract.
Raw upload handling belongs to Phase 13.

# Question

How does the pipeline handle scaling?

## Quick Answer

The classifier uses the saved train-only scaler from Phase 8.
Segmentation and scoring use raw temporal features.
This avoids representation mismatch.

# Question

What is included in the Phase 12 output JSON?

## Quick Answer

Top-level fields:
predicted shot, confidence, technique score, issues, tips, detailed feedback, spoken feedback, debug metadata.
Nested fields include prediction probabilities, segmentation, and source metadata.

# Question

How does Phase 12 reuse earlier phases?

## Quick Answer

It loads the Phase 8 checkpoint.
It calls Phase 9 segmentation.
It calls Phase 10 scoring.
It calls Phase 11 feedback.
It does not duplicate those modules.

# Question

Why is debug metadata important?

## Quick Answer

It records pipeline version, artifacts used, input contract, segmentation completion, and feedback source.
This makes API/debugging work easier later.

# Question

How does Phase 12 prepare Phase 13?

## Quick Answer

Phase 13 can call the Phase 12 pipeline and return its JSON.
The API should not duplicate model, scoring, or feedback logic.
