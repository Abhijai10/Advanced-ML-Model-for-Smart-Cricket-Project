"""FastAPI application for Smart Cricket API integration."""

from __future__ import annotations

from pathlib import Path
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ml.src.voice.voice_config import AUDIO_OUTPUT_DIR

from .config import SETTINGS
from .routes import router
from .services import PHASE13_VERSION


app = FastAPI(
    title="Smart Cricket API",
    version=PHASE13_VERSION,
    description="Production-facing API wrapper around the Smart Cricket inference pipeline.",
)

logger = logging.getLogger("smart_cricket.api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(SETTINGS.allowed_origins),
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
        logger.exception(
            "request_failed",
            extra={"request_id": request_id, "path": request.url.path, "duration_ms": duration_ms},
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Smart Cricket API failed unexpectedly.",
                "error_code": "internal_error",
                "request_id": request_id,
            },
        )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    response.headers["x-process-time-ms"] = str(duration_ms)
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=Path(AUDIO_OUTPUT_DIR)), name="audio")
app.include_router(router)
