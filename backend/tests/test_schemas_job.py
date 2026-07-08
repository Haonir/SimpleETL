"""Unit tests for job Pydantic schemas."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.schemas.job import (
    JobCreateRequest,
    JobItem,
    JobListResponse,
    JobResponse,
    JobStatus,
)


# -- JobStatus tests --------------------------------------------------------


def test_job_status_enum_values():
    """JobStatus has exactly 5 string values."""
    values = {s.value for s in JobStatus}
    assert values == {"pending", "running", "completed", "stopped", "error"}


@pytest.mark.parametrize(
    "status_str",
    ["pending", "running", "completed", "stopped", "error"],
)
def test_job_status_serializes_to_string(status_str):
    """Each JobStatus value serializes as a plain string."""
    assert JobStatus(status_str).value == status_str


# -- JobItem tests -----------------------------------------------------------


def test_job_item_required_fields():
    """JobItem requires id, file_ids, config, created_at, file_count."""
    with pytest.raises(Exception):
        JobItem()  # type: ignore[call-arg]


def test_job_item_defaults():
    """JobItem defaults: status=pending, started_at=None, completed_at=None."""
    job = JobItem(
        id="abc-123",
        file_ids=["f1"],
        config={"llm": {}},
        created_at=datetime.now(timezone.utc),
        file_count=1,
    )
    assert job.status == JobStatus.pending
    assert job.started_at is None
    assert job.completed_at is None
    assert job.output_dir is None
    assert job.error_message is None


def test_job_item_with_all_fields():
    """JobItem accepts all optional fields."""
    now = datetime.now(timezone.utc)
    job = JobItem(
        id="abc-123",
        status=JobStatus.running,
        file_ids=["f1", "f2"],
        config={"llm": {}, "processing": {}},
        created_at=now,
        started_at=now,
        completed_at=now,
        output_dir="/tmp/jobs/abc/output",
        error_message=None,
        file_count=2,
    )
    assert job.status == JobStatus.running
    assert len(job.file_ids) == 2
    assert job.file_count == 2


def test_job_item_file_ids_min_length():
    """JobItem rejects empty file_ids list."""
    with pytest.raises(Exception):
        JobItem(
            id="abc",
            file_ids=[],
            config={},
            created_at=datetime.now(timezone.utc),
            file_count=0,
        )


def test_job_item_file_count_ge_1():
    """JobItem rejects file_count < 1."""
    with pytest.raises(Exception):
        JobItem(
            id="abc",
            file_ids=["f1"],
            config={},
            created_at=datetime.now(timezone.utc),
            file_count=0,
        )


def test_job_item_invalid_status():
    """JobItem rejects invalid status string."""
    with pytest.raises(Exception):
        JobItem(
            id="abc",
            file_ids=["f1"],
            config={},
            created_at=datetime.now(timezone.utc),
            file_count=1,
            status="invalid_status",  # type: ignore[arg-type]
        )


# -- JobCreateRequest tests --------------------------------------------------


def test_job_create_request_minimal():
    """JobCreateRequest requires file_ids and config."""
    req = JobCreateRequest(file_ids=["f1"], config={"llm": {}})
    assert req.file_ids == ["f1"]
    assert req.config == {"llm": {}}


def test_job_create_request_empty_file_ids():
    """JobCreateRequest rejects empty file_ids."""
    with pytest.raises(Exception):
        JobCreateRequest(file_ids=[], config={})  # type: ignore[arg-type]


# -- JobResponse tests -------------------------------------------------------


def test_job_response_wraps_job_item():
    """JobResponse wraps a JobItem."""
    now = datetime.now(timezone.utc)
    job = JobItem(
        id="x", file_ids=["f1"], config={}, created_at=now, file_count=1
    )
    resp = JobResponse(job=job)
    assert resp.job.id == "x"


# -- JobListResponse tests ---------------------------------------------------


def test_job_list_response_defaults():
    """JobListResponse defaults to empty list."""
    resp = JobListResponse(total=0)
    assert resp.jobs == []
    assert resp.total == 0


def test_job_list_response_with_jobs():
    """JobListResponse stores list of JobItem."""
    now = datetime.now(timezone.utc)
    job = JobItem(
        id="x", file_ids=["f1"], config={}, created_at=now, file_count=1
    )
    resp = JobListResponse(jobs=[job], total=1)
    assert len(resp.jobs) == 1
