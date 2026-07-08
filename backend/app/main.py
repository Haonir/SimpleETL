"""SimpleETL FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ── API Key authentication middleware ──────────────────────────────────────

class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Validate X-API-Key header when APP_API_KEY env var is set."""

    # Endpoints that never require auth
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/api/v1/capabilities"}

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

    # Use DB in backend/ directory (persistent across restarts)
    db_path = str(Path(__file__).parent.parent / "simpleetl.db")
    init_db(db_path)
    settings = get_settings()
    settings.ensure_data_dirs()
    logger.info("Data directories: %s", settings.app_data_dir)
    logger.info("SimpleETL API starting (db=%s)", db_path)
    yield
    logger.info("SimpleETL API shutting down")


app = FastAPI(
    title="SimpleETL API",
    version="1.0.0",
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
from app.api.v1 import config_router, files_router, jobs_router, ws_router  # noqa: E402


@app.get("/api/v1/capabilities")
async def capabilities():
    """Return system capabilities (OCR availability, supported input formats)."""
    from app.etl.extractor import OCR_AVAILABLE

    return {
        "ocr_available": OCR_AVAILABLE,
        "supported_input_formats": [".txt", ".md", ".docx", ".doc", ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"],
    }


app.include_router(files_router)
app.include_router(jobs_router)
app.include_router(ws_router)
app.include_router(config_router)

# ── Static files (Vue frontend) ─────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve Vue SPA — all non-API routes return index.html."""
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(static_dir / "index.html"))

@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    from app.settings import get_settings

    settings = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.server_port, reload=True)
