# Phase 10 — Deep Interview Pack

# Question

Why did Phase 10 separate classifier confidence from technique score?

## Short Answer

Because confidence answers what shot the model thinks it saw, while technique score answers how well the shot was executed.

## Deep Technical Explanation

A classifier probability is a recognition output. It estimates class likelihood under the model. A technique score is an execution-quality assessment based on biomechanical deviation from reference behavior.

A poor cover drive can still contain enough cover-drive motion patterns for the model to classify it confidently. If confidence were reused as technique score, the system would reward recognizable but flawed shots.

## Engineering Reasoning

The system has separate responsibilities:

- Phase 8 recognizes shot class
- Phase 9 determines when one shot should trigger prediction
- Phase 10 evaluates movement quality
- Phase 11 generates feedback

Keeping these meanings separate prevents misleading coaching output.

## Why This Decision Was Taken

The roadmap explicitly states that shot confidence is not technique score. The implementation records classifier confidence only for traceability.

## Tradeoffs / Risks / Limitations

The v1 score is not coach-labeled truth. It is a template-match estimate.

## Important Engineering Insight

A production ML pipeline must preserve semantic boundaries between prediction, quality assessment, and explanation.

# Question

Why is the Phase 10 scorer rule-based instead of learned?

## Short Answer

Because the project does not yet have coach-labeled technique scores, and rule-based scoring is more honest and interpretable for v1.

## Deep Technical Explanation

A learned scoring model would need targets such as expert-rated technique scores. Without those labels, training a scorer would create a model that optimizes arbitrary or weak supervision.

The rule-based scorer uses existing engineered features and compares them to template ranges. This gives deterministic, inspectable behavior.

## Engineering Reasoning

The dataset is small, with only 80 v1 samples. A learned scorer would likely overfit and be hard to defend. Rule-based scoring allows the system to move forward while maintaining interpretability.

## Why This Decision Was Taken

The roadmap recommends keeping scoring rule-based initially.

## Tradeoffs / Risks / Limitations

Rule-based scoring depends on template quality and component design. It may miss subtle biomechanics.

## Important Engineering Insight

The best v1 ML system is not always the most complex model. Sometimes the correct engineering step is a simple, auditable layer.

# Question

How are ideal templates generated?

## Short Answer

Templates are generated from the train split per shot class, preferring good-quality examples when enough are available.

## Deep Technical Explanation

For each class, the scorer selects template samples from `X_train_sequence.npy` and `y_train_sequence.npy`. It uses `metadata.csv` to prefer good-quality clips. If fewer than three good-quality examples exist, it falls back to all training examples for that class.

For each component feature/statistic pair, it computes expected low/high ranges using robust quantiles.

## Engineering Reasoning

Using train split only avoids validation/test leakage. Using good-quality examples when available makes templates closer to intended movement quality.

## Why This Decision Was Taken

Professional reference clips are not yet available, so train-split-derived references are the most practical v1 option.

## Tradeoffs / Risks / Limitations

The templates are not coach-certified. Future versions should replace or validate them with professional references.

## Important Engineering Insight

When ideal labels are unavailable, template provenance must be explicit.

# Question

What are component scores and why are they important?

## Short Answer

Component scores break total technique quality into interpretable areas like head stability, knee bend, follow-through, and balance.

## Deep Technical Explanation

The scorer computes eight weighted components:

- head stability
- front-foot commitment
- lead elbow
- knee bend
- weight transfer
- follow-through
- rotation
- balance

Each component uses specific temporal feature summaries. The total score is a weighted average.

## Engineering Reasoning

One total score is not enough for coaching. Component scores tell the feedback engine what to explain and prioritize.

## Why This Decision Was Taken

The roadmap requires component scores, not only a total score.

## Tradeoffs / Risks / Limitations

Component weights are v1 engineering choices and should later be calibrated with coaching input.

## Important Engineering Insight

Explainability is not an afterthought. It must be designed into the scoring output.

# Question

How does Phase 10 avoid data leakage?

## Short Answer

It builds templates from the train split and scores the selected model's test predictions separately.

## Deep Technical Explanation

The template generator reads train tensors and train labels. It does not use validation or test feature values to define ideal ranges. Test samples are only scored after templates exist.

## Engineering Reasoning

If test samples influenced the template ranges, the score report would be contaminated. The system would be partially grading test samples against themselves.

## Why This Decision Was Taken

The project already follows train-only scaling in Phase 8. Phase 10 preserves the same evaluation discipline.

## Tradeoffs / Risks / Limitations

With only 14 training samples per class, template ranges can be narrow or noisy.

## Important Engineering Insight

Leakage can happen outside model training. Any learned or derived reference must respect split boundaries.

# Question

What does the technique score actually mean?

## Short Answer

It is a 0-100 template-match score based on measurable feature deviations.

## Deep Technical Explanation

For each configured feature/statistic pair, the scorer checks whether the actual sequence summary falls inside the expected range for the predicted shot. Values inside the range receive full feature credit. Values outside the range receive a penalty based on distance from the range.

Component scores average feature-level scores. The total score is a weighted component average.

## Engineering Reasoning

This makes the score deterministic, inspectable, and explainable.

## Why This Decision Was Taken

The goal is to produce a useful quality signal before natural-language feedback exists.

## Tradeoffs / Risks / Limitations

The score is not absolute cricket truth. It is only as good as the features, templates, and weights.

## Important Engineering Insight

A good engineering report explains what a metric means and what it does not mean.

# Question

How does Phase 10 prepare Phase 11?

## Short Answer

It creates component scores, deviation summaries, and recommendations that the feedback engine can convert into coaching text.

## Deep Technical Explanation

Phase 11 needs structured reasons. It cannot generate reliable feedback from a class label alone. Phase 10 gives it weak components and feature deviations, such as poor head stability or unusual follow-through extension.

## Engineering Reasoning

Feedback should be grounded in measurable evidence, not generic advice.

## Why This Decision Was Taken

The roadmap places scoring before feedback because scoring supplies the evidence layer.

## Tradeoffs / Risks / Limitations

Phase 11 must avoid overclaiming. It should phrase feedback as measured deviations, not definitive medical or coaching diagnosis.

## Important Engineering Insight

Good feedback systems need an evidence model before a language model or text-generation layer.
