"""Unit tests for etl.callbacks module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.etl.callbacks import (
    create_callbacks,
    make_log_cb,
    make_log_error_cb,
    make_progress_cb,
    make_stop_cb,
)


@pytest.fixture
def mock_ws_manager():
    """Mock WebSocket connection manager."""
    manager = AsyncMock()
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def mock_job_service():
    """Mock JobService."""
    service = MagicMock()
    service.is_stopped = MagicMock(return_value=False)
    return service


@pytest.fixture
def event_loop():
    """Get the running event loop."""
    return asyncio.get_event_loop()


class TestMakeProgressCb:
    """Tests for make_progress_cb."""

    def test_broadcasts_progress_message(self, mock_ws_manager, event_loop):
        """Progress callback broadcasts correct WS message."""
        cb = make_progress_cb(mock_ws_manager, "job-123", event_loop)
        cb(50, 25, 0)

        # Allow async task to complete
        event_loop.run_until_complete(asyncio.sleep(0.01))

        mock_ws_manager.broadcast.assert_called_once()
        call_args = mock_ws_manager.broadcast.call_args
        assert call_args[0][0] == "job-123"
        msg = call_args[0][1]
        assert msg["type"] == "progress"
        assert msg["chunk_pct"] == 50
        assert msg["global_pct"] == 25
        assert msg["file_idx"] == 0

    def test_does_not_raise_on_broadcast_error(self, mock_ws_manager, event_loop):
        """Progress callback does not raise if broadcast fails."""
        mock_ws_manager.broadcast.side_effect = Exception("WS error")
        cb = make_progress_cb(mock_ws_manager, "job-123", event_loop)
        # Should not raise
        cb(50, 25, 0)


class TestMakeLogCb:
    """Tests for make_log_cb."""

    def test_broadcasts_log_message(self, mock_ws_manager, event_loop):
        """Log callback broadcasts correct WS message."""
        cb = make_log_cb(mock_ws_manager, "job-123", event_loop)
        cb("Processing started")

        event_loop.run_until_complete(asyncio.sleep(0.01))

        mock_ws_manager.broadcast.assert_called_once()
        msg = mock_ws_manager.broadcast.call_args[0][1]
        assert msg["type"] == "log"
        assert msg["level"] == "info"
        assert msg["message"] == "Processing started"


class TestMakeLogErrorCb:
    """Tests for make_log_error_cb."""

    def test_broadcasts_error_level(self, mock_ws_manager, event_loop):
        """Error log callback uses 'error' level."""
        cb = make_log_error_cb(mock_ws_manager, "job-123", event_loop)
        cb("Something failed")

        event_loop.run_until_complete(asyncio.sleep(0.01))

        msg = mock_ws_manager.broadcast.call_args[0][1]
        assert msg["level"] == "error"


class TestMakeStopCb:
    """Tests for make_stop_cb."""

    def test_returns_false_when_not_stopped(self, mock_job_service):
        """Stop callback returns False when job is not stopped."""
        cb = make_stop_cb(mock_job_service, "job-123")
        assert cb() is False

    def test_returns_true_when_stopped(self, mock_job_service):
        """Stop callback returns True when job is stopped."""
        mock_job_service.is_stopped.return_value = True
        cb = make_stop_cb(mock_job_service, "job-123")
        assert cb() is True

    def test_passes_correct_job_id(self, mock_job_service):
        """Stop callback passes correct job_id to is_stopped."""
        cb = make_stop_cb(mock_job_service, "job-456")
        cb()
        mock_job_service.is_stopped.assert_called_with("job-456")


class TestCreateCallbacks:
    """Tests for create_callbacks factory."""

    def test_returns_all_callbacks(self, mock_ws_manager, mock_job_service, event_loop):
        """create_callbacks returns dict with all 4 callback types."""
        callbacks = create_callbacks(mock_ws_manager, "job-123", event_loop, mock_job_service)
        assert "progress" in callbacks
        assert "log" in callbacks
        assert "log_error" in callbacks
        assert "stop" in callbacks
        assert callable(callbacks["progress"])
        assert callable(callbacks["log"])
        assert callable(callbacks["stop"])
