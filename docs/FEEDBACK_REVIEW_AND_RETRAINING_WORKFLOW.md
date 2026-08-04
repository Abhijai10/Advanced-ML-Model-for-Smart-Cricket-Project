# Smart Cricket Feedback Review and Retraining Workflow

User feedback is product evidence, not ground truth. The beta feedback system now binds feedback to a server-created `analysis_session_id` before model-improvement consent can enter the review queue. The client submits only the user's judgement: prediction correctness, optional corrected shot, technique-feedback rating, tip flags, notes, and explicit consent. The backend derives clip hash, original prediction, request ID, model provenance, feature contract, and pipeline version from the trusted analysis record.

Anonymous or unbound reports must not become training data. They may be treated only as product feedback when a separate durable product-feedback path exists.

## Review Pipeline

1. Export candidate rows from `analysis_feedback` where `accepted_for_review = true`, `consent_to_model_improvement = true`, and `review_status = 'candidate'`.
2. Deduplicate by `clip_hash`, `model_version`, `pipeline_version`, and user where applicable.
3. Exclude any row or clip without consent, unclear provenance, privacy risk, unsafe content, or missing source metadata.
4. Have a qualified reviewer inspect the retained protected evidence, model result, corrected label, and user notes. In the current local scaffold, evidence storage is recorded as `not_retained` unless protected storage is configured and verified.
5. Assign label-quality status: `approved`, `needs_second_review`, `rejected`, or `unsafe`.
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
- protected evidence status and object path when configured;
- clip hash;
- prediction, corrected shot, and confidence;
- feedback rating and tip flags;
- consent status and timestamp;
- model/pipeline versions;
- reviewer decision and notes;
- dataset split assignment after adjudication.

No training script should read raw `analysis_feedback` directly. Training must consume only an adjudicated dataset manifest.

## Evidence Retention

The safe target architecture is protected server-side storage with signed reviewer access, consent versioning, retention deadlines, withdrawal/deletion status, reviewer-access audit fields, and no public raw-clip URLs. Where Supabase Storage or another protected store is unavailable, the system records `storage_status = 'not_retained'` and the candidate is not complete evidence for model improvement.

Non-consented clips are deleted after inference and must not be retained for model improvement. Consented evidence becomes reviewable only after storage is configured and verified with server credentials.

## Candidate Export Helper

Use the review helper only from a trusted server or local maintainer machine with server credentials:

```bash
python scripts/export_feedback_candidates.py --output exports/feedback_candidates.csv
```

The exported CSV is a reviewer queue, not a training dataset.
