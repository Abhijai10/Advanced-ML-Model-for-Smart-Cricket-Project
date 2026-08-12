# Smart Cricket Feedback Review and Retraining Workflow

User feedback is product evidence, not ground truth. The beta feedback system now binds feedback to a server-created `analysis_session_id` before model-improvement consent can enter the review queue. The client submits only the user's judgement: prediction correctness, optional corrected shot, technique-feedback rating, tip flags, notes, and explicit consent. The backend derives clip hash, original prediction, request ID, model provenance, feature contract, and pipeline version from the trusted analysis record.

Anonymous or unbound reports must not become training data. General usability, bug, and feature reports are stored in `public.product_feedback` through `POST /product-feedback`; they do not share the `analysis_feedback` schema and are not exported for model training.

## Review Pipeline

1. List pending candidates from `analysis_feedback` where `accepted_for_review = true`, `consent_to_model_improvement = true`, `review_status = 'candidate'`, `dataset_eligibility_status = 'pending_review'`, `storage_status = 'stored'`, evidence has not expired, and neither `withdrawn_at` nor `deleted_at` is set.
2. Have a qualified reviewer inspect the retained protected evidence, model result, corrected label, and user notes. Evidence is reviewable only when the protected object path, checksum, user ID, analysis session ID, consent version, storage provider, and retention deadline are complete.
3. Record reviewer ID, reviewer label, label-quality score, second-review flag, disagreement notes, rejection reason, safety flag, split assignment, and training inclusion version.
4. Approve only when the evidence supports the label and there is no unsafe-content flag. Rejected/unsafe rows become non-eligible.
5. Export only adjudicated rows from `analysis_feedback` where `accepted_for_review = true`, `consent_to_model_improvement = true`, `review_status = 'approved'`, `dataset_eligibility_status = 'eligible'`, `storage_status = 'stored'`, and neither `withdrawn_at` nor `deleted_at` is set.
6. Deduplicate by `clip_hash`, `model_version`, `pipeline_version`, and user where applicable.
7. Exclude any row or clip without consent, unclear provenance, privacy risk, unsafe content, or missing source metadata.
8. Resolve disagreements through a second human review. AI tools may summarize or flag inconsistencies, but they are never the deciding label authority.
9. Keep train, validation, and test users/clips isolated. A clip reported by a validation/test user must not leak into training.
10. Version the accepted dataset, feature schema, scaler, checkpoint, label map, scoring templates, and feedback rules together.
11. Retrain only after release gates pass: minimum data diversity, player-held-out metrics, calibration, safety review, regression tests, and rollback plan.
12. Monitor drift, low-confidence rate, unsafe-tip flags, duplicate reports, and class imbalance after beta release.

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

The safe target architecture is protected server-side storage with signed reviewer access, consent versioning, retention deadlines, withdrawal/deletion status, reviewer-access audit fields, and no public raw-clip URLs. Where Supabase Storage or another protected store is unavailable, the system records `storage_status = 'not_retained'`, `failed`, or `disabled`, and the candidate is not complete evidence for model improvement.

Non-consented clips are deleted after inference and must not be retained for model improvement. Consented evidence becomes reviewable only after storage is configured and verified with server credentials. Consent withdrawal immediately disables dataset eligibility and attempts evidence deletion through the stored provider ID. If physical deletion fails, the record is marked `deletion_pending`; cleanup retries may continue, but the row remains non-reviewable and non-exportable.

## Candidate Export Helper

Use reviewer helpers only from a trusted server or local maintainer machine with server credentials. First list pending candidates:

```bash
python scripts/review_feedback_candidates.py list
python scripts/review_feedback_candidates.py list --include-access
```

Then record a reviewer decision:

```bash
python scripts/review_feedback_candidates.py decision \
  --feedback-id <feedback-row-id> \
  --reviewer-id <reviewer-user-id> \
  --decision approve \
  --reviewer-label cover_drive \
  --label-quality-score 0.95 \
  --split-assignment train \
  --training-inclusion-version dataset-2026-08
```

Finally export approved, eligible rows:

```bash
python scripts/export_feedback_candidates.py --output exports/feedback_candidates.csv
```

The exported CSV is an adjudicated manifest input, not a raw training dataset. Metadata-only, expired, withdrawn, deleted, unreviewed, unsafe, or rejected feedback is excluded.

## Evidence Cleanup Helper

Expired and deletion-pending evidence should be retried from a trusted server or maintainer machine:

```bash
python scripts/cleanup_evidence.py
python scripts/cleanup_evidence.py --execute
```

The first command is a dry run. The execute mode deletes through the stored evidence provider and marks analysis/feedback rows so training eligibility remains disabled.
