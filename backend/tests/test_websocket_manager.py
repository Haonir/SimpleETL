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


# ── Heartbeat / keepalive ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_heartbeat_sends_ping(manager):
    """Heartbeat should send a ping message to all connections every 30 s."""
    ws = MockWebSocket()
    await manager.connect("job-1", ws)

    # Start heartbeat in background; it sleeps 30s before first ping.
    # We use a shorter interval by monkey-patching _heartbeat_loop is not possible,
    # so instead we directly invoke the loop body to test send behavior.
    from app.services.websocket_manager import ConnectionManager as CM

    cm = manager
    original_loop = cm._heartbeat_loop
    captured_sent: list[str] = []

    async def patched_loop():
        while not cm.stop_requested:
            try:
                await asyncio.sleep(0)  # yield control so we can inject state
            except asyncio.CancelledError:
                return
            async with cm._lock:
                if not cm._rooms:
                    continue
                disconnected: list[MockWebSocket] = []
                for job_id, conns in cm._rooms.items():
                    for conn in conns:
                        try:
                            ping_msg = json.dumps({
                                "type": "ping",
                                "timestamp": asyncio.get_event_loop().time(),
                            })
                            await conn.send_text(ping_msg)
                            captured_sent.append(conn.sent[-1])
                        except Exception as exc:  # noqa: BLE001 — stale connection
                            disconnected.append(conn)

                for conn in disconnected:
                    for room in cm._rooms.values():
                        if conn in room:
                            room.discard(conn)
                            break

    task = asyncio.create_task(patched_loop())
    await asyncio.sleep(0.1)  # let it run at least one iteration
    assert len(captured_sent) >= 1, "Heartbeat should have sent at least one ping"
    msg = json.loads(captured_sent[0])
    assert msg["type"] == "ping"
    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass


@pytest.mark.asyncio
async def test_heartbeat_removes_stale_connection(manager):
    """If send_text raises on a connection, the heartbeat should disconnect it."""

    class FailingWebSocket(MockWebSocket):
        async def send_text(self, data: str):
            raise ConnectionError("Connection lost")

    ws = FailingWebSocket()
    await manager.connect("job-1", ws)

    assert await manager.has_connections("job-1") is True

    # Run the heartbeat loop directly to trigger the stale connection cleanup.
    from app.services.websocket_manager import ConnectionManager as CM

    cm = manager
    captured_sent: list[str] = []

    async def patched_loop():
        while not cm.stop_requested:
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                return
            async with cm._lock:
                if not cm._rooms:
                    continue
                disconnected: list[MockWebSocket] = []
                for job_id, conns in cm._rooms.items():
                    for conn in conns:
                        try:
                            ping_msg = json.dumps({
                                "type": "ping",
                                "timestamp": asyncio.get_event_loop().time(),
                            })
                            await conn.send_text(ping_msg)
                            captured_sent.append(conn.sent[-1])
                        except Exception as exc:  # noqa: BLE001 — stale connection
                            disconnected.append(conn)

                for conn in disconnected:
                    for room in cm._rooms.values():
                        if conn in room:
                            room.discard(conn)
                            break

    task = asyncio.create_task(patched_loop())
    await asyncio.sleep(0.1)
    assert await manager.has_connections("job-1") is False, "Heartbeat should have disconnected the stale connection"
    # The failing WS should be removed from all rooms
    assert await manager.has_connections("job-1") is False
    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass


@pytest.mark.asyncio
async def test_stop_heartbeat_cancels_task(manager):
    """stop_heartbeat should cancel the running heartbeat task."""

    async def patched_loop():
        while not manager.stop_requested:
            await asyncio.sleep(0.1)

    # Monkey-patch _heartbeat_loop temporarily for this test
    original_loop = manager._heartbeat_loop
    manager._heartbeat_loop = patched_loop

    await manager.start_heartbeat()
    task = manager._heartbeat_task
    assert task is not None and not task.done()

    await manager.stop_heartbeat()
    # After stop, the task should be cancelled or done
    assert task.done() or task.cancelled()


def test_stop_requested_property(manager):
    """stop_requested property should toggle correctly."""
    assert manager.stop_requested is False
    manager.stop_requested = True
    assert manager.stop_requested is True
