"""Tests for REST endpoints /jobs/{id}/logs and /jobs/{id}/outputs."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.jobs import router


@pytest.fixture(autouse=True)
def reset_job_service():
    """Reset JobService singleton between tests."""
    from app.services.job_service import get_job_service, _job_service

    original = _job_service
    _job_service = None
    yield
    _job_service = original


@pytest.fixture
def client(tmp_path: Path):
    """Create a FastAPI TestClient with the jobs router and isolated JobService."""
    from app.db import init_db
    from app.services.job_service import JobService

    db_path = str(tmp_path / "jobs" / "jobs.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(db_path)

    service = JobService(output_base_dir=tmp_path / "jobs")

    # Monkeypatch the reference in the endpoint module (not the source module)
    import app.api.v1.jobs as endpoint_mod
    original_get = endpoint_mod.get_job_service
    endpoint_mod.get_job_service = lambda: service

    app = FastAPI()
    app.include_router(router)
    yield TestClient(app), service

    # Restore original
    endpoint_mod.get_job_service = original_get


@pytest.fixture
def sample_config() -> dict:
    """Sample ETL config for tests."""
    return {
        "llm": {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
        "processing": {"chunk_size": 10000, "chunk_overlap": 1500, "max_workers": 1, "output_format": "spr"},
        "prompt_text": "Analyze this text.",
    }


@pytest.fixture
def registered_file_id(client: tuple) -> str:
    """Register a test file ID in the same DB that client uses."""
    test_client, service = client
    from app.db import get_cursor

    file_id = "test-file-id-001"

    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO files (id, filename, size_bytes, content_type, uploaded_at) VALUES (?, ?, ?, ?, ?)",
            (file_id, "test.txt", 12, "text/plain", "2026-07-05T00:00:00"),
        )

    return file_id


# -- GET /jobs/{job_id}/logs --------------------------------------------------


def test_get_logs_not_found(client: tuple[TestClient, object], sample_config: dict, registered_file_id: str):
    """GET /jobs/{id}/logs returns 404 for nonexistent job."""
    test_client, service = client

    resp = test_client.get(f"/api/v1/jobs/{uuid.uuid4()}/logs")
    assert resp.status_code == 404

def test_get_logs_empty(client: tuple[TestClient, object], sample_config: dict, registered_file_id: str):
    """GET /jobs/{id}/logs returns empty list when no log file exists."""
    test_client, service = client

    job = service.create(file_ids=[registered_file_id], config=sample_config)

    resp = test_client.get(f"/api/v1/jobs/{job.id}/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["logs"] == []


def test_get_logs_with_entries(client: tuple[TestClient, object], sample_config: dict, registered_file_id: str):
    """GET /jobs/{id}/logs returns log entries from logs.json."""
    test_client, service = client

    job = service.create(file_ids=[registered_file_id], config=sample_config)

    # Create logs.json in the correct location
    job_dir = Path(job.output_dir).parent  # job_id directory
    job_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / "logs.json"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": "2026-07-05T12:00:00", "level": "INFO", "message": "Step 1"}))
        f.write("\n")
        f.write(json.dumps({"timestamp": "2026-07-05T12:01:00", "level": "WARNING", "message": "Slow chunk"}))
        f.write("\n")

    resp = test_client.get(f"/api/v1/jobs/{job.id}/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["logs"]) == 2
    assert data["logs"][0]["timestamp"] == "2026-07-05T12:00:00"
    assert data["logs"][0]["level"] == "INFO"
    assert data["logs"][0]["message"] == "Step 1"
    assert data["logs"][1]["level"] == "WARNING"


def test_get_logs_invalid_json_ignored(client: tuple[TestClient, object], sample_config: dict, registered_file_id: str):
    """GET /jobs/{id}/logs skips lines that are not valid JSON."""
    test_client, service = client

    job = service.create(file_ids=[registered_file_id], config=sample_config)
    # Create logs.json in the correct location
    job_dir = Path(job.output_dir).parent  # job_id directory
    job_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / "logs.json"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": "2026-07-05T12:00:00", "level": "INFO", "message": "ok"}))
        f.write("\n")
        f.write("not valid json\n")
        f.write(json.dumps({"timestamp": "2026-07-05T12:01:00", "level": "ERROR", "message": "fail"}))

    resp = test_client.get(f"/api/v1/jobs/{job.id}/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


def test_get_logs_response_schema(client: tuple[TestClient, object], sample_config: dict, registered_file_id: str):
    """GET /jobs/{id}/logs response matches JobLogsResponse schema."""
    test_client, service = client

    job = service.create(file_ids=[registered_file_id], config=sample_config)
    log_path = Path(job.output_dir, "logs.json")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": "2026-07-05T12:00:00", "level": "INFO", "message": "test"}))

    resp = test_client.get(f"/api/v1/jobs/{job.id}/logs")
    assert resp.status_code == 200
    data = resp.json()
    # Verify response structure matches JobLogsResponse
    assert "logs" in data
    assert "total" in data
    assert isinstance(data["logs"], list)
    assert isinstance(data["total"], int)


# -- GET /jobs/{job_id}/outputs -----------------------------------------------


def test_get_outputs_not_found(client: tuple[TestClient, object], sample_config: dict, registered_file_id: str):
    """GET /jobs/{id}/outputs returns 404 for nonexistent job."""
    test_client, service = client

    resp = test_client.get(f"/api/v1/jobs/nonexistent-id/outputs")
    assert resp.status_code == 404


def test_get_outputs_empty(client: tuple[TestClient, object], sample_config: dict, registered_file_id: str):
    """GET /jobs/{id}/outputs returns empty list when no output dir exists."""
    test_client, service = client

    job = service.create(file_ids=[registered_file_id], config=sample_config)

    resp = test_client.get(f"/api/v1/jobs/{job.id}/outputs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["outputs"] == []


def test_get_outputs_with_files(client: tuple[TestClient, object], sample_config: dict, registered_file_id: str):
    """GET /jobs/{id}/outputs returns output files."""
    test_client, service = client
    job = service.create(file_ids=[registered_file_id], config=sample_config)

    # Create output directory with test files
    output_dir = Path(job.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "test.spr.md").write_text("test output")
    (output_dir / "test.frontmatter.md").write_text("test output 2")

    resp = test_client.get(f"/api/v1/jobs/{job.id}/outputs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


def test_get_outputs_response_schema(client: tuple[TestClient, object], sample_config: dict, registered_file_id: str):
    """GET /jobs/{id}/outputs response matches JobOutputsResponse schema."""
    test_client, service = client

    job = service.create(file_ids=[registered_file_id], config=sample_config)

    # Create output directory with test files
    output_dir = Path(job.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "test.spr").write_text("content")

    resp = test_client.get(f"/api/v1/jobs/{job.id}/outputs")
    assert resp.status_code == 200
    data = resp.json()
    # Verify response structure matches JobOutputsResponse
    assert "outputs" in data
    assert "total" in data
    assert isinstance(data["outputs"], list)
    assert isinstance(data["total"], int)
