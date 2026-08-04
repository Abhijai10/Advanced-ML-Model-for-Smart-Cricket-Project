# Smart Cricket Feedback Review and Retraining Workflow

User feedback is product evidence, not ground truth. The beta feedback system captures prediction correctness, optional corrected shot, technique-feedback rating, tip flags, notes, clip hash, model/pipeline version, request ID, auth presence, and explicit consent.

## Review Pipeline

1. Export candidate rows from `analysis_feedback` where `accepted_for_review = true`, `consent_to_model_improvement = true`, and `review_status = 'candidate'`.
2. Deduplicate by `clip_hash`, `model_version`, `pipeline_version`, and user where applicable.
3. Exclude any row or clip without consent, unclear provenance, privacy risk, unsafe content, or missing source metadata.
4. Have a qualified reviewer inspect the clip, model result, corrected label, and user notes.
5. Assign label-quality status: `accepted`, `needs_second_review`, `rejected`, or `unsafe`.
6. Resolve disagreements through a second human review. AI tools may summarize or flag inconsistencies, but they are never the deciding label authority.
7. Keep train, validation, and test users/clips isolated. A clip reported by a validation/test user must not leak into training.
8. Version the accepted dataset, feature schema, scaler, checkpoint, label map, scoring templates, and feedback rules together.
9. Retrain only after release gates pass: minimum data diversity, player-held-out metrics, calibration, safety review, regression tests, and rollback plan.
10. Monitor drift, low-confidence rate, unsafe-tip flags, duplicate reports, and class imbalance after beta release.

## Export Contract

An export job should produce:

- feedback row ID;
- user ID or pseudonymous reviewer-safe ID;
- analysis session ID if available;
- clip hash;
- prediction, corrected shot, and confidence;
- feedback rating and tip flags;
- consent status and timestamp;
- model/pipeline versions;
- reviewer decision and notes;
- dataset split assignment after adjudication.

No training script should read raw `analysis_feedback` directly. Training must consume only an adjudicated dataset manifest.

## Candidate Export Helper

Use the review helper only from a trusted server or local maintainer machine with server credentials:

```bash
python scripts/export_feedback_candidates.py --output exports/feedback_candidates.csv
```

The exported CSV is a reviewer queue, not a training dataset.
