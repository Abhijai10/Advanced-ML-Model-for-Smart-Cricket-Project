# Phase 13 — Quick Revision Pack

# Question

What did Phase 13 add to the project?

## Quick Answer

It added FastAPI backend integration.
Endpoints:
`GET /health`
`POST /analyze`
The API calls the Phase 12 inference pipeline and returns structured JSON.

# Question

Why should API logic stay separate from ML logic?

## Quick Answer

API handles transport: upload, validation, response, errors.
ML logic stays in Phase 12.
This avoids duplicated model/scoring/feedback behavior.

# Question

What endpoints were implemented?

## Quick Answer

`GET /health` checks readiness.
`POST /analyze` accepts a video upload and returns prediction, score, feedback, debug metadata, and API metadata.

# Question

How does Phase 13 handle errors?

## Quick Answer

Invalid user inputs return structured 422 errors.
Unexpected analysis failures return structured 500 errors.
This gives the frontend clean error handling.

# Question

Why does Phase 13 v1 use known dataset filenames?

## Quick Answer

The validated inference contract is currently finalized `[60,32]` temporal sequences.
The upload filename resolves to a known dataset sequence.
Arbitrary raw-video preprocessing is future hardening.

# Question

How does Phase 13 prepare the frontend?

## Quick Answer

It returns stable JSON with shot prediction, confidence, technique score, tips, detailed feedback, spoken feedback, and metadata.
Frontend can consume this directly.

# Question

How does Phase 13 prepare Phase 14?

## Quick Answer

The API exposes `spoken_feedback`.
Phase 14 can convert that text into audio without regenerating feedback.
