# Phase 11 — Feedback Engine

# 🎯 Goal of the Phase

Phase 11 converts measurable technique problems into human-readable coaching feedback.

Previous phases produced:

```text
predicted shot
technique score
component scores
feature deviations
```

Phase 11 transforms those structured signals into:

```text
detected issues
coaching tips
detailed feedback
spoken feedback
debug metadata
```

This phase is what makes Smart Cricket start to feel like a coach instead of just a classifier.

# 🧠 Core Concepts Introduced

## Rule-Based Feedback

The feedback engine is rule-based because the system already has structured evidence from Phase 10. It does not need a language model or another ML model to generate v1 feedback.

Rules map measurable issues to:

- what went wrong
- why it matters
- how to improve

This keeps feedback explainable and editable.

## Feature-Linked Issues

Every detected issue is linked to a source feature deviation. For example, if `head_over_base_offset` is outside the template range, the feedback can say the head moved away from the stable base.

This prevents generic advice. The engine does not simply say:

```text
bad shot
```

It explains:

```text
Your hip-rotation velocity moved outside the expected range.
Unstable rotation speed can disturb balance and shot timing.
Use controlled hip rotation so the swing stays balanced.
```

## Detailed Feedback vs Spoken Feedback

The system generates two output layers:

- detailed feedback for reports and UI
- spoken feedback for future TTS

Detailed feedback includes more context. Spoken feedback is shorter, cleaner, and easier to convert into voice later.

## Debug Metadata

Each feedback output contains debug metadata such as:

- source phase
- feedback version
- issue threshold
- number of detected issues
- score band
- prediction correctness

This makes feedback auditable and easier to troubleshoot.

# 🏗️ System-Level Importance

Phase 11 sits between scoring and inference.

The pipeline now looks like:

```text
temporal features
→ model prediction
→ shot segmentation
→ technique scoring
→ feedback generation
```

Phase 12 can now assemble these pieces into one offline inference result.

# 📂 Important Files / Scripts

## ml/src/feedback/feedback_schema.py

Defines structured dataclasses for detected issues and feedback outputs.

## ml/src/feedback/feedback_templates.py

Stores editable coaching text templates for features and components.

## ml/src/feedback/feedback_rules.py

Selects important issues from Phase 10 deviations and assigns severity.

## ml/src/feedback/feedback_engine.py

Main engine that loads Phase 10 scoring output and writes Phase 11 feedback artifacts.

## ml/src/feedback/validate_feedback_engine.py

Validation entry point for generating and checking feedback artifacts.

## ml/src/feedback/tests/test_feedback_engine.py

Tests severity rules, direction handling, required output layers, and high-score maintenance feedback.

## ml/artifacts/phase11/sample_feedback_outputs.json

Main machine-readable feedback artifact.

## ml/artifacts/phase11/feedback_outputs.csv

Flat inspection table for feedback outputs.

## ml/artifacts/phase11/feedback_report.md

Human-readable report summarizing feedback validation and examples.

# 🔄 Data Flow

```text
ml/artifacts/phase10/technique_score_report.json
→ feedback rules
→ coaching templates
→ feedback outputs
→ phase11 artifacts
```

Phase 11 does not modify models, tensors, scoring templates, or dataset files.

# ⚠️ Common Mistakes / Pitfalls

- generating feedback from class labels alone
- giving generic advice without feature evidence
- using harsh labels like "bad shot"
- generating long text that is not TTS-friendly
- hiding why feedback was produced
- overclaiming biomechanical certainty from v1 templates

# 💡 Key Engineering Decisions

## Rule-Based First

The project does not need a generative feedback model yet. Rule-based feedback is more controllable, explainable, and easy to review.

## Separate Detailed and Spoken Outputs

UI/report feedback and voice feedback have different needs. Separating them now makes Phase 14 easier later.

## Coach-Like but Evidence-Grounded

The tone is coaching-oriented, but each issue is tied to measurable deviations.

## Maintenance Feedback for Strong Shots

When no issue crosses the threshold, the system gives maintenance guidance instead of inventing a flaw.

# 📘 What I Should Write in Notes

- Phase 11 converts scoring evidence into coaching language.
- Feedback is generated from measurable deviations, not generic labels.
- Detailed feedback and spoken feedback are separate output layers.
- Debug metadata explains why feedback was generated.
- Phase 11 prepares Phase 12 inference and Phase 14 voice output.

# 🧠 Personal Learning Insights

The key lesson is that intelligent feedback needs an evidence layer. A feedback engine should not hallucinate coaching advice from a prediction alone.

Another lesson is that language design is part of ML engineering. The output must be useful, short when spoken, and precise enough to defend technically.

# 🚀 Future Impact

Phase 11 prepares:

- Phase 12 end-to-end inference
- Phase 13 API response structure
- Phase 14 voice output
- UI display of issue lists and tips
- future coach-reviewed feedback calibration

The system can now produce a complete coaching-style explanation from structured ML outputs.
