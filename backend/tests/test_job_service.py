"""Unit tests for JobService."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.schemas.file import FileItem
from app.schemas.job import JobStatus
from app.services.file_service import FileService
from app.services.job_service import JobService


@pytest.fixture
def file_service(tmp_path: Path) -> FileService:
    """Create an isolated FileService."""
    return FileService(upload_dir=tmp_path / "uploads")


@pytest.fixture
def service(tmp_path: Path, file_service: FileService) -> JobService:
    """Create an isolated JobService with isolated output dir."""
    return JobService(output_base_dir=tmp_path / "jobs")


@pytest.fixture
def sample_config() -> dict:
    """Sample ETL config for tests."""
    return {
        "llm": {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
        "processing": {"chunk_size": 10000, "chunk_overlap": 1500, "max_workers": 1, "output_format": "spr"},
        "prompt_text": "Analyze this text.",
    }


@pytest.fixture
def registered_file_id(file_service: FileService, monkeypatch) -> str:
    """Register a fake file in FileService and patch the global singleton."""
    from app.services import job_service as js_mod

    # Reset singleton so get_file_service uses our patched version
    js_mod._job_service = None

    # Patch get_file_service to return our isolated file_service
    monkeypatch.setattr(js_mod, "get_file_service", lambda: file_service)

    file_id = "test-file-id-001"
    item = FileItem(
        id=file_id,
        filename="test.txt",
        size_bytes=100,
        content_type="text/plain",
        uploaded_at=datetime.now(timezone.utc),
    )
    file_service._files[file_id] = item
    return file_id


# -- Create tests ------------------------------------------------------------


def test_create_job_success(service: JobService, registered_file_id: str, sample_config: dict):
    """Creating a job with valid file_id succeeds."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    assert job.id
    assert job.status == JobStatus.pending
    assert job.file_ids == [registered_file_id]
    assert job.file_count == 1
    assert job.output_dir is not None


def test_create_job_empty_file_ids(service: JobService, sample_config: dict):
    """Creating a job with empty file_ids raises ValueError."""
    with pytest.raises(ValueError, match="At least one file_id"):
        service.create(file_ids=[], config=sample_config)


def test_create_job_invalid_file_id(service: JobService, sample_config: dict):
    """Creating a job with nonexistent file_id raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        service.create(file_ids=["nonexistent-id"], config=sample_config)


def test_create_job_assigns_uuid(service: JobService, registered_file_id: str, sample_config: dict):
    """Created job has a UUID string as ID."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    assert isinstance(job.id, str)
    assert len(job.id) == 36  # UUID4 format: 8-4-4-4-12


def test_create_job_output_dir(service: JobService, registered_file_id: str, sample_config: dict):
    """Created job has output_dir set to /jobs/{id}/output."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    assert job.output_dir.endswith(f"/{job.id}/output")


def test_create_job_multiple_files(service: JobService, file_service: FileService, monkeypatch, sample_config: dict):
    """Creating a job with multiple valid file_ids succeeds."""
    from app.services import job_service as js_mod

    # Patch get_file_service to return our isolated file_service
    monkeypatch.setattr(js_mod, "get_file_service", lambda: file_service)

    ids = []
    for i in range(3):
        fid = f"file-{i}"
        file_service._files[fid] = FileItem(
            id=fid, filename=f"doc{i}.txt", size_bytes=10,
            content_type="text/plain", uploaded_at=datetime.now(timezone.utc),
        )
        ids.append(fid)
    job = service.create(file_ids=ids, config=sample_config)
    assert job.file_count == 3
    assert len(job.file_ids) == 3


# -- Get tests ---------------------------------------------------------------


def test_get_job_exists(service: JobService, registered_file_id: str, sample_config: dict):
    """get() returns JobItem for existing job."""
    created = service.create(file_ids=[registered_file_id], config=sample_config)
    found = service.get(created.id)
    assert found is not None
    assert found.id == created.id


def test_get_job_not_found(service: JobService):
    """get() returns None for nonexistent job."""
    assert service.get("nonexistent") is None


# -- List tests --------------------------------------------------------------


def test_list_all_empty(service: JobService):
    """list_all() returns empty list when no jobs."""
    assert service.list_all() == []


def test_list_all_with_jobs(service: JobService, registered_file_id: str, sample_config: dict):
    """list_all() returns all created jobs."""
    j1 = service.create(file_ids=[registered_file_id], config=sample_config)
    j2 = service.create(file_ids=[registered_file_id], config=sample_config)
    jobs = service.list_all()
    assert len(jobs) == 2
    ids = {j.id for j in jobs}
    assert j1.id in ids
    assert j2.id in ids


# -- Update status tests -----------------------------------------------------


def test_update_status_running_sets_started_at(service: JobService, registered_file_id: str, sample_config: dict):
    """Transitioning to 'running' sets started_at."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    assert job.started_at is None
    updated = service.update_status(job.id, JobStatus.running)
    assert updated.started_at is not None
    assert updated.status == JobStatus.running


def test_update_status_completed_sets_completed_at(service: JobService, registered_file_id: str, sample_config: dict):
    """Transitioning to 'completed' sets completed_at."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    service.update_status(job.id, JobStatus.running)
    updated = service.update_status(job.id, JobStatus.completed)
    assert updated.completed_at is not None
    assert updated.status == JobStatus.completed


def test_update_status_not_found(service: JobService):
    """update_status() raises KeyError for nonexistent job."""
    with pytest.raises(KeyError):
        service.update_status("nonexistent", JobStatus.running)


def test_update_status_error_with_message(service: JobService, registered_file_id: str, sample_config: dict):
    """Transitioning to 'error' with error_message stores it."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    updated = service.update_status(job.id, JobStatus.error, error_message="LLM timeout")
    assert updated.error_message == "LLM timeout"
    assert updated.completed_at is not None


def test_update_status_stopped_sets_completed_at(service: JobService, registered_file_id: str, sample_config: dict):
    """Transitioning to 'stopped' also sets completed_at."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    updated = service.update_status(job.id, JobStatus.stopped)
    assert updated.completed_at is not None
    assert updated.status == JobStatus.stopped


# -- Stop tests --------------------------------------------------------------


def test_request_stop(service: JobService, registered_file_id: str, sample_config: dict):
    """request_stop() sets the stop flag."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    assert service.is_stopped(job.id) is False
    service.request_stop(job.id)
    assert service.is_stopped(job.id) is True


def test_request_stop_not_found(service: JobService):
    """request_stop() raises KeyError for nonexistent job."""
    with pytest.raises(KeyError):
        service.request_stop("nonexistent")


def test_is_stopped_default_false(service: JobService):
    """is_stopped() returns False for unknown job_id."""
    assert service.is_stopped("unknown") is False


# -- Delete tests ------------------------------------------------------------


def test_delete_job(service: JobService, registered_file_id: str, sample_config: dict):
    """delete() removes job from registry."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    assert service.delete(job.id) is True
    assert service.get(job.id) is None


def test_delete_job_not_found(service: JobService):
    """delete() returns False for nonexistent job."""
    assert service.delete("nonexistent") is False


def test_delete_cleans_stop_flag(service: JobService, registered_file_id: str, sample_config: dict):
    """delete() also removes the stop flag."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    service.request_stop(job.id)
    service.delete(job.id)
    assert service.is_stopped(job.id) is False


# -- Singleton test ----------------------------------------------------------


def test_singleton_returns_same_instance():
    """get_job_service() returns same instance."""
    import app.services.job_service as mod
    mod._job_service = None

    s1 = get_job_service()
    s2 = get_job_service()
    assert s1 is s2
    mod._job_service = None  # cleanup


def get_job_service():
    from app.services.job_service import get_job_service as _get
    return _get()
