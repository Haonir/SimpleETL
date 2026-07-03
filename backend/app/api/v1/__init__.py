"""API v1 routers."""

from app.api.v1.config import router as config_router
from app.api.v1.websocket import router as ws_router  # noqa: E402

__all__ = ["config_router", "ws_router"]
