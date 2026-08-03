"""FastAPI application for Phase 13 Smart Cricket API integration."""

from __future__ import annotations

from fastapi import FastAPI

from .routes import router
from .services import PHASE13_VERSION


app = FastAPI(
    title="Smart Cricket API",
    version=PHASE13_VERSION,
    description="Phase 13 API wrapper around the Phase 12 offline inference pipeline.",
)

app.include_router(router)
