# Phase 14 TTS and Audio Architecture

Phase 14 originally used local macOS speech generation and a WAV cue fallback. That was useful for demonstrating that the analysis response could include playable audio, but it was not a production TTS architecture: it depended on a developer machine, did not model provider failures cleanly, and treated generated files as local artifacts rather than protected product data.

The current architecture separates the product contract from provider implementation.

## Provider Boundary

Backend analysis calls a provider-neutral TTS boundary in `backend/api/tts.py`. Providers return a structured `TTSResult` with status, provider ID, bytes, MIME type, extension, duration when known, safe error code, and metadata. Provider-specific SDK objects do not leave the provider layer.

Implemented providers:

- `text_only`: explicit fallback when TTS is disabled, unconfigured, timed out, or unavailable.
- `local_development`: development/test provider using macOS `say` when available, otherwise a clearly labelled audio cue. This is not production narration.
- `google`: Google Cloud Text-to-Speech adapter using Google-supported Application Default Credentials. It supports plain-text synthesis, configurable language/voice, bounded timeout, retry-limited failures, and browser-friendly MP3 output.

The API never sends arbitrary user content as trusted SSML. Text is normalized as plain text, control characters are removed, and length is capped by `SMART_CRICKET_TTS_MAX_TEXT_CHARACTERS`.

## Graceful Degradation

TTS is not allowed to fail primary cricket analysis. If the provider is disabled, missing credentials, times out, returns invalid output, or fails transiently, the API returns the full text coaching feedback with:

```text
voice_output.available = false
voice_output.degraded_to_text_only = true
```

Stable safe error codes include `tts_unconfigured`, `tts_timeout`, `tts_auth_failed`, `tts_provider_unavailable`, `tts_invalid_output`, and `tts_request_failed`.

## Audio Artifacts

Generated audio is stored through `backend/api/audio.py` as an `AudioArtifact` with:

- opaque artifact ID;
- provider;
- MIME type and extension;
- creation and expiry timestamps;
- byte count;
- SHA-256 checksum;
- storage backend;
- short-lived signed access URL.

The API response does not expose local filesystem paths. MIME type and extension are validated together so MP3 bytes are not mislabeled as WAV or the reverse.

## Storage and Signed Access

Local development storage writes randomized filenames under `SMART_CRICKET_AUDIO_OUTPUT_DIR` and serves them through signed `/audio/...` URLs. The signing secret must be strong outside development/test, TTL is capped, and traversal or tampered signatures are rejected.

Production audio storage supports a private Supabase Storage adapter with:

- server-side upload using backend-only credentials;
- short-lived signed URLs;
- private bucket expectation;
- failure normalization without leaking service-role keys or signed URLs.

Authenticated analyses pass user/session context into storage so production object paths can be bound to the owning user/session. Anonymous/demo analyses use short-lived opaque access.

## Cleanup

Operators can run:

```bash
python scripts/cleanup_audio.py --dry-run
python scripts/cleanup_audio.py
```

The command reports `scanned`, `expired`, `deleted`, `failed`, and `skipped` without printing signed URLs or secrets. Local cleanup is executable now; live Supabase cleanup/playback verification remains an external staging task.

## Observability

The existing metrics registry records TTS and audio lifecycle events:

- `smart_cricket_tts_request`
- `smart_cricket_tts_success`
- `smart_cricket_tts_failure`
- `smart_cricket_tts_timeout`
- `smart_cricket_tts_fallback`
- `smart_cricket_audio_storage_success`
- `smart_cricket_audio_storage_failure`
- `smart_cricket_audio_signed_url_failure`
- `smart_cricket_audio_cleanup_deleted`
- `smart_cricket_audio_cleanup_failed`

Logs include safe provider/status/error metadata and request IDs, but not coaching text, credentials, signed URLs, or audio bytes.

## Live Provider Gate

Phase 14 is now code-complete with live provider validation pending. The remaining gate is to configure real Google Cloud TTS credentials and a private Supabase audio bucket in staging, then run a small paid-safe synthesis/storage/playback/delete smoke test.
