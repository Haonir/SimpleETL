"""SimpleETL FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ── API Key authentication middleware ──────────────────────────────────────

class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Validate X-API-Key header when APP_API_KEY env var is set."""

    # Endpoints that never require auth
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app, api_key: str | None = None):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if self.api_key and request.url.path not in self.EXEMPT_PATHS:
            provided = request.headers.get("x-api-key", "")
            if provided != self.api_key:
                return Response(
                    content='{"detail": "Invalid or missing API key"}',
                    status_code=401,
                    media_type="application/json",
                )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown."""
    from app.db import init_db

    init_db()
    logger.info("SimpleETL API starting")
    yield
    logger.info("SimpleETL API shutting down")


app = FastAPI(
    title="SimpleETL API",
    version="0.1.0",
    lifespan=lifespan,
)

# ── API Key middleware ──────────────────────────────────────────────────────
from app.settings import get_settings
_api_key = get_settings().api_key or None
if _api_key:
    logger.info("API key authentication enabled")
    app.add_middleware(ApiKeyMiddleware, api_key=_api_key)
else:
    logger.info("API key authentication disabled (APP_API_KEY not set)")

# ── CORS ────────────────────────────────────────────────────────────────────
allow_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
from app.api.v1 import files_router, jobs_router, ws_router  # noqa: E402

app.include_router(files_router)
app.include_router(jobs_router)
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
