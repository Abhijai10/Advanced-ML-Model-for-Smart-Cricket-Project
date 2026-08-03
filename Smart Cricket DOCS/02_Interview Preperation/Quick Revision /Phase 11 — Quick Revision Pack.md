# Phase 11 — Quick Revision Pack

# Question

What problem did Phase 11 solve?

## Quick Answer

It turned Phase 10 scoring evidence into coaching feedback.
Input: technique score, component scores, feature deviations.
Output: detected issues, tips, detailed feedback, spoken feedback, and debug metadata.

# Question

Why is the feedback engine rule-based?

## Quick Answer

Rule-based feedback is explainable, editable, and safer for v1.
There are no coach-labeled feedback targets yet.
Rules map measurable deviations to issue text, why it matters, and improvement tips.

# Question

How is feedback linked to measurable features?

## Quick Answer

Each issue comes from a Phase 10 feature deviation.
The output stores component name, feature name, statistic, severity, evidence values, and the generated coaching tip.
This makes feedback traceable.

# Question

Why are detailed feedback and spoken feedback separate?

## Quick Answer

Detailed feedback is for UI/reports.
Spoken feedback is short and TTS-friendly.
This prepares Phase 14 voice output without making current feedback too verbose.

# Question

How does Phase 11 avoid generic feedback?

## Quick Answer

It does not generate feedback from shot label alone.
It selects weak measured features and explains the issue.
Example: unstable hip rotation or high head offset, not just "bad shot."

# Question

What does debug metadata provide?

## Quick Answer

It records feedback version, source phase, issue threshold, score band, number of issues, and prediction correctness.
This makes feedback auditable and easier to debug in Phase 12.

# Question

How does Phase 11 prepare Phase 12?

## Quick Answer

It creates the final feedback object that end-to-end inference can return.
Phase 12 can now focus on orchestration:
segmentation → prediction → scoring → feedback.
