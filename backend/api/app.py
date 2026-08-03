"""FastAPI application for Smart Cricket API integration."""

from __future__ import annotations

from pathlib import Path
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
    try:
        response = await call_next(request)
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Smart Cricket API failed unexpectedly.",
                "error_code": "internal_error",
                "request_id": request_id,
            },
        )
    response.headers["x-request-id"] = request_id
    return response


AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=Path(AUDIO_OUTPUT_DIR)), name="audio")
app.include_router(router)
