"""WebSocket connection manager for SimpleETL backend."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by job_id.

    Thread-safe via asyncio.Lock — all public methods are async and acquire
    the lock before touching internal state.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task | None = None

    # ── Public API ───────────────────────────────────────────────────────────

    async def connect(self, job_id: str, ws: WebSocket) -> None:
        """Accept a new WebSocket and register it in the given room."""
        async with self._lock:
            if job_id not in self._rooms:
                self._rooms[job_id] = set()
            self._rooms[job_id].add(ws)

        # Auto-start heartbeat if not already running
        if self._heartbeat_task is None or self._heartbeat_task.done():
            await self.start_heartbeat()

    async def disconnect(self, job_id: str, ws: WebSocket) -> None:
        """Remove a WebSocket from its room and cleanup empty rooms."""
        async with self._lock:
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
            disconnected: list[WebSocket] = []
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

    # ── Heartbeat / keepalive ───────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        """Background loop that pings all connections every 30 s."""
        while not self.stop_requested:
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                return
            async with self._lock:
                if not self._rooms:
                    continue
                disconnected: list[WebSocket] = []
                for job_id, conns in self._rooms.items():
                    for conn in conns:
                        try:
                            ping_msg = json.dumps({
                                "type": "ping",
                                "timestamp": asyncio.get_event_loop().time(),
                            })
                            await conn.send_text(ping_msg)
                        except Exception as exc:  # noqa: BLE001 — stale connection
                            logger.debug("Heartbeat failed for ws: %s", exc)
                            disconnected.append(conn)

                for conn in disconnected:
                    for room in self._rooms.values():
                        if conn in room:
                            room.discard(conn)
                            break
                    if not any(conn in room for room in self._rooms.values()):
                        pass  # connection was removed from all rooms

    async def start_heartbeat(self) -> None:
        """Start the background heartbeat task."""
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            return
        self.stop_requested = False
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        """Cancel and wait for the heartbeat task."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            return
        self.stop_requested = True
        try:
            await asyncio.wait_for(self._heartbeat_task, timeout=5.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        finally:
            self._heartbeat_task = None

    # ── Stop flag for heartbeat ──────────────────────────────────────────────

    @property
    def stop_requested(self) -> bool:
        """Whether the heartbeat loop should stop."""
        return getattr(self, "_stop_requested", False)

    @stop_requested.setter
    def stop_requested(self, value: bool) -> None:
        self._stop_requested = value


# ── Singleton ───────────────────────────────────────────────────────────────

_manager: ConnectionManager | None = None


def get_ws_manager() -> ConnectionManager:
    """Return the global singleton ConnectionManager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
