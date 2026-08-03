"""FastAPI application for Phase 13 Smart Cricket API integration."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .services import PHASE13_VERSION


app = FastAPI(
    title="Smart Cricket API",
    version=PHASE13_VERSION,
    description="Phase 13 API wrapper around the Phase 12 offline inference pipeline.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router)
