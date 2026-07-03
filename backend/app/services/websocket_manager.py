"""WebSocket connection manager for SimpleETL backend."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by job_id.

    Thread-safe via asyncio.Lock — all public methods are async and acquire
    the lock before touching internal state.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[asyncio.WebSocket]] = {}
        self._lock = asyncio.Lock()

    # ── Public API ───────────────────────────────────────────────────────────

    async def connect(self, job_id: str, ws: asyncio.WebSocket) -> None:
        """Accept a new WebSocket and register it in the given room."""
        async with self._lock:
            if job_id not in self._rooms:
                self._rooms[job_id] = set()
            self._rooms[job_id].add(ws)

    async def disconnect(self, job_id: str, ws: asyncio.WebSocket) -> None:
        """Remove a WebSocket from its room and cleanup empty rooms."""
        if job_id in self._rooms:
            self._rooms[job_id].discard(ws)
            if not self._rooms[job_id]:
                del self._rooms[job_id]

    async def broadcast(self, job_id: str, message: dict[str, Any]) -> None:
        """Send a JSON-encoded message to all connections in the given room."""
        data = json.dumps(message)
        async with self._lock:
            if job_id not in self._rooms or not self._rooms[job_id]:
                return
            disconnected: list[asyncio.WebSocket] = []
            for conn in self._rooms[job_id]:
                try:
                    await conn.send_text(data)
                except Exception as exc:  # noqa: BLE001 — connection may be closed
                    logger.debug("Failed to send to ws: %s", exc)
                    disconnected.append(conn)

            for conn in disconnected:
                self._rooms[job_id].discard(conn)
            if not self._rooms[job_id]:
                del self._rooms[job_id]

    async def has_connections(self, job_id: str) -> bool:
        """Return True if the room for *job_id* currently has active connections."""
        async with self._lock:
            return job_id in self._rooms and len(self._rooms[job_id]) > 0


# ── Singleton ───────────────────────────────────────────────────────────────

_manager: ConnectionManager | None = None


def get_ws_manager() -> ConnectionManager:
    """Return the global singleton ConnectionManager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
