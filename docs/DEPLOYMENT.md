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

- Set `SMART_CRICKET_REQUIRE_AUTH=true`.
- Set `SMART_CRICKET_ENV=production`.
- Set `SUPABASE_JWT_SECRET` for legacy HS256 projects, or set `SUPABASE_URL` plus issuer/audience values so the verifier can use Supabase JWKS for asymmetric signing keys.
- Set `SUPABASE_JWT_AUDIENCE` and `SUPABASE_JWT_ISSUER` in production.
- Set `SUPABASE_SERVICE_ROLE_KEY` only on the backend. Never expose it to the frontend.
- Set `SMART_CRICKET_AUDIO_SIGNING_SECRET` to a high-entropy secret that is not the Supabase service-role key.
- Set `SMART_CRICKET_EVIDENCE_STORAGE_BACKEND=supabase`, `SMART_CRICKET_EVIDENCE_SUPABASE_BUCKET`, and private bucket policies before enabling model-improvement participation.
- Schedule `python scripts/cleanup_audio.py` for generated audio cleanup.
- Schedule `python scripts/cleanup_evidence.py --execute` for expired or deletion-pending retained evidence after protected evidence storage is enabled.
- Set a narrow `SMART_CRICKET_CORS_ORIGINS` value.
- Use protected object storage and a cleanup policy for generated audio and any retained model-improvement evidence.
- Put a reverse proxy in front of the API for TLS and configure `SMART_CRICKET_TRUSTED_PROXY_HOPS` only for proxies you operate.
- Production multi-instance deployments should set `SMART_CRICKET_RATE_LIMIT_BACKEND=redis` with `SMART_CRICKET_REDIS_URL`, or `SMART_CRICKET_RATE_LIMIT_BACKEND=gateway` when a verified external gateway/WAF owns rate limiting. Do not use the memory backend for public production.
- Keep trusted analysis history server-side. Browser roles must not receive `INSERT` or `UPDATE` grants on `analysis_sessions`.
- Run the container smoke from CI locally before production: build image, start container, call `/health`, call `/ready`, inspect logs, shut down cleanly.
