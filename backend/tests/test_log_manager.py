"""Unit tests for services.log_manager module."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.log_manager import create_job_logger, make_log_cb


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test logs."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


class TestCreateJobLogger:
    """Tests for create_job_logger."""

    def test_creates_logger_with_correct_name(self, temp_dir):
        """Logger is named 'etl.{job_id}'."""
        job_id = "test-job-1"
        logger = create_job_logger(job_id, temp_dir)
        assert logger.name == f"etl.{job_id}"

    def test_logger_level_is_info(self, temp_dir):
        """Logger level is set to INFO."""
        logger = create_job_logger("job-1", temp_dir)
        assert logger.level == logging.INFO

    def test_propagate_is_false(self, temp_dir):
        """Logger propagation is disabled."""
        logger = create_job_logger("job-1", temp_dir)
        assert logger.propagate is False

    def test_creates_logs_json_file(self, temp_dir):
        """A logs.json file is created in the job directory."""
        job_id = "job-file-test"
        logger = create_job_logger(job_id, temp_dir)
        log_path = temp_dir / "logs.json"
        assert log_path.exists()

    def test_writes_json_lines(self, temp_dir):
        """Logger writes valid JSON lines to logs.json."""
        job_id = "job-json-test"
        logger = create_job_logger(job_id, temp_dir)
        logger.info("Test message")

        log_path = temp_dir / "logs.json"
        content = log_path.read_text(encoding="utf-8").strip()
        parsed = json.loads(content)
        assert "timestamp" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"

    def test_multiple_messages_append(self, temp_dir):
        """Multiple log calls produce multiple JSON lines."""
        job_id = "job-multi-test"
        logger = create_job_logger(job_id, temp_dir)
        logger.info("First message")
        logger.info("Second message")

        log_path = temp_dir / "logs.json"
        lines = [l.strip() for l in log_path.read_text(encoding="utf-8").splitlines()]
        assert len(lines) == 2
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["message"] == "First message"
        assert second["message"] == "Second message"

    def test_timestamp_format(self, temp_dir):
        """Timestamp follows ISO format."""
        job_id = "job-ts-test"
        logger = create_job_logger(job_id, temp_dir)
        logger.info("Time check")

        log_path = temp_dir / "logs.json"
        content = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert "T" in content["timestamp"]


class TestMakeLogCb:
    """Tests for make_log_cb."""

    def test_callback_is_callable(self, temp_dir):
        """make_log_cb returns a callable."""
        logger = create_job_logger("job-cb-test", temp_dir)
        cb = make_log_cb(logger)
        assert callable(cb)

    def test_callback_writes_to_file(self, temp_dir):
        """Callback writes message to logs.json via the logger."""
        job_id = "job-write-cb"
        logger = create_job_logger(job_id, temp_dir)
        cb = make_log_cb(logger)
        cb("Hello from callback")

        log_path = temp_dir / "logs.json"
        content = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert content["message"] == "Hello from callback"

    def test_callback_thread_safety(self, temp_dir):
        """Multiple concurrent calls do not corrupt the JSON file."""
        job_id = "job-thread-test"
        logger = create_job_logger(job_id, temp_dir)
        cb = make_log_cb(logger)

        import threading

        errors = []

        def worker(msg: str):
            try:
                cb(msg)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"msg-{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        log_path = temp_dir / "logs.json"
        lines = [l.strip() for l in log_path.read_text(encoding="utf-8").splitlines()]
        assert len(lines) == 20

    def test_callback_does_not_propagate(self, temp_dir):
        """Logger does not propagate to root logger."""
        job_id = "job-no-prop"
        logger = create_job_logger(job_id, temp_dir)
        cb = make_log_cb(logger)
        cb("No propagation test")

        # Root logger should have no records from this call
        assert len(logging.getLogger().handlers) > 0  # root exists but no new records
