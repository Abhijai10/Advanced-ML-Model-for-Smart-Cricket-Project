# Phase 11 — Deep Interview Pack

# Question

What problem did Phase 11 solve?

## Short Answer

It converted measurable technique scores and deviations into human-readable coaching feedback.

## Deep Technical Explanation

Phase 10 produced structured scoring outputs: component scores, feature deviations, and recommendations. Phase 11 turns those into detected issues, coaching tips, detailed feedback, spoken feedback, and debug metadata.

## Engineering Reasoning

A classifier and score are useful, but a user needs actionable guidance. Phase 11 bridges the gap between analytics and coaching.

## Why This Decision Was Taken

The roadmap requires feedback after technique scoring because feedback must be grounded in measurable issues.

## Tradeoffs / Risks / Limitations

The feedback depends on Phase 10 template quality. If scoring templates are weak, feedback quality also suffers.

## Important Engineering Insight

Feedback should come from evidence, not from the shot label alone.

# Question

Why is the feedback engine rule-based?

## Short Answer

Because rule-based feedback is explainable, editable, and appropriate for v1.

## Deep Technical Explanation

The system maps feature deviations to predefined feedback rules. Each rule contains an issue, why it matters, and a coaching tip.

This is safer than using a language model or learned feedback model before the project has coach-reviewed feedback labels.

## Engineering Reasoning

Rule-based feedback gives deterministic behavior and clear debugging.

## Why This Decision Was Taken

The roadmap explicitly says not to rely only on ML for feedback and to keep rules editable.

## Tradeoffs / Risks / Limitations

Rules can feel repetitive and may miss nuanced coaching observations.

## Important Engineering Insight

In early production ML systems, controlled rules often create better trust than opaque generation.

# Question

How is feedback linked to measurable features?

## Short Answer

Each detected issue is created from a Phase 10 feature deviation.

## Deep Technical Explanation

The feedback engine inspects feature-level deviation scores. If a feature score is below the issue threshold, it creates a detected issue containing:

- component name
- feature name
- statistic
- severity
- evidence values
- issue text
- why it matters
- coaching tip

## Engineering Reasoning

This makes feedback auditable. A developer can trace every coaching tip back to a measured feature.

## Why This Decision Was Taken

The roadmap requires explainable feedback from biomechanical thresholds and template deviation interpretation.

## Tradeoffs / Risks / Limitations

Feature-linked feedback is only as accurate as the underlying features and templates.

## Important Engineering Insight

Explainability requires traceability, not just friendly language.

# Question

Why are detailed feedback and spoken feedback separate?

## Short Answer

Detailed feedback is for reports/UI, while spoken feedback is short and TTS-friendly.

## Deep Technical Explanation

Detailed feedback includes score band, strong areas, weak areas, and primary focus. Spoken feedback compresses this into a short sentence that can later be converted into voice.

## Engineering Reasoning

Text that is good for a report is often too long for voice output. Separating them avoids future rewrites.

## Why This Decision Was Taken

The roadmap says feedback should generate short and detailed outputs separately and make output TTS-friendly.

## Tradeoffs / Risks / Limitations

Spoken feedback loses detail by design.

## Important Engineering Insight

Output format should match the downstream channel.

# Question

How does Phase 11 avoid generic feedback?

## Short Answer

It chooses tips from detected feature deviations rather than only from predicted shot class.

## Deep Technical Explanation

The engine does not say "bad shot." It identifies the weakest measured issues, such as hip-rotation velocity or head stability, and explains why that specific issue matters.

## Engineering Reasoning

Generic feedback is not useful. Specific feedback helps users understand what to adjust.

## Why This Decision Was Taken

The system goal is coaching intelligence, not only classification.

## Tradeoffs / Risks / Limitations

Highly specific feedback can be wrong if the template or feature measurement is wrong.

## Important Engineering Insight

Specificity improves usefulness, but it must remain tied to evidence.

# Question

What does debug metadata provide?

## Short Answer

It explains why and how feedback was produced.

## Deep Technical Explanation

Each output stores metadata such as feedback version, source phase, issue threshold, number of detected issues, score band, and prediction correctness.

## Engineering Reasoning

Debug metadata makes the feedback engine auditable and easier to validate in Phase 12.

## Why This Decision Was Taken

Feedback should be transparent because it influences user coaching.

## Tradeoffs / Risks / Limitations

Metadata increases output size, but the clarity is worth it.

## Important Engineering Insight

Production feedback systems need observability, not just text output.

# Question

How does Phase 11 prepare Phase 12?

## Short Answer

It provides the final feedback object that Phase 12 can include in an end-to-end inference result.

## Deep Technical Explanation

Phase 12 needs to combine segmentation, prediction, scoring, and feedback into one structured pipeline. Phase 11 defines the feedback payload shape before that integration.

## Engineering Reasoning

By completing feedback as an independent module first, Phase 12 can focus on orchestration instead of inventing feedback logic.

## Why This Decision Was Taken

The roadmap builds modular subsystems before combining them into inference.

## Tradeoffs / Risks / Limitations

Phase 11 currently uses Phase 10 artifact outputs, not live video inference yet.

## Important Engineering Insight

End-to-end systems are easier to build when each module has a stable contract.
