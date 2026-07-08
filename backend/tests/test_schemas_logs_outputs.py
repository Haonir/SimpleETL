"""Unit tests for log + output Pydantic schemas."""

from __future__ import annotations

import pytest

from app.schemas.job import (
    JobLogEntry,
    JobLogsResponse,
    JobOutputItem,
    JobOutputsResponse,
)


# -- JobLogEntry tests -------------------------------------------------------


def test_job_log_entry_required_fields():
    """JobLogEntry requires timestamp, level, message."""
    with pytest.raises(Exception):
        JobLogEntry()  # type: ignore[call-arg]


def test_job_log_entry_defaults():
    """JobLogEntry has no defaults (all fields required)."""
    with pytest.raises(Exception):
        JobLogEntry(timestamp="")  # type: ignore[call-arg]


def test_job_log_entry_valid():
    """JobLogEntry accepts valid data."""
    entry = JobLogEntry(
        timestamp="2026-07-05T12:00:00",
        level="INFO",
        message="Processing started.",
    )
    assert entry.timestamp == "2026-07-05T12:00:00"
    assert entry.level == "INFO"
    assert entry.message == "Processing started."


def test_job_log_entry_invalid_timestamp():
    """JobLogEntry rejects empty timestamp."""
    with pytest.raises(Exception):
        JobLogEntry(timestamp="", level="INFO", message="test")  # type: ignore[arg-type]


# -- JobLogsResponse tests ---------------------------------------------------


def test_job_logs_response_defaults():
    """JobLogsResponse defaults to empty list."""
    resp = JobLogsResponse(total=0)
    assert resp.logs == []
    assert resp.total == 0


def test_job_logs_response_with_entries():
    """JobLogsResponse stores list of JobLogEntry."""
    entry1 = JobLogEntry(
        timestamp="2026-07-05T12:00:00", level="INFO", message="Step 1"
    )
    entry2 = JobLogEntry(
        timestamp="2026-07-05T12:01:00", level="WARNING", message="Slow chunk"
    )
    resp = JobLogsResponse(logs=[entry1, entry2], total=2)
    assert len(resp.logs) == 2
    assert resp.total == 2


def test_job_logs_response_total_ge_0():
    """JobLogsResponse rejects negative total."""
    with pytest.raises(Exception):
        JobLogsResponse(total=-1)  # type: ignore[arg-type]


# -- JobOutputItem tests -----------------------------------------------------


def test_job_output_item_required_fields():
    """JobOutputItem requires filename, file_path, size_bytes, format."""
    with pytest.raises(Exception):
        JobOutputItem()  # type: ignore[call-arg]


def test_job_output_item_valid():
    """JobOutputItem accepts valid data."""
    item = JobOutputItem(
        filename="output.spr",
        file_path="output.spr",
        size_bytes=1024,
        format="spr",
    )
    assert item.filename == "output.spr"
    assert item.file_path == "output.spr"
    assert item.size_bytes == 1024
    assert item.format == "spr"


def test_job_output_item_size_ge_0():
    """JobOutputItem rejects negative size_bytes."""
    with pytest.raises(Exception):
        JobOutputItem(
            filename="x", file_path="x", size_bytes=-1, format="spr"  # type: ignore[arg-type]
        )


# -- JobOutputsResponse tests ------------------------------------------------


def test_job_outputs_response_defaults():
    """JobOutputsResponse defaults to empty list."""
    resp = JobOutputsResponse(total=0)
    assert resp.outputs == []
    assert resp.total == 0


def test_job_outputs_response_with_items():
    """JobOutputsResponse stores list of JobOutputItem."""
    item1 = JobOutputItem(
        filename="a.spr", file_path="a.spr", size_bytes=500, format="spr"
    )
    item2 = JobOutputItem(
        filename="b.md", file_path="sub/b.md", size_bytes=300, format="markdown"
    )
    resp = JobOutputsResponse(outputs=[item1, item2], total=2)
    assert len(resp.outputs) == 2
    assert resp.total == 2


def test_job_outputs_response_total_ge_0():
    """JobOutputsResponse rejects negative total."""
    with pytest.raises(Exception):
        JobOutputsResponse(total=-1)  # type: ignore[arg-type]
