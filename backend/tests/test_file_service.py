"""Unit tests for FileService."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.db import init_db
from app.schemas.file import FileItem
from app.services.file_service import FileService, ALLOWED_EXTENSIONS


@pytest.fixture
def service(tmp_path: Path) -> FileService:
    """Create a FileService with isolated temp directory."""
    return FileService(upload_dir=tmp_path)


@pytest.fixture(autouse=True)
def _reset_file_service(tmp_path):
    """Reset singleton and DB for each test."""
    import app.services.file_service as fs_module
    fs_module._file_service = None  # reset singleton
    from app.db import init_db
    init_db(str(tmp_path / "test.db"))  # fresh DB per test
    yield
    fs_module._file_service = None


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


# ── SQLite persistence tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_persists_to_sqlite(service, mock_upload_file):
    """Uploaded file can be retrieved via list_files after upload."""
    file = mock_upload_file("test.txt", b"Hello world")
    item = await service.upload(file)
    
    # Verify persisted in SQLite
    result = service.list_files()
    assert result.total == 1
    assert result.files[0].id == item.id

@pytest.mark.asyncio
async def test_list_files_order_by_uploaded_at(service, mock_upload_file):
    """list_files returns files ordered by upload time."""
    file1 = mock_upload_file("first.txt", b"content1")
    await service.upload(file1)
    
    # Small delay to ensure different timestamps
    import asyncio
    await asyncio.sleep(0.01)
    
    file2 = mock_upload_file("second.txt", b"content2")
    await service.upload(file2)
    
    result = service.list_files()
    assert result.total == 2
    # second should come after first
    assert result.files[0].filename == "first.txt"
    assert result.files[1].filename == "second.txt"

@pytest.mark.asyncio
async def test_get_file_from_sqlite(service, mock_upload_file):
    """get_file retrieves file from SQLite."""
    file = mock_upload_file("test.txt", b"data")
    item = await service.upload(file)
    
    found = service.get_file(item.id)
    assert found is not None
    assert found.filename == "test.txt"
    assert found.size_bytes == 4

@pytest.mark.asyncio
async def test_delete_removes_from_sqlite(service, mock_upload_file):
    """Delete removes file from SQLite."""
    file = mock_upload_file("test.txt", b"data")
    item = await service.upload(file)
    
    service.delete(item.id)
    
    # Verify removed from SQLite
    assert service.get_file(item.id) is None

@pytest.mark.asyncio
async def test_delete_nonexistent_returns_false(service):
    """Delete nonexistent file returns False."""
    result = service.delete("nonexistent-id")
    assert result is False

async def test_cleanup_removes_old_files_from_sqlite(service, mock_upload_file):
    """cleanup removes files older than max_age_hours from SQLite."""
    # Upload a file with old timestamp
    import io as _io

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(hours=48)
    
    item = FileItem(
        id="old-file-id",
        filename="old.txt",
        size_bytes=10,
        content_type="text/plain",
        uploaded_at=old_time,
    )
    
    # Insert directly into SQLite with old timestamp
    from app.db import get_cursor
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO files (id, filename, size_bytes, content_type, uploaded_at) VALUES (?, ?, ?, ?, ?)",
            ("old-file-id", "old.txt", 10, "text/plain", old_time.isoformat()),
        )
    
    # Upload a fresh file
    file = mock_upload_file("fresh.txt", b"content")
    await service.upload(file)
    
    # Cleanup should remove the old file
    count = service.cleanup(max_age_hours=24)
    assert count == 1
    
    result = service.list_files()
    assert result.total == 1
    assert result.files[0].filename == "fresh.txt"

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
