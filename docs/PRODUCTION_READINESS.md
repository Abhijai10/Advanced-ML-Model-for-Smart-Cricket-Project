# Smart Cricket Production Readiness

## Current Verdict

Smart Cricket is now a stronger product prototype with production-oriented API boundaries, repeatable tests, CI scaffolding, and a polished React app shell.

It should not be described as fully production-ready yet. The remaining blockers are external or data-dependent:

- Supabase project selection, secrets, and server-side persistence need real deployment credentials.
- Real-world model readiness requires a larger, player-held-out dataset and coach validation.
- Production TTS should be connected to a real provider if spoken narration is required outside macOS/local demos.
- Browser end-to-end tests should run in CI after the deployed API/frontend URLs exist.
- Real-video Phase 12 validation still requires a legally usable batting-video fixture. Mocked API tests are not evidence of real inference quality.

## Implemented Hardening

- `POST /analyze` analyzes uploaded bytes only.
- Dataset-sample analysis is isolated behind disabled-by-default `POST /dev/analyze-dataset`.
- Uploads are size-limited, extension-checked, byte-signature checked, and probed as real video containers.
- Video duration and resolution limits are environment configurable.
- Readiness is separate from liveness via `GET /ready`.
- `GET /health` is lightweight process liveness only; `GET /ready` performs dependency checks.
- Readiness checks checkpoint, scaler, schemas, technique templates, pose model, temp storage, auth configuration, production persistence, signing secret, evidence storage, and rate-limit backend when those are required.
- `GET /capabilities` exposes non-secret frontend capability flags for auth, feedback, model-improvement participation, evidence retention, TTS mode, upload size, recording duration, and accepted video extensions.
- Request IDs are attached to responses and error payloads.
- Analysis requests can require Supabase JWTs by setting `SMART_CRICKET_REQUIRE_AUTH=true`. Legacy HS256 verification uses `SUPABASE_JWT_SECRET`; modern asymmetric Supabase tokens use `SUPABASE_URL` for JWKS plus `SUPABASE_JWT_AUDIENCE` and `SUPABASE_JWT_ISSUER`.
- Local auth tests cover HS256, RS256, ES256, malformed signatures, empty/invalid JWKS responses, route-level JWKS outage behavior, and key-cache refresh on unknown `kid`. Live Supabase issuer/audience/key-rotation verification remains an external deployment gate.
- Rate limiting now uses an explicit adapter contract with authenticated user keys when auth has resolved and IP keys otherwise. The memory backend protects single-process deployments and local demos; production readiness rejects memory mode and expects Redis or a verified gateway/WAF. Trusted proxy parsing uses the configured proxy-hop count instead of blindly trusting the first `X-Forwarded-For` value.
- Voice artifacts are unique per request and exposed through signed `/audio/<filename>` links. Production/staging require `SMART_CRICKET_AUDIO_SIGNING_SECRET`; the local fallback is test/development only.
- UI duration uses backend timing from source video timestamps when available.
- Frontend sends Supabase access tokens when a user is signed in.
- Frontend no longer writes model results into Supabase directly; authenticated history writes are local-only until server-side persistence is connected.
- Backend-owned history persistence is available when `SUPABASE_URL` and server-only `SUPABASE_SERVICE_ROLE_KEY` are configured. Missing credentials are treated as a safe no-op, not a frontend write fallback.
- Controlled-beta analysis feedback can be submitted through `POST /feedback` with prediction correctness, corrected label, technique rating, tip flags, notes, and explicit model-improvement consent.
- General usability/bug/feature feedback is separate at `POST /product-feedback` and never enters model-training review.
- Feedback is marked as user-reported provenance. It becomes a review candidate only when the user opted in before analysis and protected evidence was retained successfully. It must go through human/expert review before any retraining dataset changes.
- Model-improvement participation is default-disabled. When `SMART_CRICKET_ALLOW_MODEL_IMPROVEMENT_PARTICIPATION=false`, the backend records retention requests as disabled and the frontend disables consent controls.
- Consent withdrawal now disables training eligibility immediately and attempts provider-aware evidence deletion using the stored `evidence_metadata.storage_provider`, not the current runtime provider setting.
- Failed evidence deletion is marked `deletion_pending` for retry by `scripts/cleanup_evidence.py`; pending/deleted/withdrawn rows are not reviewable or exportable.
- Reviewer/admin operations are available through `scripts/review_feedback_candidates.py`: list pending candidates, optionally issue short-lived reviewer evidence access, and record approve/reject decisions with reviewer provenance, label quality, split assignment, safety flags, and training inclusion version.
- Supabase retained evidence can be served to trusted reviewers through short-lived Storage signed URLs generated server-side by the evidence provider. Live Supabase Storage verification still requires a private bucket and project credentials.
- Voice output degrades to text-only metadata if TTS generation fails, so analysis does not fail just because audio generation is unavailable.
- Analysis responses include `analysis_quality.status` with `ok`, `uncertain`, or `insufficient_quality` based on configurable confidence and clean-pose-frame thresholds.
- ML evaluation tooling now supports player-disjoint manifest generation plus calibration/reliability reports for future player-held-out predictions. This does not change the current model validity blocker.

## Environment

Use `.env.example` as the source contract.

Important variables:

- `SMART_CRICKET_CORS_ORIGINS`
- `SMART_CRICKET_REQUIRE_AUTH`
- `SUPABASE_JWT_SECRET`
- `SUPABASE_JWT_AUDIENCE`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (server only; never expose to frontend)
- `SMART_CRICKET_ENABLE_DEV_DATASET_ENDPOINTS`
- `SMART_CRICKET_RATE_LIMIT_PER_MINUTE`
- `SMART_CRICKET_RATE_LIMIT_BACKEND`
- `SMART_CRICKET_REDIS_URL`
- `SMART_CRICKET_TRUSTED_PROXY_HOPS`
- `SMART_CRICKET_ANALYSIS_EXECUTION_TIMEOUT_SECONDS`
- `SMART_CRICKET_PERSISTENCE_TIMEOUT_SECONDS`
- `SMART_CRICKET_MAX_UPLOAD_BYTES`
- `SMART_CRICKET_MAX_VIDEO_DURATION_SECONDS`
- `SMART_CRICKET_MAX_VIDEO_PIXELS`
- `SMART_CRICKET_AUDIO_OUTPUT_DIR`
- `SMART_CRICKET_AUDIO_SIGNING_SECRET`
- `SMART_CRICKET_EVIDENCE_STORAGE_BACKEND`
- `SMART_CRICKET_EVIDENCE_SUPABASE_BUCKET`
- `SMART_CRICKET_ALLOW_MODEL_IMPROVEMENT_PARTICIPATION`
- `VITE_MAX_RECORDING_SECONDS`

## Verification

Local setup:

```bash
scripts/setup.sh
```

Local test run:

```bash
scripts/test.sh
```

Focused API safety tests:

```bash
python -m pytest backend/api/tests/test_api.py
```

## Supabase Notes

The migration in `supabase/migrations/202608040001_smart_cricket_app_schema.sql` enables RLS and grants authenticated Data API access explicitly. This is required for new Supabase projects because public tables may no longer be exposed automatically.

The current frontend reads history from owner-scoped RLS tables but does not write analysis results directly. The follow-up migration `20260804080002_secure_trusted_analysis_and_feedback.sql` also revokes browser `INSERT` and `UPDATE` access to `analysis_sessions`, so trusted analysis history is server-created only.

The follow-up migration `20260812135543_product_feedback_and_evidence_lifecycle.sql` creates `public.product_feedback` for usability/bug/feature feedback and expands analysis/evidence states such as `disabled` and `deletion_pending`. This keeps general product reports outside `analysis_feedback` and outside ML retraining workflows.

Authenticated history is durable only when the backend has Supabase server credentials. The frontend must never receive a service-role key. Production setup requires:

- explicit Supabase project selection;
- `SUPABASE_URL` and a server-only service role or secret key;
- backend-only inserts immediately after verified inference;
- no service-role or secret key exposure to frontend bundles;
- integration tests against a real or local Supabase instance proving owner reads, browser insert/update denial, and service-role insert success.

## Feedback and Continual Learning

The feedback endpoint is safe for a controlled beta only when persistence is configured. It returns an explicit failure when feedback cannot be saved. Model-improvement candidates require an authenticated user, a verified server-created analysis session owned by that user, pre-analysis evidence-retention consent, successfully retained protected evidence, unexpired evidence, and explicit feedback consent. User feedback may be useful for triage, but it is not ground truth. The production retraining process must:

- retain consent and provenance for every clip/result;
- deduplicate clip hashes before review;
- separate train/validation/test users and clips;
- assign label-quality scores;
- resolve disagreement through qualified human review;
- allow AI-assisted review only for triage, anomaly detection, or reviewer summarization;
- version every dataset, feature schema, scaler, checkpoint, and prompt/rule template;
- gate retraining on minimum data quality and held-out performance;
- support rollback when drift or unsafe advice is detected.

## Privacy, Retention, and Storage

Production must define retention periods for uploaded clips, generated audio, feedback records, and derived pose/features. Audio is currently served through signed local `/audio/<filename>?expires=...&signature=...` links with cleanup support; protected object storage is still required before production use. Users need deletion/export flows, consent withdrawal behavior, and a documented incident-response path.

The current implementation supports a protected local development evidence provider and a Supabase Storage adapter interface with mocked/code tests. Evidence deletion is provider-aware based on stored metadata, and expired/deletion-pending evidence can be retried with:

```bash
python scripts/cleanup_evidence.py --execute
```

Run without `--execute` for a dry run. Live Supabase Storage verification remains an external deployment gate.

## ML Evaluation Tooling

Use `python -m ml.src.evaluation.player_disjoint_split` for future manifests with player IDs, and `python -m ml.src.evaluation.evaluate_predictions` for player-held-out prediction reports. The evaluation output includes reliability data, ECE, Brier score, confidence rejection curves, confusion matrix, and class-wise metrics. These reports are release evidence only when run on larger, representative, coach-reviewed data.
