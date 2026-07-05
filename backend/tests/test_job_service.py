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
    from app.db import init_db

    # Initialize DB at the path that JobService will use
    db_path = str(tmp_path / "jobs" / "jobs.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(db_path)
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
def registered_file_id(tmp_path, service: JobService, monkeypatch) -> str:
    """Register a test file ID in the same DB that service uses."""
    from app.services.file_service import FileService
    from app.db import get_cursor

    fs = FileService(upload_dir=tmp_path / "uploads")
    file_id = "test-file-id-001"

    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO files (id, filename, size_bytes, content_type, uploaded_at) VALUES (?, ?, ?, ?, ?)",
            (file_id, "test.txt", 12, "text/plain", "2026-07-05T00:00:00"),
        )

    # Monkeypatch the import IN job_service module
    monkeypatch.setattr("app.services.job_service.get_file_service", lambda: fs)
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


def test_create_job_multiple_files(service: JobService, tmp_path, monkeypatch, sample_config: dict):
    """Creating a job with multiple valid file_ids succeeds."""
    from app.services.file_service import FileService
    from app.db import get_cursor

    fs = FileService(upload_dir=tmp_path / "uploads")
    ids = []
    db_path = str(tmp_path / "jobs" / "jobs.db")  # Same DB as service uses
    with get_cursor() as cur:
        for i in range(3):
            fid = f"file-{i}"
            cur.execute(
                "INSERT INTO files (id, filename, size_bytes, content_type, uploaded_at) VALUES (?, ?, ?, ?, ?)",
                (fid, f"file{i}.txt", 0, "text/plain", "2026-07-05T00:00:00"),
            )
            ids.append(fid)

    # Monkeypatch the import IN job_service module
    monkeypatch.setattr("app.services.job_service.get_file_service", lambda: fs)
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


# -- Get logs tests ----------------------------------------------------------


def test_get_logs_empty(service: JobService, registered_file_id: str, sample_config: dict):
    """get_logs() returns empty list when no log file exists."""
    job = service.create(file_ids=[registered_file_id], config=sample_config)
    assert service.get_logs(job.id) == []


def test_get_logs_with_entries(service: JobService, registered_file_id: str, sample_config: dict):
    """get_logs() reads and parses log entries from logs.json."""
    import json

    job = service.create(file_ids=[registered_file_id], config=sample_config)
    log_path = service._get_log_path(job.id)
    # Create parent directories for logs.json
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Write some test log entries
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"step": "extract", "message": "Reading file 1"}))
        f.write("\n")
        f.write(json.dumps({"step": "split", "message": "Chunked into 5 pieces"}))
        f.write("\n")

    entries = service.get_logs(job.id)
    assert len(entries) == 2
    assert entries[0]["step"] == "extract"
    assert entries[1]["step"] == "split"


def test_get_logs_invalid_json_ignored(service: JobService, registered_file_id: str, sample_config: dict):
    """get_logs() skips lines that are not valid JSON."""
    import json

    job = service.create(file_ids=[registered_file_id], config=sample_config)
    log_path = service._get_log_path(job.id)
    # Create parent directories for logs.json
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"step": "ok"}))
        f.write("\n")
        f.write("not valid json\n")
        f.write(json.dumps({"step": "also_ok"}))

    entries = service.get_logs(job.id)
    assert len(entries) == 2


# -- Delete job files tests --------------------------------------------------


def test_delete_job_files_removes_directory(service: JobService, registered_file_id: str, sample_config: dict):
    """delete_job_files() removes the output directory from disk."""
    import shutil

    job = service.create(file_ids=[registered_file_id], config=sample_config)
    output_dir = Path(job.output_dir)
    # Create the output directory before writing a dummy file
    output_dir.mkdir(parents=True, exist_ok=True)
    # Create a dummy file in output dir to verify it gets deleted
    (output_dir / "dummy.txt").write_text("test")
    assert (output_dir / "dummy.txt").exists()

    service.delete_job_files(job.id)
    assert not (output_dir / "dummy.txt").exists()


def test_delete_job_files_removes_from_db(service: JobService, registered_file_id: str, sample_config: dict):
    """delete_job_files() removes the job record from SQLite."""
    import shutil

    job = service.create(file_ids=[registered_file_id], config=sample_config)
    assert service.get(job.id) is not None

    service.delete_job_files(job.id)
    assert service.get(job.id) is None


def test_delete_job_files_nonexistent(service: JobService):
    """delete_job_files() does nothing for nonexistent job."""
    # Should not raise
    service.delete_job_files("nonexistent")
