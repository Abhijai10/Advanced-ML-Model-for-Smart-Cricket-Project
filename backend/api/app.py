"""FastAPI application for Smart Cricket API integration."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ml.src.voice.voice_config import AUDIO_OUTPUT_DIR

from .audio import router as audio_router
from .config import SETTINGS, normalize_origins
from .observability import METRICS, initialize_sentry, pseudonymous_user_id
from .routes import router
from .services import PHASE13_VERSION, terminate_active_workers


@asynccontextmanager
async def lifespan(_app: FastAPI):
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        yield
    finally:
        terminate_active_workers()


app = FastAPI(
    title="Smart Cricket API",
    version=PHASE13_VERSION,
    description="Production-facing API wrapper around the Smart Cricket inference pipeline.",
    lifespan=lifespan,
)

logger = logging.getLogger("smart_cricket.api")
initialize_sentry()

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(normalize_origins(SETTINGS.allowed_origins)),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        METRICS.increment("smart_cricket_request", route=request.url.path, method=request.method, status="500")
        METRICS.observe("smart_cricket_request_latency", duration_ms / 1000.0, route=request.url.path, method=request.method)
        logger.exception(
            "request_failed",
            extra={
                "event": "request_failed",
                "request_id": request_id,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "user_id_hash": pseudonymous_user_id(getattr(getattr(request.state, "auth", None), "user_id", None)),
            },
        )
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "Smart Cricket API failed unexpectedly.",
                "error_code": "internal_error",
                "request_id": request_id,
            },
        )
        _set_security_headers(response, request.url.path)
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = str(duration_ms)
        return response
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    response.headers["x-process-time-ms"] = str(duration_ms)
    _set_security_headers(response, request.url.path)
    METRICS.increment("smart_cricket_request", route=request.url.path, method=request.method, status=str(response.status_code))
    METRICS.observe("smart_cricket_request_latency", duration_ms / 1000.0, route=request.url.path, method=request.method)
    logger.info(
        "request_completed",
        extra={
            "event": "request_completed",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id_hash": pseudonymous_user_id(getattr(getattr(request.state, "auth", None), "user_id", None)),
        },
    )
    return response


def _set_security_headers(response, path: str) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if path not in {"/health", "/ready", "/capabilities", "/metrics"}:
        response.headers.setdefault("Cache-Control", "no-store")


app.include_router(audio_router)
app.include_router(router)
