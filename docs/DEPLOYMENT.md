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
- `GET /audio/<filename>` for generated audio artifacts

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
- Set `SUPABASE_JWT_SECRET` or replace the verifier with JWKS validation if the Supabase project uses asymmetric JWT signing keys.
- Set a narrow `SMART_CRICKET_CORS_ORIGINS` value.
- Use persistent object storage or a cleanup policy for generated audio.
- Put a reverse proxy in front of the API for TLS and stronger distributed rate limiting.
- Move analysis history writes server-side before relying on analytics or billing.
- Do not re-enable browser-side writes for `analysis_sessions.full_result`; trusted history must be created from backend inference output.
