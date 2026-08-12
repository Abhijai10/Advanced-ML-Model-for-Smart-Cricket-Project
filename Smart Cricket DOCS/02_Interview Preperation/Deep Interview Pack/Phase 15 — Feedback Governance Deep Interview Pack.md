# Phase 15 — Feedback Governance Deep Interview Pack

## Why is user feedback not automatically ground truth?

Short answer: A user report is useful evidence, but it may be wrong, incomplete, biased, or unsupported by video. Smart Cricket treats it as a review candidate, not a training label.

Deep answer: The system only considers feedback for model improvement when it is attached to a server-created analysis, has explicit model-improvement consent, has retained protected evidence, has complete provenance, has not expired, and has not been withdrawn or deleted. A reviewer must inspect the evidence and record a decision before the row can become dataset-eligible.

## How does the review workflow work?

Short answer: Pending candidates are listed, reviewed with protected evidence, approved or rejected, and only approved eligible rows are exported.

Deep answer:

1. `POST /feedback` stores user-reported feedback only after verifying ownership of `analysis_session_id`.
2. `scripts/review_feedback_candidates.py list` returns pending candidates with reviewable evidence.
3. `scripts/review_feedback_candidates.py list --include-access` can request short-lived reviewer access from the stored evidence provider.
4. `scripts/review_feedback_candidates.py decision` records reviewer ID, label, quality score, second-review flag, notes, safety flags, split assignment, and training inclusion version.
5. `scripts/export_feedback_candidates.py` exports only approved, eligible, unexpired, non-withdrawn rows.

## Why separate product feedback from analysis feedback?

Short answer: Product feedback is about the app; analysis feedback is about model output. Mixing them can pollute training data.

Deep answer: General bug reports and feature requests now go to `product_feedback`. That table has no prediction, corrected label, evidence object, or training eligibility fields. This prevents a usability note such as “camera button is confusing” from entering a machine-learning review/export path.

## What prevents privacy mistakes?

Short answer: Consent, provider-aware deletion, expiration cleanup, and export filters.

Deep answer: Evidence metadata records the storage provider, object path, checksum, user ID, analysis session ID, consent version, and retention deadline. Withdrawal disables training eligibility immediately and attempts physical deletion. If deletion fails, the row is marked `deletion_pending` and remains excluded from reviewer export.

## What is still not production-complete?

Short answer: The code workflow exists, but real human review operations and live Supabase verification still need external setup.

Deep answer: The repository has local/mock tests for gating, evidence lifecycle, reviewer commands, and export filtering. Public production still requires real Supabase storage/RLS verification, trained reviewer accounts, coach validation of labels and advice, privacy/legal approval, and monitoring of the review queue.
