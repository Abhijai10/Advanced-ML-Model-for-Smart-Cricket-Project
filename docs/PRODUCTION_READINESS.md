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
- `GET /health` no longer hard-codes inference readiness; it reports an honest boolean derived from readiness checks.
- Readiness checks checkpoint, scaler, schemas, technique templates, pose model, temp storage, and auth configuration.
- Request IDs are attached to responses and error payloads.
- Analysis requests can require Supabase JWTs by setting `SMART_CRICKET_REQUIRE_AUTH=true` and `SUPABASE_JWT_SECRET`.
- Basic in-memory rate limiting protects single-process deployments and local demos.
- Voice artifacts are unique per request and exposed through `/audio/<filename>`.
- UI duration uses backend timing from source video timestamps when available.
- Frontend sends Supabase access tokens when a user is signed in.
- Frontend no longer writes model results into Supabase directly; authenticated history writes are local-only until server-side persistence is connected.
- Backend-owned history persistence is available when `SUPABASE_URL` and server-only `SUPABASE_SERVICE_ROLE_KEY` are configured. Missing credentials are treated as a safe no-op, not a frontend write fallback.
- Controlled-beta feedback can be submitted through `POST /feedback` with prediction correctness, corrected label, technique rating, tip flags, notes, and explicit model-improvement consent.
- Feedback is marked as user-reported provenance and candidate material only. It must go through human/expert review before any retraining dataset changes.
- Voice output degrades to text-only metadata if TTS generation fails, so analysis does not fail just because audio generation is unavailable.
- Analysis responses include `analysis_quality.status` with `ok`, `uncertain`, or `insufficient_quality` based on configurable confidence and clean-pose-frame thresholds.

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
- `SMART_CRICKET_TRUSTED_PROXY_HOPS`
- `SMART_CRICKET_PERSISTENCE_TIMEOUT_SECONDS`
- `SMART_CRICKET_MAX_UPLOAD_BYTES`
- `SMART_CRICKET_MAX_VIDEO_DURATION_SECONDS`
- `SMART_CRICKET_MAX_VIDEO_PIXELS`
- `SMART_CRICKET_AUDIO_OUTPUT_DIR`
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

The current frontend reads history from owner-scoped RLS tables but does not write analysis results directly. This prevents browser clients from storing forged model results as trusted history.

Authenticated history is durable only when the backend has Supabase server credentials. The frontend must never receive a service-role key. Production setup requires:

- explicit Supabase project selection;
- `SUPABASE_URL` and a server-only service role or secret key;
- backend-only inserts immediately after verified inference;
- no service-role or secret key exposure to frontend bundles;
- integration tests against a real or local Supabase instance.

## Feedback and Continual Learning

The feedback endpoint is safe for a controlled beta, not automatic learning. User feedback may be useful for triage, but it is not ground truth. The production retraining process must:

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

Production must define retention periods for uploaded clips, generated audio, feedback records, and derived pose/features. Audio is currently served from `/audio/<filename>` for local/demo use; protected object storage or signed URLs are required before production use. Users need deletion/export flows, consent withdrawal behavior, and a documented incident-response path.
