# Phase 15 — Production Hardening Quick Revision Pack

## One-Line Answers

- User feedback is evidence, not ground truth.
- Training candidates require consent, verified analysis binding, retained evidence, and human review.
- Browser clients must not insert trusted analysis history.
- Supabase service-role credentials stay server-side only.
- Private retained evidence is accessed through short-lived signed reviewer URLs.
- Player leakage means the same player appears across train/test splits.
- Calibration checks whether confidence matches real correctness.
- ECE measures the average confidence-vs-accuracy gap.
- Brier score measures probability quality against the true label.
- The current model is engineering-valid, not production-valid.

## 30-Second Architecture Flow

```text
Video
→ MediaPipe pose extraction
→ cleaning / normalization / alignment
→ 60 x 32 temporal tensor
→ GRU shot classifier
→ segmentation and technique scoring
→ feedback engine
→ FastAPI response
→ trusted server persistence
→ optional retained evidence
→ human-reviewed feedback candidates
```

## Key Numbers

- Dataset: 80 samples.
- Tensor: 60 frames by 32 features.
- Classes: 4 shot labels.
- Current split: deterministic, class-balanced, not player-disjoint.
- Production blocker: no legal real raw-video E2E fixture yet.

## Common Pitfalls

- Do not claim confidence is calibrated without calibration evidence.
- Do not call user feedback ground truth.
- Do not let the frontend write trusted analysis rows.
- Do not retain clips after analysis unless consent was given before submission.
- Do not put metadata-only feedback into training exports.
- Do not change `lead_wrist_acceleration` semantics without retraining.

## Last-Day Interview Cheat Sheet

Best project explanation:

Smart Cricket is a layered sports-AI system. It uses pose estimation and temporal sequence modeling for shot recognition, then uses rule-based biomechanics for explainable feedback. The production-hardening work focused on trust boundaries: server-owned history, safe feedback, consented evidence retention, reviewer adjudication, and honest ML limitations.

Strongest honesty point:

The product is close to a restricted internal beta, but not public production-ready because real-video E2E, live Supabase verification, larger player-held-out evaluation, coach validation, deployment, and legal/privacy gates remain external.
