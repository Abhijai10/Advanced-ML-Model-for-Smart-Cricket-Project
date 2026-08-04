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
- `POST /analyze` for uploaded video analysis
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
- Set `SUPABASE_JWT_SECRET` for legacy HS256 projects, or set `SUPABASE_URL` plus issuer/audience values so the verifier can use Supabase JWKS for asymmetric signing keys.
- Set `SUPABASE_SERVICE_ROLE_KEY` only on the backend. Never expose it to the frontend.
- Set a narrow `SMART_CRICKET_CORS_ORIGINS` value.
- Use protected object storage and a cleanup policy for generated audio and any retained model-improvement evidence.
- Put a reverse proxy in front of the API for TLS and stronger distributed rate limiting.
- Keep trusted analysis history server-side. Browser roles must not receive `INSERT` or `UPDATE` grants on `analysis_sessions`.
- Run the container smoke from CI locally before production: build image, start container, call `/health`, call `/ready`, inspect logs, shut down cleanly.
