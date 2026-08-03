# Phase 13 — Deep Interview Pack

# Question

What did Phase 13 add to the project?

## Short Answer

It exposed the Phase 12 inference pipeline through a FastAPI backend with `/health` and `/analyze` endpoints.

## Deep Technical Explanation

Phase 13 added an API boundary around the existing ML system. The `/analyze` endpoint accepts an uploaded video, validates it, saves it temporarily, calls the Phase 12 pipeline, returns a structured JSON response, and cleans temporary files.

## Engineering Reasoning

The API should not contain model, scoring, or feedback logic. It should act as transport and orchestration around the already validated inference pipeline.

## Why This Decision Was Taken

The roadmap says the API should call the inference pipeline and not duplicate logic.

## Tradeoffs / Risks / Limitations

Phase 13 v1 validates known finalized dataset video filenames. Arbitrary raw-video preprocessing is still a future hardening task.

## Important Engineering Insight

Backend integration is about exposing stable business logic, not rewriting that logic.

# Question

Why should API logic stay separate from ML logic?

## Short Answer

To avoid duplicated behavior and keep the system maintainable.

## Deep Technical Explanation

ML logic includes checkpoint loading, scaling, segmentation, scoring, and feedback. API logic includes upload validation, temporary file handling, routing, response schemas, and error handling.

Mixing them makes testing and debugging harder.

## Engineering Reasoning

When the model changes, the inference pipeline should change once. If API code duplicates model logic, the system can produce inconsistent outputs.

## Why This Decision Was Taken

The Phase 12 pipeline already provides stable inference. Phase 13 should wrap it.

## Tradeoffs / Risks / Limitations

The API depends on Phase 12 being stable. Upstream changes require API validation reruns.

## Important Engineering Insight

Good APIs are thin wrappers around stable application services.

# Question

What endpoints were implemented?

## Short Answer

`GET /health` and `POST /analyze`.

## Deep Technical Explanation

`/health` returns service readiness metadata. `/analyze` accepts a video upload and returns prediction, confidence, technique score, feedback, debug metadata, source metadata, prediction probabilities, segmentation metadata, and API metadata.

## Engineering Reasoning

Health checks support deployment readiness. Analyze is the main frontend-facing endpoint.

## Why This Decision Was Taken

The roadmap explicitly suggests `POST /analyze` and a later health endpoint.

## Tradeoffs / Risks / Limitations

The response is larger than the minimal frontend requirement, but it is much easier to debug.

## Important Engineering Insight

Production endpoints need both user-facing data and operational metadata.

# Question

How does Phase 13 handle errors?

## Short Answer

Invalid inputs return structured 422 errors; unexpected failures return structured 500 errors.

## Deep Technical Explanation

Unsupported extensions and unknown dataset videos raise API validation errors. The route converts these into HTTP 422 responses with an error code and debug metadata.

## Engineering Reasoning

User/input errors should not look like server crashes. Clean error handling improves frontend integration.

## Why This Decision Was Taken

The roadmap requires clean error handling.

## Tradeoffs / Risks / Limitations

The current error schema is simple and may evolve as the frontend matures.

## Important Engineering Insight

Error response shape is part of the API contract.

# Question

Why does Phase 13 v1 use known dataset filenames?

## Short Answer

Because the validated inference contract is finalized temporal sequences, not arbitrary raw-video preprocessing.

## Deep Technical Explanation

The API accepts a video upload and uses its filename to resolve an existing finalized temporal sequence. This proves API upload handling and response flow without pretending the raw-video-to-feature path is fully production-ready.

## Engineering Reasoning

This keeps the implementation roadmap-aligned and honest.

## Why This Decision Was Taken

Phase 12 intentionally built offline inference before API. Raw-video hardening is a separate integration problem.

## Tradeoffs / Risks / Limitations

Users cannot upload arbitrary unseen videos yet.

## Important Engineering Insight

It is better to document a v1 limitation than silently fake a capability.

# Question

How does Phase 13 prepare the frontend?

## Short Answer

It provides a stable JSON response with prediction, score, feedback, and metadata.

## Deep Technical Explanation

The response contains the visible user information and enough debug data for engineering. A frontend can display shot class, confidence, technique score, tips, detailed feedback, and spoken feedback.

## Engineering Reasoning

Frontend integration needs predictable keys and error responses.

## Why This Decision Was Taken

The roadmap says Phase 13 prepares integration with the Smart Cricket web app.

## Tradeoffs / Risks / Limitations

Frontend UX still needs design and implementation outside this phase.

## Important Engineering Insight

API design is a contract between backend, ML, and frontend.

# Question

How does Phase 13 prepare Phase 14?

## Short Answer

It exposes `spoken_feedback` through the API so voice output can consume it.

## Deep Technical Explanation

Phase 14 can take the API response's spoken feedback text and pass it to a TTS service.

## Engineering Reasoning

Voice output should not regenerate feedback. It should use the existing spoken feedback string.

## Why This Decision Was Taken

The roadmap says voice comes after prediction, scoring, feedback, and API.

## Tradeoffs / Risks / Limitations

No audio is generated yet.

## Important Engineering Insight

Voice is an output layer over feedback, not a replacement for feedback logic.
