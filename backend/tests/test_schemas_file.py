"""Validation tests for file-related Pydantic schemas."""

from __future__ import annotations

import pytest

from app.schemas.file import FileItem, FileListResponse, FileUploadResponse


# ── FileItem ────────────────────────────────────────────────────────────────

class TestFileItem:
    def test_valid(self):
        item = FileItem(
            id="abc-123",
            filename="report.txt",
            size_bytes=4096,
            content_type="text/plain",
            uploaded_at="2025-01-01T00:00:00Z",
        )
        assert item.id == "abc-123"
        assert item.filename == "report.txt"
        assert item.size_bytes == 4096
        assert item.content_type == "text/plain"

    def test_empty_id_raises(self):
        with pytest.raises(Exception):
            FileItem(
                id="",
                filename="report.txt",
                size_bytes=100,
                content_type="text/plain",
                uploaded_at="2025-01-01T00:00:00Z",
            )

    def test_negative_size_raises(self):
        with pytest.raises(Exception):
            FileItem(
                id="abc-456",
                filename="report.txt",
                size_bytes=-1,
                content_type="text/plain",
                uploaded_at="2025-01-01T00:00:00Z",
            )

    def test_empty_filename_raises(self):
        with pytest.raises(Exception):
            FileItem(
                id="abc-789",
                filename="",
                size_bytes=100,
                content_type="text/plain",
                uploaded_at="2025-01-01T00:00:00Z",
            )

    def test_zero_size_ok(self):
        item = FileItem(
            id="abc-000",
            filename=".empty",
            size_bytes=0,
            content_type="application/octet-stream",
            uploaded_at="2025-01-01T00:00:00Z",
        )
        assert item.size_bytes == 0

    def test_missing_id_raises(self):
        with pytest.raises(Exception):
            FileItem(
                filename="report.txt",
                size_bytes=100,
                content_type="text/plain",
                uploaded_at="2025-01-01T00:00:00Z",
            )

    def test_missing_filename_raises(self):
        with pytest.raises(Exception):
            FileItem(
                id="abc-999",
                size_bytes=100,
                content_type="text/plain",
                uploaded_at="2025-01-01T00:00:00Z",
            )

    def test_missing_size_raises(self):
        with pytest.raises(Exception):
            FileItem(
                id="abc-888",
                filename="report.txt",
                content_type="text/plain",
                uploaded_at="2025-01-01T00:00:00Z",
            )

    def test_missing_content_type_raises(self):
        with pytest.raises(Exception):
            FileItem(
                id="abc-777",
                filename="report.txt",
                size_bytes=100,
                uploaded_at="2025-01-01T00:00:00Z",
            )

    def test_missing_uploaded_at_raises(self):
        with pytest.raises(Exception):
            FileItem(
                id="abc-666",
                filename="report.txt",
                size_bytes=100,
                content_type="text/plain",
            )


# ── FileListResponse ────────────────────────────────────────────────────────

class TestFileListResponse:
    def test_empty_list(self):
        resp = FileListResponse(files=[], total=0)
        assert len(resp.files) == 0
        assert resp.total == 0

    def test_with_files(self):
        files = [
            FileItem(
                id="f1", filename="a.txt", size_bytes=100, content_type="text/plain", uploaded_at="2025-01-01T00:00:00Z"
            ),
            FileItem(
                id="f2", filename="b.md", size_bytes=200, content_type="text/markdown", uploaded_at="2025-01-02T00:00:00Z"
            ),
        ]
        resp = FileListResponse(files=files, total=2)
        assert len(resp.files) == 2
        assert resp.total == 2


# ── FileUploadResponse ──────────────────────────────────────────────────────

class TestFileUploadResponse:
    def test_valid(self):
        files = [
            FileItem(
                id="u1", filename="doc.pdf", size_bytes=5000, content_type="application/pdf", uploaded_at="2025-06-01T12:00:00Z"
            ),
        ]
        resp = FileUploadResponse(files=files, total=1)
        assert len(resp.files) == 1
        assert resp.total == 1
        assert resp.message == "Files uploaded successfully."

    def test_empty_files_list(self):
        resp = FileUploadResponse(files=[], total=0)
        assert len(resp.files) == 0
        assert resp.total == 0
