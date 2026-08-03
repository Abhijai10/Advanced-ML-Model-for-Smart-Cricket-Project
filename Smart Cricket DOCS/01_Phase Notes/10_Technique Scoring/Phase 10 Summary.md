# Phase 10 — Technique Scoring System

# 🎯 Goal of the Phase

Phase 10 added the first layer that evaluates shot execution quality instead of only recognizing shot class.

Previous phases answered:

```text
What shot was played?
Where does the shot segment complete?
```

Phase 10 answers:

```text
How closely does the movement match measurable reference mechanics for the predicted shot?
```

Input:

```text
predicted shot
temporal feature sequence
ideal shot template
```

Output:

```text
technique_match_score
component scores
deviation summary
recommendations for feedback
```

The main architectural distinction is that classifier confidence is not treated as technique quality. A model can be confident that a shot is a pull shot while the batting technique still has weak balance, rotation, or follow-through.

# 🧠 Core Concepts Introduced

## Technique Score vs Classifier Confidence

Classifier confidence is a recognition signal. It measures how strongly the trained model assigns a sequence to a shot class.

Technique score is a movement-quality signal. It compares measured biomechanical features with shot-specific reference ranges.

This separation matters because a bad cover drive can still be confidently classified as a cover drive. If the system reused probability as technique score, feedback would become misleading and scientifically weak.

## Rule-Based Template Matching

The v1 scoring system is intentionally rule-based. It creates expected feature ranges per shot class and compares a user sequence against those ranges.

This is appropriate at this stage because:

- the dataset is small
- professional scoring labels are not available
- interpretability matters more than opaque scoring
- Phase 11 needs component-level explanations

Templates are generated from the training split only. The system prefers good-quality training examples when enough exist, and otherwise falls back to all training examples for that shot class. This avoids leaking validation/test samples into the reference behavior.

## Component Scores

The system returns eight component scores:

- head_stability_score
- front_foot_commitment_score
- lead_elbow_score
- knee_bend_score
- weight_transfer_score
- follow_through_score
- rotation_score
- balance_score

Each component is based on a small group of measurable temporal features. For example, follow-through uses final-frame-region summaries of follow-through height, extension, and wrist height signals.

The total technique score is a weighted average of component scores. This keeps the output simple while preserving detailed reasons behind the score.

## Feature Deviation

For every feature/statistic pair, the scorer computes:

- actual value from the sequence
- expected low/high template range
- template center
- deviation outside the range
- feature-level score

This creates explainability. The system can say which measurable feature was above or below the template, instead of giving a random score with no reasoning.

# 🏗️ System-Level Importance

Phase 10 connects model prediction to coaching intelligence.

Earlier phases built:

```text
pose extraction
→ temporal features
→ trained classifier
→ segmentation trigger
```

Phase 10 adds:

```text
predicted shot + temporal features
→ technique scoring
```

This prepares Phase 11 because feedback should not be generic. The feedback engine needs structured weaknesses such as low head stability or poor follow-through, not only the predicted shot label.

# 📂 Important Files / Scripts

## ml/src/scoring/score_config.py

Defines the scoring contract:

- expected sequence length: 60
- expected feature dimension: 32
- component names
- component weights
- feature/statistic pairs
- template quantile thresholds

This keeps scoring rules centralized and easy to audit.

## ml/src/scoring/technique_scoring.py

Implements:

- template generation
- sequence validation
- feature summarization
- component scoring
- total score aggregation
- deviation summaries
- Phase 10 artifact generation

This is the core scoring engine.

## ml/src/scoring/validate_technique_scoring.py

Runs the Phase 10 artifact generation and validates that:

- templates exist for all four classes
- scores are within 0-100
- component scores are valid
- classifier confidence is not used as technique score

## ml/src/scoring/tests/test_technique_scoring.py

Lightweight unit tests for:

- component weights
- valid score range
- unknown predicted shot failure
- invalid sequence shape failure

## ml/artifacts/phase10/ideal_template_schema.json

Machine-readable ideal template schema. It stores shot-specific expected ranges for measurable features.

## ml/artifacts/phase10/technique_score_report.json

Main structured scoring report. It includes summary metrics and detailed per-sample component/deviation data.

## ml/artifacts/phase10/technique_scores.csv

Flat table for inspection and analysis.

# 🔄 Data Flow

```text
X_train_sequence.npy
y_train_sequence.npy
train_temporal_index.csv
metadata.csv
→ build shot-specific ideal templates
```

```text
X_test_sequence.npy
Phase 8 selected-model test predictions
ideal templates
→ score each predicted shot
→ write component scores and deviation summaries
```

The train split builds templates. The test split is scored. Validation/test data is not used to define ideal behavior.

# ⚠️ Common Mistakes / Pitfalls

- Treating model confidence as technique score
- Building templates from the test split
- Returning only a total score without component explanations
- Overclaiming that v1 templates are professional biomechanical truth
- Making scoring too complex before feedback and inference exist
- Ignoring invalid tensor shapes or non-finite values

# 💡 Key Engineering Decisions

## Rule-Based First

A learned technique scorer would require labeled technique scores from coaches. Those labels do not exist yet. Rule-based scoring is more honest, explainable, and maintainable for v1.

## Train-Split Templates

Templates are built from train data only to avoid leaking holdout behavior into scoring references.

## Component Scores Instead of One Opaque Number

A single score is easy to display but not useful for coaching. Component scores are the bridge to Phase 11 feedback.

## Confidence Kept Separate

Classifier confidence is stored for traceability but is not part of the scoring formula.

# 📘 What I Should Write in Notes

- Technique scoring is not classification confidence.
- Phase 10 compares measurable movement features against shot-specific references.
- V1 templates are train-split-derived because professional references are not available yet.
- Component scores make feedback possible.
- The score is interpretable but not a certified coaching grade.
- Phase 11 depends on deviation summaries and weakest components.

# 🧠 Personal Learning Insights

The key ML engineering lesson is that downstream intelligence should not blindly reuse model probability. A production AI system needs semantic separation between recognition, segmentation, scoring, and feedback.

Another important lesson is honesty about label quality. Since coach-certified technique labels do not exist yet, rule-based scoring is the right first version. It is less flashy than a learned scorer, but it is more defensible.

# 🚀 Future Impact

Phase 10 prepares:

- Phase 11 feedback generation
- Phase 12 inference response format
- future coach-reviewed scoring calibration
- future UI score breakdowns
- future personalized improvement tracking

The feedback engine can now say why a shot score was low, not just what shot was predicted.
