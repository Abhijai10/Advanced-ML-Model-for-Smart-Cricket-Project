# Smart Cricket Production Readiness

## Current Verdict

Smart Cricket is now a stronger product prototype with production-oriented API boundaries, repeatable tests, CI scaffolding, and a polished React app shell.

It should not be described as fully production-ready yet. The remaining blockers are external or data-dependent:

- Supabase project selection, secrets, and server-side persistence need real deployment credentials.
- Real-world model readiness requires a larger, player-held-out dataset and coach validation.
- Production TTS should be connected to a real provider if spoken narration is required outside macOS/local demos.
- Browser end-to-end tests should run in CI after the deployed API/frontend URLs exist.

## Implemented Hardening

- `POST /analyze` analyzes uploaded bytes only.
- Dataset-sample analysis is isolated behind disabled-by-default `POST /dev/analyze-dataset`.
- Uploads are size-limited, extension-checked, byte-signature checked, and probed as real video containers.
- Video duration and resolution limits are environment configurable.
- Readiness is separate from liveness via `GET /ready`.
- Readiness checks checkpoint, scaler, schemas, technique templates, pose model, temp storage, and auth configuration.
- Request IDs are attached to responses and error payloads.
- Analysis requests can require Supabase JWTs by setting `SMART_CRICKET_REQUIRE_AUTH=true` and `SUPABASE_JWT_SECRET`.
- Basic in-memory rate limiting protects single-process deployments and local demos.
- Voice artifacts are unique per request and exposed through `/audio/<filename>`.
- UI duration uses backend timing from source video timestamps when available.
- Frontend sends Supabase access tokens when a user is signed in.

## Environment

Use `.env.example` as the source contract.

Important variables:

- `SMART_CRICKET_CORS_ORIGINS`
- `SMART_CRICKET_REQUIRE_AUTH`
- `SUPABASE_JWT_SECRET`
- `SMART_CRICKET_ENABLE_DEV_DATASET_ENDPOINTS`
- `SMART_CRICKET_RATE_LIMIT_PER_MINUTE`
- `SMART_CRICKET_MAX_UPLOAD_BYTES`
- `SMART_CRICKET_MAX_VIDEO_DURATION_SECONDS`
- `SMART_CRICKET_MAX_VIDEO_PIXELS`
- `SMART_CRICKET_AUDIO_OUTPUT_DIR`

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

The current frontend can save analysis history directly under owner-scoped RLS. For stricter production integrity, move history creation to the backend with a Supabase service role key stored only on the server, so clients cannot submit forged `full_result` payloads.
