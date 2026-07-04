"""Unit tests for FileService."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services.file_service import FileService, ALLOWED_EXTENSIONS


@pytest.fixture
def service(tmp_path: Path) -> FileService:
    """Create a FileService with isolated temp directory."""
    return FileService(upload_dir=tmp_path)


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile for testing."""
    import io as _io

    def _create(filename: str, content: bytes = b"test content", content_type: str = "text/plain"):
        file_content = _io.BytesIO(content)
        file = UploadFile(filename=filename, file=file_content)
        return file
    return _create


# ── Upload tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_txt_file(service, mock_upload_file):
    """Upload a .txt file succeeds."""
    file = mock_upload_file("test.txt", b"Hello world")
    item = await service.upload(file)
    
    assert item.filename == "test.txt"
    assert item.size_bytes == 11
    assert item.id  # UUID generated
    assert item.uploaded_at


@pytest.mark.asyncio
async def test_upload_unsupported_extension(service, mock_upload_file):
    """Upload a .exe file raises ValueError."""
    file = mock_upload_file("malware.exe", b"binary")
    with pytest.raises(ValueError, match="not allowed"):
        await service.upload(file)


@pytest.mark.asyncio
async def test_upload_empty_filename(service):
    """Upload with empty filename raises ValueError."""
    import io as _io

    file = UploadFile(filename="", file=_io.BytesIO(b"content"))
    with pytest.raises(ValueError, match="Filename is required"):
        await service.upload(file)


@pytest.mark.asyncio
async def test_upload_duplicate_filenames(service, mock_upload_file):
    """Two files with same name get different IDs."""
    file1 = mock_upload_file("doc.txt", b"content1")
    file2 = mock_upload_file("doc.txt", b"content2")
    
    item1 = await service.upload(file1)
    item2 = await service.upload(file2)
    
    assert item1.id != item2.id


@pytest.mark.asyncio
async def test_upload_empty_file(service, mock_upload_file):
    """Upload empty file raises ValueError."""
    file = mock_upload_file("empty.txt", b"")
    with pytest.raises(ValueError, match="empty"):
        await service.upload(file)


# ── List tests ──────────────────────────────────────────────────────────────

def test_list_files_empty(service):
    """List files when empty returns total=0."""
    result = service.list_files()
    assert result.total == 0
    assert result.files == []


@pytest.mark.asyncio
async def test_list_files_after_upload(service, mock_upload_file):
    """List files returns uploaded file."""
    file = mock_upload_file("test.txt", b"content")
    await service.upload(file)
    
    result = service.list_files()
    assert result.total == 1
    assert result.files[0].filename == "test.txt"


# ── Get tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_file_exists(service, mock_upload_file):
    """Get file by ID returns FileItem."""
    file = mock_upload_file("test.txt", b"content")
    item = await service.upload(file)
    
    found = service.get_file(item.id)
    assert found is not None
    assert found.filename == "test.txt"


def test_get_file_not_found(service):
    """Get file with nonexistent ID returns None."""
    found = service.get_file("nonexistent-id")
    assert found is None


@pytest.mark.asyncio
async def test_get_path_returns_path(service, mock_upload_file):
    """Get path returns valid Path on disk."""
    file = mock_upload_file("test.txt", b"content")
    item = await service.upload(file)
    
    path = service.get_path(item.id)
    assert path is not None
    assert path.exists()


def test_get_path_not_found(service):
    """Get path with nonexistent ID returns None."""
    path = service.get_path("nonexistent-id")
    assert path is None


# ── Delete tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_file(service, mock_upload_file):
    """Delete existing file returns True and removes from disk."""
    file = mock_upload_file("test.txt", b"content")
    item = await service.upload(file)
    
    result = service.delete(item.id)
    assert result is True
    
    # Verify removed
    assert service.get_file(item.id) is None
    assert service.get_path(item.id) is None


def test_delete_file_not_found(service):
    """Delete nonexistent file returns False."""
    result = service.delete("nonexistent-id")
    assert result is False


@pytest.mark.asyncio
async def test_delete_removes_from_disk(service, mock_upload_file):
    """Delete removes file from disk."""
    file = mock_upload_file("test.txt", b"content")
    item = await service.upload(file)
    
    path = service.get_path(item.id)
    assert path.exists()
    
    service.delete(item.id)
    assert not path.exists()


# ── Singleton test ──────────────────────────────────────────────────────────

def test_singleton_returns_same_instance():
    """get_file_service() returns same instance."""
    from app.services.file_service import get_file_service, _file_service
    
    # Reset for test isolation
    import app.services.file_service as mod
    mod._file_service = None
    
    s1 = get_file_service()
    s2 = get_file_service()
    assert s1 is s2
