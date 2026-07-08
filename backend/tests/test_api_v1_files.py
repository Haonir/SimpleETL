"""Tests for REST endpoints in app/api/v1/files.py."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.files import router


@pytest.fixture(autouse=True)
def reset_file_service():
    """Reset FileService singleton between tests."""
    from app.services.file_service import get_file_service, _file_service

    # Reset singleton for test isolation
    import app.services.file_service as mod
    original = mod._file_service
    mod._file_service = None
    yield
    mod._file_service = original


@pytest.fixture
def client():
    """Create a FastAPI TestClient with only the files router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def sample_txt():
    """Create a sample .txt file for upload."""
    return ("test.txt", io.BytesIO(b"Hello world"), "text/plain")


@pytest.fixture
def sample_docx():
    """Create a sample .docx file for upload."""
    return ("doc.docx", io.BytesIO(b"docx content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


# ── POST /files/upload ──────────────────────────────────────────────────────

def test_upload_single_file(client, sample_txt):
    """POST /api/v1/files/upload with single file returns 201."""
    filename, content, content_type = sample_txt
    resp = client.post(
        "/api/v1/files/upload",
        files=[("files", (filename, content, content_type))],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["files"]) == 1
    assert data["files"][0]["filename"] == "test.txt"
    assert data["total"] >= 1


def test_upload_multiple_files(client):
    """POST /api/v1/files/upload with multiple files returns 201."""
    files = [
        ("files", ("file1.txt", io.BytesIO(b"content1"), "text/plain")),
        ("files", ("file2.md", io.BytesIO(b"content2"), "text/markdown")),
    ]
    resp = client.post("/api/v1/files/upload", files=files)
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["files"]) == 2


def test_upload_unsupported_extension(client):
    """POST /api/v1/files/upload with .exe returns 422."""
    resp = client.post(
        "/api/v1/files/upload",
        files=[("files", ("malware.exe", io.BytesIO(b"binary"), "application/octet-stream"))],
    )
    assert resp.status_code == 422


def test_upload_no_files(client):
    """POST /api/v1/files/upload with no files returns 422."""
    resp = client.post("/api/v1/files/upload")
    assert resp.status_code == 422


# ── GET /files ──────────────────────────────────────────────────────────────

def test_list_files_empty(client):
    """GET /api/v1/files returns empty list when no files."""
    resp = client.get("/api/v1/files")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["files"] == []


def test_list_files_after_upload(client, sample_txt):
    """GET /api/v1/files returns uploaded files."""
    filename, content, content_type = sample_txt
    client.post(
        "/api/v1/files/upload",
        files=[("files", (filename, content, content_type))],
    )

    resp = client.get("/api/v1/files")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


# ── DELETE /files/{id} ──────────────────────────────────────────────────────

def test_delete_file(client, sample_txt):
    """DELETE /api/v1/files/{id} removes file and returns 204."""
    # First upload
    filename, content, content_type = sample_txt
    upload_resp = client.post(
        "/api/v1/files/upload",
        files=[("files", (filename, content, content_type))],
    )
    file_id = upload_resp.json()["files"][0]["id"]

    # Then delete
    resp = client.delete(f"/api/v1/files/{file_id}")
    assert resp.status_code == 204

    # Verify it's gone
    list_resp = client.get("/api/v1/files")
    assert list_resp.json()["total"] == 0


def test_delete_file_not_found(client):
    """DELETE /api/v1/files/{id} returns 404 for nonexistent file."""
    resp = client.delete("/api/v1/files/nonexistent-id")
    assert resp.status_code == 404


# ── File on disk tests ──────────────────────────────────────────────────────

def test_file_uploaded_to_disk(client, sample_txt):
    """After upload, file exists on disk."""
    from app.services.file_service import get_file_service

    filename, content, content_type = sample_txt
    upload_resp = client.post(
        "/api/v1/files/upload",
        files=[("files", (filename, content, content_type))],
    )
    file_id = upload_resp.json()["files"][0]["id"]

    service = get_file_service()
    path = service.get_path(file_id)
    assert path is not None
    assert path.exists()
