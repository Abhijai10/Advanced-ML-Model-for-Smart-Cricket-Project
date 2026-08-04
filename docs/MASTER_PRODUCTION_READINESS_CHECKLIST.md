# Smart Cricket - Master Production Readiness Checklist and Current State

Last updated: 2026-08-04
Working branch: `production-readiness-execution`
Base branch: `origin/production-hardening`
Existing PR context: draft PR #2, `production-hardening` -> `main`

## Executive Readiness Verdict

Smart Cricket is a strong production-oriented MVP, not a production-ready coaching product. The `production-hardening` branch fixed the highest-risk filename-inference bug, improved upload validation, separated liveness and readiness, added API tests, added basic auth/rate-limit scaffolding, and improved the React app shell. The product still cannot honestly be released as production-ready because ML generalization, real-video Phase 12 validation, trusted persistence, production auth configuration, natural TTS, deployment, privacy/retention operations, browser/device coverage, and coach/user validation remain incomplete or unverified.

Release verdict: controlled technical beta only after P0 code-hardening items below pass. Public production release remains blocked by external data, credentials, deployment, and expert validation gates.

## Current Branch, PR, and Release State

- `main`: latest local and remote main is `49cfbf3 Add Smart Cricket website app`; it does not contain `production-hardening`.
- `origin/production-hardening`: latest inspected commit is `796521f Polish frontend browser basics`.
- Working branch for this execution: `production-readiness-execution`, created from `origin/production-hardening`.
- Draft PR #2 exists per prior review and appears to contain production-hardening work. This pass should create or update a draft PR from `production-readiness-execution`; it must not merge automatically.
- No production deployment, release tag, verified Supabase project, or production CI run was confirmed during the initial audit.

## Roadmap Phase 1-14 Status

| ID | Phase | Status | Severity | Evidence | Acceptance Gate |
| --- | --- | --- | --- | --- | --- |
| RM-01 | Phase 1: project framing/data plan | Partial | P1 | Product/docs exist, but production privacy, consent, retention, and user-study protocol are not final. | Signed beta protocol, privacy policy, consent text, retention schedule. |
| RM-02 | Phase 2: raw data/preprocessing | Partial | P0 | Processed pose sequences exist; no raw legal batting video fixture exists in repo for true E2E. | At least one legally usable raw batting video fixture and documented provenance. |
| RM-03 | Phase 3: pose extraction | Partial | P0 | `ml/src/preprocessing/extract_pose.py` and MediaPipe path exist; not validated in CI against a real cricket video. | Real-video MediaPipe extraction test passes or explicit fixture blocker remains. |
| RM-04 | Phase 4: cleaning/normalization | Partial | P1 | Cleaning, normalization, alignment modules exist; field robustness unverified. | Tests with varied framing/lighting/occlusion and coach-reviewed quality labels. |
| RM-05 | Phase 5: feature engineering | Partial | P0 | 32-D schema exists; `lead_wrist_acceleration` is documented as acceleration-like but actually computes abs lead-vs-trail velocity difference. Duplicate feature systems still exist. | Versioned feature contract and migration plan; no silent tensor change without retraining. |
| RM-06 | Phase 6: dataset infrastructure | Partial | P0 | Temporal dataset is `(80, 60, 32)` with 80 samples; split metadata exists. | Player/group metadata, scalable manifests, group-held-out split generation. |
| RM-07 | Phase 7: temporal architectures | Complete for prototype | P2 | GRU/BiLSTM architecture and shape tests exist. | Production gate still depends on valid dataset/evaluation. |
| RM-08 | Phase 8: training/evaluation | Partial | P0 | Best model checkpoint exists; model card reports test accuracy 0.6667 and macro F1 0.6762; split is not player-disjoint. | Player-held-out metrics, calibration, confidence thresholds, drift plan. |
| RM-09 | Phase 9: segmentation/prediction gating | Partial | P1 | State machine emits one trigger; reusable reset/rearm behavior is missing at initial audit. | Multi-shot/rearm tests pass while one-shot default remains unchanged. |
| RM-10 | Phase 10: technique scoring | Partial | P1 | Rule/template scoring artifacts exist; not coach-certified and may be sensitive to feature semantics. | Coach validation and per-issue safety review. |
| RM-11 | Phase 11: feedback engine | Partial | P1 | Feedback text exists; no user feedback safety loop at initial audit. | Human-in-the-loop feedback system with consent, moderation, expert adjudication. |
| RM-12 | Phase 12: offline inference pipeline | Unverified | P0 | `raw_video_pipeline.py` exists, but repo contains no raw `.mp4/.mov/.webm/.avi/.mkv` fixture. Current API tests mock `analyze_raw_video`. | One actual batting video goes through MediaPipe, preprocessing, checkpoint, segmentation, scoring, feedback, API response, and audio without mocks. |
| RM-13 | Phase 13: API integration | Partial | P0 | FastAPI wrapper exists; server-side persistence, production JWT/JWKS validation, durable rate limiting, observability, timeouts, deployment/TLS, and RLS validation are incomplete. | Production env configured; backend-owned persistence; auth/RLS tested; deployment smoke and monitoring pass. |
| RM-14 | Phase 14: voice output | Partial | P1 | Local macOS `say` plus WAV cue fallback exists; not natural production TTS and provider failure can fail analysis at initial audit. | Provider abstraction, graceful degradation, protected audio, cleanup lifecycle, provider and browser tests. |

## DeepSeek and Known Audit Findings

| ID | Finding | Status | Severity | Evidence | Required Action |
| --- | --- | --- | --- | --- | --- |
| DS-01 | Filename-based `/analyze` inference could return stored results for uploaded dataset-like filename. | Fixed | P0 | `analyze_uploaded_video` saves and analyzes uploaded bytes; tests verify known filename invalid bytes are rejected. | Keep regression tests. |
| DS-02 | Upload validation too weak. | Partial | P0 | Extension, byte signature, OpenCV probe, size, duration, and resolution checks exist. | Add request timeout/concurrency strategy and better MIME/container coverage. |
| DS-03 | `/health` reports `inference_ready: true` without readiness checks. | Unresolved initially | P1 | `api_health()` hard-codes `inference_ready: True`. | Make liveness honest or remove inference-ready claim. |
| DS-04 | Client-forged trusted history. | Partial | P0 | Frontend no longer writes analysis results directly, but backend persistence is not implemented. | Add backend-owned persistence with service-role-only server config and safe fallback. |
| DS-05 | Auth validation is incomplete. | Partial | P0 | Manual HS256 JWT validation using `SUPABASE_JWT_SECRET`; no JWKS/project URL support. | Prefer JWKS-compatible architecture while retaining testability. |
| DS-06 | Rate limiting is in-memory and proxy trust is unsafe. | Partial | P1 | `_client_key` trusts `x-forwarded-for`; in-memory buckets are single-process only. | Add trusted proxy config and pluggable rate-limit backend contract. |
| DS-07 | TTS can fail analysis and is not production-natural TTS. | Partial | P1 | `synthesize_spoken_feedback` can raise; local cue fallback is not speech. | Graceful degradation and provider docs/tests. |
| DS-08 | Audio files are public static artifacts without lifecycle protection. | Partial | P1 | `/audio` static mount is public; unique filenames exist. | Cleanup policy, retention docs, protected access design. |
| DS-09 | CameraAnalysis cleanup stops tracks when `pendingClip` changes while `isCameraReady` remains true. | Unresolved initially | P0 | Effect cleanup depends on `pendingClip` and stops `streamRef` on each pending clip change. | Split stream lifecycle cleanup from preview URL cleanup. |
| DS-10 | No true raw-video E2E test. | Unresolved | P0 | No raw video fixture found under `ml/data`; current API tests patch `analyze_raw_video`. | Add real fixture if legally available; otherwise add skipped harness with blocker. |
| DS-11 | `lead_wrist_acceleration` semantic bug. | Partial | P0 | Feature name implies acceleration; code computes abs difference between lead/trail wrist velocities. | Add feature-contract metadata and migration plan; retrain before changing tensor. |
| DS-12 | State machine not reusable for multi-shot sessions. | Unresolved initially | P1 | `_triggered` never resets; no reset/rearm test. | Add reset/rearm API and tests. |
| DS-13 | Python package import/sys.path manipulation. | Partial | P2 | `raw_video_pipeline.py` inserts `ml/src` into `sys.path`; pytest config also injects paths. | Reduce where safe; broader package cleanup deferred. |
| DS-14 | Docker image includes dev dependencies and runs as root. | Unresolved initially | P1 | `Dockerfile.api` installs `.[dev]` and no non-root user. | Use production deps only, non-root user, health/smoke docs. |
| DS-15 | CI lacks frontend tests/E2E/container checks. | Partial | P1 | CI runs Python, lint, build only. | Add component/E2E/container jobs where practical. |

## ML and Data Production Blockers

| ID | Blocker | Status | Severity | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| ML-01 | Dataset has only 80 samples. | Blocked External | P0 | Larger consented dataset across players, devices, lighting, camera positions, skill levels. |
| ML-02 | Official split is not player-disjoint. | Blocked External | P0 | Player/group IDs and held-out evaluation with no player leakage. |
| ML-03 | Calibration and uncertainty thresholds are engineering heuristics. | Partial | P0 | Calibrated probabilities and thresholds validated on held-out data. |
| ML-04 | No coach validation of shot labels, technique issues, or advice safety. | Blocked External | P0 | Coach-reviewed label and feedback acceptance report. |
| ML-05 | Feature schema migration is unresolved. | Partial | P0 | Versioned feature contract, migration guide, retrained artifacts for any tensor change. |
| ML-06 | `lead_wrist_acceleration` semantic mismatch. | Partial | P0 | Metadata documents v1 meaning; v2 migration is explicit and retrained. |
| ML-07 | Duplicate feature systems. | Partial | P1 | Single source of truth or documented compatibility boundary. |
| ML-08 | Model generalization to real users is unproven. | Blocked External | P0 | Field evaluation and drift monitoring pass release thresholds. |

## Phase 12 True End-to-End Test Requirements

| ID | Requirement | Status | Severity | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| E2E-01 | Legally usable actual batting video fixture. | Blocked External | P0 | Fixture path, license/provenance, consent, and expected non-label-specific assertions documented. |
| E2E-02 | MediaPipe pose extraction is unmocked. | Not Started | P0 | Test invokes `extract_pose_from_video` on fixture. |
| E2E-03 | Preprocessing, cleaning, normalization, alignment, resampling are unmocked. | Not Started | P0 | Test asserts valid 60x32 sequence and source metadata. |
| E2E-04 | Real checkpoint inference is unmocked. | Not Started | P0 | Test calls `analyze_raw_video` without patching model pipeline. |
| E2E-05 | Segmentation/scoring/feedback/API/audio are included. | Not Started | P0 | API-level test submits fixture and distinguishes TTS fallback from model inference. |

## Phase 13 Completion Requirements

| ID | Requirement | Status | Severity | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| API-01 | Production authentication. | Partial | P0 | Supabase JWKS/JWT validation configured and tested with invalid/expired/wrong-audience tokens. |
| API-02 | Server-side Supabase persistence. | Not Started initially | P0 | Backend inserts verified analysis and feedback rows; frontend never uses service role. |
| API-03 | RLS validation. | Partial | P0 | Migration includes RLS; tests against Supabase local/project prove owner isolation. |
| API-04 | Production storage. | Not Started | P1 | Audio/clips are stored in protected storage with retention and signed access. |
| API-05 | Error handling and observability. | Partial | P1 | Structured logs, timings, stable error codes, request IDs, metrics hooks. |
| API-06 | Async/concurrency strategy. | Not Started | P1 | Blocking ML work is isolated via worker/thread/job queue strategy and timeout controls. |
| API-07 | Rate limiting. | Partial | P1 | Pluggable distributed rate limiter and trusted proxy config. |
| API-08 | Reverse proxy/TLS/deployment. | Blocked External | P0 | Production deployment smoke under TLS with configured origins. |
| API-09 | Privacy and retention. | Partial | P0 | Consent, retention, deletion, export, and incident response docs. |

## Phase 14 Completion Requirements

| ID | Requirement | Status | Severity | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| VO-01 | Actual natural TTS provider. | Blocked External | P1 | Provider credentials configured and provider-specific integration tests pass. |
| VO-02 | Text-only graceful degradation. | Unresolved initially | P1 | Analysis succeeds when TTS fails and marks audio unavailable. |
| VO-03 | Protected audio access. | Not Started | P1 | Audio requires authenticated/signed access in production. |
| VO-04 | Cleanup lifecycle. | Partial | P1 | Configurable retention and cleanup command/job exist. |
| VO-05 | Browser playback tests. | Not Started | P2 | Browser E2E verifies audio UI for available and unavailable audio. |

## Continual-Learning and Feedback Architecture

| ID | Requirement | Status | Severity | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| FB-01 | Ask users whether prediction was correct. | Not Started initially | P1 | UI captures correct/incorrect/unsure. |
| FB-02 | Optional corrected shot label. | Not Started initially | P1 | Corrected label must be one of supported classes. |
| FB-03 | Rate technique feedback. | Not Started initially | P1 | 1-5 rating with optional note. |
| FB-04 | Mark tips useful, incorrect, or unsafe. | Not Started initially | P0 | Safety flags are captured and never used for automatic retraining. |
| FB-05 | Consent to contribute clip/result. | Not Started initially | P0 | Explicit consent field, privacy copy, and server audit metadata. |
| FB-06 | Safe human-in-the-loop pipeline. | Documentation Needed | P0 | Provenance, consent, moderation, deduplication, confidence weighting, expert review, label-quality scoring, disagreement resolution, model versioning, rollback, drift monitoring, and retraining gates documented. |
| FB-07 | AI-assisted review boundaries. | Documentation Needed | P1 | AI may triage/flag inconsistencies but is never ground truth. |
| FB-08 | No blind retraining on user reports. | Required | P0 | Export/review flow produces candidates; no training job consumes raw reports automatically. |

## Website and Product Gaps

| ID | Gap | Status | Severity | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| WEB-01 | Camera lifecycle/restart/retake bug. | Unresolved initially | P0 | Stream cleanup and preview URL cleanup are independent; restart/retake tested. |
| WEB-02 | Recording countdown and max length. | Not Started initially | P1 | Countdown, visible timer, auto-stop, configurable max duration. |
| WEB-03 | Framing/full-body guide. | Not Started initially | P1 | Accessible visual guide and text instructions. |
| WEB-04 | Pose/skeleton overlay or honest phase visualization. | Partial | P2 | Use backend output only; do not fake pose landmarks. |
| WEB-05 | Upload preview/review before submission. | Not Started initially | P1 | Uploaded files are previewed and reviewed before API submission. |
| WEB-06 | Staged progress UX and quality guidance. | Partial | P1 | Progress stages describe upload/analyze/feedback/audio and quality tips. |
| WEB-07 | Session details/history UX. | Partial | P2 | Shows confidence, quality, timing, source, and meaningful empty/loading/error states. |
| WEB-08 | Premium restrained polish. | Partial | P2 | Better hierarchy, responsive layout, accessible controls, polished states. |
| WEB-09 | Mobile Safari/Android/device coverage. | Unverified | P1 | Browser/device test matrix passes. |
| WEB-10 | Accessibility. | Partial | P1 | Keyboard, labels, contrast, announcements, reduced-motion, screen-reader checks. |
| WEB-11 | Component tests and browser E2E. | Not Started initially | P1 | Component tests and Playwright scaffolding cover primary flows. |
| WEB-12 | Bundle splitting. | Not Started initially | P2 | Lazy-load chart/results-heavy surfaces where appropriate. |

## Testing Matrix

| ID | Area | Initial Status | Severity | Evidence/Acceptance Criteria |
| --- | --- | --- | --- | --- |
| TEST-01 | Python unit tests | Partial | P1 | `python -m pytest` must pass. |
| TEST-02 | Backend API tests | Partial | P0 | Upload validation, auth, rate limit, feedback, persistence fallback, TTS failure tests. |
| TEST-03 | True ML E2E | Blocked External | P0 | Real fixture through unmocked raw pipeline. |
| TEST-04 | API security | Partial | P0 | Invalid tokens, forged feedback/history payloads, size/type/rate limits. |
| TEST-05 | Supabase integration | Partial | P0 | Migration/RLS checks plus mocked/local service-role tests. |
| TEST-06 | Frontend component tests | Not Started initially | P1 | Camera/upload/results/history/auth fallback tests. |
| TEST-07 | Browser E2E | Not Started initially | P1 | Happy-path mocked API, auth fallback, feedback, upload review, result display. |
| TEST-08 | Device/browser | Unverified | P1 | Chrome/Safari/Firefox/mobile Safari/Android manual or automated coverage. |
| TEST-09 | Accessibility | Partial | P1 | Automated and manual checks. |
| TEST-10 | Performance/load/concurrency | Not Started | P1 | Upload and inference concurrency strategy/load test. |
| TEST-11 | Privacy/security | Partial | P0 | Retention, consent, protected storage, secrets audit. |
| TEST-12 | Container/deployment smoke | Done | P1 | GitHub Actions builds the API image, starts it, and checks `/health` plus `/ready`. |
| TEST-13 | Migration/rollback | Partial | P1 | SQL migration syntax, RLS, rollback/disaster recovery docs. |
| TEST-14 | Model evaluation | Blocked External | P0 | Player-held-out metrics, calibration, drift monitoring. |
| TEST-15 | Coach/user acceptance | Blocked External | P0 | Coach and beta-user acceptance reports. |

## Can Be Completed in Code Now

| ID | Item | Priority | Dependencies | Acceptance Criteria | Final Status |
| --- | --- | --- | --- | --- | --- |
| NOW-01 | Fix CameraAnalysis stream cleanup and object URL cleanup. | P0 | None | Retake/review does not stop live camera; URLs revoked. | Done |
| NOW-02 | Add countdown, max recording length, timer, auto-stop, review flow. | P1 | Browser MediaRecorder | UI has countdown/timer/auto-stop/review; component test covers upload review. | Partial |
| NOW-03 | Add upload preview/review before submission. | P1 | Browser video preview | Upload does not submit until user confirms. | Done |
| NOW-04 | Add staged analysis progress and framing guide. | P1 | None | Accessible status updates and quality guidance are present. | Done |
| NOW-05 | Improve result/history details using trustworthy fields. | P2 | Existing API response | History includes quality state; result panel includes timing, quality, probabilities, audio fallback. | Done |
| NOW-06 | Add safe feedback API/UI/schema/migration/docs. | P0 | None for local/mock | Feedback now requires durable persistence for saved states, binds model-improvement feedback to verified analyses, and rejects client-forged provenance. Protected evidence storage remains external. | Partial |
| NOW-07 | Add feedback tests: auth/forgery/consent/duplicates/labels. | P0 | TestClient | Backend and frontend tests cover no fake saved state, duplicates, auth-required consent, forged trusted fields, missing/cross-user analysis IDs, and reset behavior. Live Supabase RLS tests remain external. | Partial |
| NOW-08 | Add server-side analysis persistence scaffolding with safe fallback. | P0 | Optional Supabase env | Backend-owned persistence returns `analysis_session_id` when stored and marks failures explicitly. Service-role insert behavior still needs Supabase-local/project verification. | Partial |
| NOW-09 | Make `/health` inference readiness honest. | P1 | None | Health derives readiness instead of hard-coded true. | Done |
| NOW-10 | Add TTS graceful degradation and tests. | P1 | None | Analysis succeeds with unavailable audio metadata when TTS fails. | Done |
| NOW-11 | Version/document `lead_wrist_acceleration` contract. | P0 | No retraining | Feature schema metadata and docs explain v1 semantics and v2 migration. | Done |
| NOW-12 | Add state-machine reset/rearm tests. | P1 | None | Existing one-shot behavior preserved; reset/rearm tests pass. | Done |
| NOW-13 | Add real-video E2E harness with explicit skip if fixture missing. | P0 | Fixture absent | Harness added and skipped honestly because fixture is absent. | Blocked External |
| NOW-14 | Improve Docker image hygiene. | P1 | None | Dockerfile uses production deps, non-root user, signed local audio path, pinned MediaPipe pose model download, and CI container smoke starts the image and checks `/health` plus `/ready`. | Done |
| NOW-15 | Add frontend test/E2E scaffolding and CI jobs where practical. | P1 | npm packages | Vitest and Playwright scaffolding added; local lint/build/component/browser checks pass. | Done |
| NOW-16 | Add structured logging, timing, safer proxy config, timeout/limits docs. | P1 | None | Request timing/log metadata, process-time header, trusted proxy setting, persistence timeout added. | Done |
| NOW-17 | Add security/privacy/retention/environment docs. | P0 | None | Environment and privacy/retention docs updated. | Done |

## Requires External Data, Credentials, Coach, Users, or Deployment

| ID | Item | Priority | External Dependency | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| EXT-01 | Collect larger, diverse, consented dataset. | P0 | Players/videos/consent | Dataset sufficient for target release segment. |
| EXT-02 | Add player IDs and player-disjoint evaluation. | P0 | Metadata | Held-out metrics pass release threshold. |
| EXT-03 | Coach label and feedback validation. | P0 | Qualified coach/reviewer | Approved label and advice safety report. |
| EXT-04 | Supabase project credentials and RLS validation. | P0 | Project URL/keys/local Supabase | Auth/persistence/RLS tests pass. |
| EXT-05 | Natural TTS provider. | P1 | Provider credentials/billing | Provider integration and playback tests pass. |
| EXT-06 | Production hosting/TLS/reverse proxy. | P0 | Hosting domain/infra | Deployment smoke and monitoring pass. |
| EXT-07 | Device/browser beta testing. | P1 | Devices/users | Mobile Safari/Android/desktop acceptance. |
| EXT-08 | Privacy/legal review. | P0 | Legal/product owner | Policy, consent, deletion, retention approved. |

## Suggested Implementation Order and Release Gates

1. P0 safety/code truthfulness: `NOW-01`, `NOW-06`, `NOW-07`, `NOW-08`, `NOW-09`, `NOW-10`, `NOW-11`, `NOW-13`, `NOW-17`.
2. P1 product and operational hardening: `NOW-02`, `NOW-03`, `NOW-04`, `NOW-12`, `NOW-14`, `NOW-15`, `NOW-16`.
3. P2 polish and experience depth: `NOW-05`, `WEB-04`, `WEB-08`, `WEB-12`.
4. External release gates: `EXT-01` through `EXT-08`.

Release gate A, controlled beta: all P0 code items done or explicitly blocked external; Python/API/frontend checks pass; no mock is represented as real-E2E.

Release gate B, public production: all P0/P1 code items pass, real-video E2E passes, Supabase/auth/deployment/TLS are verified, dataset is larger and player-held-out, coach validation is complete, and privacy/retention is approved.

## Verification Log

This section must be updated after implementation.

| Command | Result | Duration | Notes |
| --- | --- | --- | --- |
| `python3 -m pytest` | Pass | 27.00s | 91 passed, 1 skipped. The skip is `ml/src/inference/tests/test_true_raw_video_e2e.py` because `ml/data/e2e/raw_batting_fixture.mp4` is absent. |
| `npm run lint` in `frontend` | Pass | about 4s | ESLint passed. |
| `npm run build` in `frontend` | Pass | about 5s | TypeScript and Vite production build passed; `ShotCharts` emitted as separate lazy chunk. |
| `npm run test` in `frontend` | Pass | 2.85s | 8 component tests passed, covering upload preview, camera lifecycle, feedback reset, duplicate, and persistence failure states. |
| `npm run test:e2e` in `frontend` | Pass | 6.4s | 1 Playwright Chromium test passed with mocked `/analyze` and `/feedback`; not real ML evidence. |
| `npm audit --audit-level=high` in `frontend` | Pass | about 1s | 0 vulnerabilities reported. |
| secret scan for service-role patterns | Pass | immediate | No obvious `SUPABASE_SERVICE_ROLE_KEY`, `sb_secret_`, or service-role JWT value found in repo text. |
| `supabase migration list --local` | Blocked | about 11s | Supabase CLI exists, but no local Postgres/Supabase DB is running; live RLS verification remains external. |
| GitHub Actions container smoke | Pass | 3m09s | Remote CI builds the image, starts the container, calls `/health`, calls `/ready`, prints readiness details, and removes the container. Local Docker CLI is not installed. |
| `python3 -m json.tool ml/data/final_temporal/temporal_feature_schema.json` | Pass | immediate | Feature schema JSON remains parseable. |

## Final Checklist Status

Phase D status: code-feasible P0/P1 items were implemented where possible. Production readiness remains blocked by real-video fixture validation, Supabase/local project verification, production deployment/TLS, natural TTS credentials, larger player-disjoint dataset, coach validation, and privacy/legal review.

Done: `NOW-01`, `NOW-03`, `NOW-04`, `NOW-05`, `NOW-09`, `NOW-10`, `NOW-11`, `NOW-12`, `NOW-14`, `NOW-15`, `NOW-16`, `NOW-17`.

Partial: `NOW-02` because countdown/auto-stop are implemented and unit-tested but real-device mobile recording remains unverified; `NOW-06`, `NOW-07`, `NOW-08` because code/mock tests now enforce safe feedback and server-owned history but live Supabase/RLS/storage verification remains external.

Blocked External: `NOW-13`, `E2E-01` through `E2E-05`, `EXT-01` through `EXT-08`.

Phase 12 final status: not complete. A skipped unmocked harness exists, but no actual raw batting-video fixture is available.

Phase 13 final status: partial. Backend-owned persistence now returns trusted `analysis_session_id`, browser write grants are revoked in a follow-up migration, feedback binds to verified analyses, and analysis concurrency is bounded. Supabase-local/project RLS verification, deployment/TLS, distributed rate limiting, load testing, and monitoring remain unverified or external.

Phase 14 final status: partial. TTS failure now degrades safely to text-only and local audio URLs are signed, but natural production TTS, protected object storage, cleanup jobs, and provider/browser coverage remain incomplete.

Website status: materially improved and closer to a premium controlled-beta product, with better camera/review/progress/feedback/history states. It still needs real-device mobile Safari/Android testing and more advanced annotated pose/phase visualization only after backend data supports it.
