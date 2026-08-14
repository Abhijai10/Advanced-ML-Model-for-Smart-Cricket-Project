# Smart Cricket Deployment

## API

Build and run the API container:

```bash
docker compose up --build api
```

The API listens on `http://127.0.0.1:8000`.

Endpoints:

- `GET /health` for liveness
- `GET /ready` for dependency readiness
- `GET /capabilities` for non-secret frontend feature flags
- `POST /analyze` for uploaded video analysis
- `POST /feedback` for verified analysis feedback
- `POST /product-feedback` for general usability/bug/feature feedback
- `POST /analysis/<id>/withdraw-consent` and `DELETE /analysis/<id>/evidence` for consent/evidence lifecycle operations
- `POST /dev/analyze-dataset` for local dataset samples, only when enabled
- `GET /audio/<filename>?expires=...&signature=...` for signed generated audio artifacts

## Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run build
```

Set:

- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

## Production Checklist

- Set `SMART_CRICKET_ENV=staging` for staging and `SMART_CRICKET_ENV=production` for production. Invalid values fail fast.
- Set `SMART_CRICKET_REQUIRE_AUTH=true`.
- Set `SUPABASE_JWT_SECRET` for legacy HS256 projects, or set `SUPABASE_URL` plus issuer/audience values so the verifier can use Supabase JWKS for asymmetric signing keys.
- Set `SUPABASE_JWT_AUDIENCE` and `SUPABASE_JWT_ISSUER` in production.
- Set `SUPABASE_SERVICE_ROLE_KEY` only on the backend. Never expose it to the frontend.
- Set `SMART_CRICKET_AUDIO_SIGNING_SECRET` to a high-entropy secret that is not the Supabase service-role key.
- Set `SMART_CRICKET_EVIDENCE_STORAGE_BACKEND=supabase`, `SMART_CRICKET_EVIDENCE_SUPABASE_BUCKET`, and private bucket policies before enabling model-improvement participation.
- Use `python scripts/review_feedback_candidates.py list --include-access` only from a trusted backend/maintainer environment. Supabase reviewer access is generated as a short-lived signed URL and requires backend-only Supabase credentials.
- Schedule `python scripts/cleanup_audio.py` for generated audio cleanup.
- Schedule `python scripts/cleanup_evidence.py --execute` for expired or deletion-pending retained evidence after protected evidence storage is enabled.
- Set a narrow `SMART_CRICKET_CORS_ORIGINS` value.
- Use protected object storage and a cleanup policy for generated audio and any retained model-improvement evidence.
- Put a reverse proxy in front of the API for TLS and configure `SMART_CRICKET_TRUSTED_PROXY_HOPS` only for proxies you operate.
- Production multi-instance deployments should set `SMART_CRICKET_RATE_LIMIT_BACKEND=redis` with `SMART_CRICKET_REDIS_URL`, or `SMART_CRICKET_RATE_LIMIT_BACKEND=gateway` when a verified external gateway/WAF owns rate limiting. Do not use the memory backend for public production.
- Keep trusted analysis history server-side. Browser roles must not receive `INSERT` or `UPDATE` grants on `analysis_sessions`.
- Run the container smoke from CI locally before production: build image, start container, call `/health`, call `/ready`, inspect logs, shut down cleanly.

## Health, Readiness, and Deployment Smoke

`/health` is lightweight liveness. It answers only whether the API process is alive and must stay cheap enough for platform health checks.

`/ready` is dependency readiness. In staging and production it includes artifact checks plus production configuration validation for auth, persistence, evidence storage, audio signing, rate limiting, CORS, upload limits, and inference timeouts.

Run a deployed smoke check without a cricket fixture:

```bash
python scripts/smoke_deployment.py https://your-api.example.com
python scripts/smoke_deployment.py https://your-api.example.com --json
```

Expected passing checks:

- `/health` returns `200`
- `/ready` returns `200`
- `/capabilities` returns safe public metadata
- `POST /analyze` without a file returns a safe validation error, not a traceback
- version metadata is present

## Docker Runtime

The API image is Docker-first and expects a managed HTTPS reverse proxy or platform TLS in front of it. The container:

- runs as the non-root `smartcricket` user;
- uses production Python dependencies from `pyproject.toml`;
- copies only backend code and required ML artifacts;
- downloads the MediaPipe pose landmarker with a pinned SHA-256 checksum;
- uses `/tmp/smart-cricket-audio` for generated audio;
- exposes `/health` as its Docker healthcheck;
- declares `SIGTERM` as the stop signal so FastAPI shutdown can terminate active inference workers.

Provider examples such as Render, Railway, Fly.io, or Cloud Run should use the same contract: Docker image, environment secrets, managed TLS, `/health` liveness, `/ready` readiness, and external persistence/storage services.

## Controlled Concurrency Smoke

After staging has a safe short MP4 fixture, run:

```bash
python scripts/concurrency_smoke.py https://your-api.example.com ./path/to/non-sensitive-short.mp4 --workers 3
```

This is not a production load test. It only checks that simultaneous analysis requests produce a bounded mix of success and overload/busy responses instead of unbounded worker creation.
