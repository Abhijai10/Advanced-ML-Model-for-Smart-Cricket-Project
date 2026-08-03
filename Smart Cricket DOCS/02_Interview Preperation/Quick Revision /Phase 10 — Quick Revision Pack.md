# Phase 10 — Quick Revision Pack

# Question

Why did Phase 10 separate classifier confidence from technique score?

## Quick Answer

Classifier confidence means “how sure the model is about the shot class.”
Technique score means “how well the movement matches reference mechanics.”
A flawed shot can still be classified confidently.
So confidence is stored for traceability but never used as technique quality.

# Question

Why is the Phase 10 scorer rule-based instead of learned?

## Quick Answer

There are no coach-labeled technique scores yet.
A learned scorer would be weakly supervised and likely overfit.
Rule-based scoring is interpretable, deterministic, and roadmap-aligned for v1.
It compares engineered features against reference ranges.

# Question

How are ideal templates generated?

## Quick Answer

Templates are generated per shot class from the train split.
The system prefers good-quality examples when at least three exist.
Otherwise it falls back to all train examples for that class.
Validation/test samples are not used to build templates.

# Question

What are component scores and why are they important?

## Quick Answer

Component scores break technique into areas:
head stability, front-foot commitment, lead elbow, knee bend, weight transfer, follow-through, rotation, and balance.
They make the score explainable.
Phase 11 uses them to generate specific feedback.

# Question

How does Phase 10 avoid data leakage?

## Quick Answer

Templates come only from train tensors and train labels.
The selected model's test predictions are scored afterward.
This prevents test examples from influencing the reference ranges used to grade them.

# Question

What does the technique score actually mean?

## Quick Answer

It is a 0-100 template-match score.
The scorer compares sequence feature summaries with expected ranges.
Inside range gives high score; outside range gets penalized by deviation size.
It is interpretable, but not coach-certified biomechanical truth.

# Question

How does Phase 10 prepare Phase 11?

## Quick Answer

Phase 10 creates the evidence layer for feedback:
component scores, weakest components, deviation summaries, and recommendations.
Phase 11 can turn those structured results into human-readable coaching advice.
