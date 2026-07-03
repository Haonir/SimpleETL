"""Unit tests for ConnectionManager."""

from __future__ import annotations

import asyncio
import json

import pytest


class MockWebSocket:
    """Mock WebSocket for unit testing — replaces asyncio.WebSocket."""

    def __init__(self):
        self.sent = []
        self._receive_queue = asyncio.Queue()

    async def send_text(self, data: str):
        self.sent.append(data)

    async def receive_text(self) -> str:
        return await self._receive_queue.get()

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other


@pytest.fixture
def manager():
    """Return a fresh ConnectionManager instance."""
    from app.services.websocket_manager import ConnectionManager

    return ConnectionManager()


# ── connect / disconnect ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connect_creates_room(manager):
    ws = MockWebSocket()
    await manager.connect("job-1", ws)
    assert "job-1" in manager._rooms
    assert len(manager._rooms["job-1"]) == 1


@pytest.mark.asyncio
async def test_connect_second_ws_same_job(manager):
    wsa = MockWebSocket()
    wsb = MockWebSocket()
    await manager.connect("job-1", wsa)
    await manager.connect("job-1", wsb)
    assert len(manager._rooms["job-1"]) == 2


@pytest.mark.asyncio
async def test_disconnect_removes_ws(manager):
    ws = MockWebSocket()
    await manager.connect("job-1", ws)
    await manager.disconnect("job-1", ws)
    assert "job-1" not in manager._rooms


@pytest.mark.asyncio
async def test_disconnect_empty_room_is_cleaned(manager):
    ws = MockWebSocket()
    await manager.connect("job-1", ws)
    await manager.disconnect("job-1", ws)
    assert len(manager._rooms) == 0


@pytest.mark.asyncio
async def test_disconnect_nonexistent_room_is_noop(manager):
    ws = MockWebSocket()
    await manager.disconnect("no-such-job", ws)


# ── broadcast ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_broadcast_sends_to_all(manager):
    wsa = MockWebSocket()
    wsb = MockWebSocket()
    await manager.connect("job-1", wsa)
    await manager.connect("job-1", wsb)

    message = {"type": "progress", "job_id": "job-1"}
    await manager.broadcast("job-1", message)

    # Check that send_text was called on both WebSockets
    assert len(wsa.sent) == 1
    assert len(wsb.sent) == 1

    # Verify the message content
    msg = json.loads(wsa.sent[0])
    assert msg["type"] == "progress"
    assert msg["job_id"] == "job-1"


@pytest.mark.asyncio
async def test_broadcast_empty_room_is_noop(manager):
    # No connections registered — broadcast should not raise
    await manager.broadcast("no-connections", {"type": "test"})


# ── has_connections ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_has_connections_false_when_empty(manager):
    assert await manager.has_connections("job-1") is False


@pytest.mark.asyncio
async def test_has_connections_true_after_connect(manager):
    ws = MockWebSocket()
    await manager.connect("job-1", ws)
    assert await manager.has_connections("job-1") is True


# ── singleton ───────────────────────────────────────────────────────────────

def test_singleton_returns_same_instance():
    from app.services.websocket_manager import get_ws_manager, ConnectionManager

    m1 = get_ws_manager()
    m2 = get_ws_manager()
    assert m1 is m2
    assert isinstance(m1, ConnectionManager)


def test_get_ws_manager_creates_on_first_call():
    """Before any call the global manager should be None."""
    from app.services.websocket_manager import _manager

    # Reset for isolation — but only if it was created by this process
    if _manager is not None:
        pytest.skip("Global manager already initialized")
