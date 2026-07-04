"""FileService — upload, list, delete files. In-memory registry + temp storage."""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Optional

from fastapi import UploadFile

from app.schemas.file import FileItem, FileListResponse, FileUploadResponse

logger = logging.getLogger(__name__)

# Allowed file extensions (matching core ETL pipeline)
ALLOWED_EXTENSIONS: set[str] = {".txt", ".md", ".docx", ".doc", ".pdf"}

# Default max file size: 100 MB
DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024


class FileService:
    """Service for managing uploaded files.
    
    Stores files in a temporary directory and maintains an in-memory registry.
    Singleton pattern: use get_file_service() to get the global instance.
    """

    def __init__(self, upload_dir: Optional[str | Path] = None):
        """Initialize FileService with an upload directory.
        
        Args:
            upload_dir: Directory to store uploaded files. 
                       If None, uses system temp dir + 'SimpleETL/uploads'.
        """
        if upload_dir is not None:
            self._upload_dir = Path(upload_dir)
        else:
            self._upload_dir = Path(tempfile.gettempdir()) / "SimpleETL" / "uploads"
        
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory registry: file_id -> FileItem
        self._files: dict[str, FileItem] = {}
        
        # In-memory file data: file_id -> bytes (for simplicity in MVP)
        # In production, files would be on disk and we'd track paths only
        self._file_data: dict[str, bytes] = {}
        
        logger.info("FileService initialized with upload_dir: %s", self._upload_dir)

    @property
    def upload_dir(self) -> Path:
        """Return the upload directory path."""
        return self._upload_dir

    def _validate_extension(self, filename: str) -> None:
        """Validate file extension. Raises ValueError if not allowed."""
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File extension '{ext}' is not allowed. "
                f"Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

    async def upload(self, file: UploadFile) -> FileItem:
        """Upload a single file and store it.
        
        Args:
            file: FastAPI UploadFile object.
            
        Returns:
            FileItem with metadata.
            
        Raises:
            ValueError: If file extension is not allowed or file is empty.
        """
        # Validate filename
        if not file.filename:
            raise ValueError("Filename is required.")
        
        self._validate_extension(file.filename)
        
        # Read file content
        content = await file.read()
        if not content:
            raise ValueError("File is empty.")
        
        # Check file size
        if len(content) > DEFAULT_MAX_FILE_SIZE:
            raise ValueError(
                f"File size ({len(content)} bytes) exceeds maximum "
                f"({DEFAULT_MAX_FILE_SIZE} bytes)."
            )
        
        # Generate unique ID
        file_id = str(uuid.uuid4())
        
        # Determine storage path
        ext = Path(file.filename).suffix
        storage_name = f"{file_id}{ext}"
        storage_path = self._upload_dir / storage_name
        
        # Write to disk
        storage_path.write_bytes(content)
        
        # Create FileItem
        item = FileItem(
            id=file_id,
            filename=file.filename,
            size_bytes=len(content),
            content_type=file.content_type or "application/octet-stream",
            uploaded_at=datetime.now(timezone.utc),
        )
        
        # Register in memory
        self._files[file_id] = item
        self._file_data[file_id] = content
        
        logger.info("Uploaded file: %s (id=%s, size=%d)", file.filename, file_id, len(content))
        return item

    def list_files(self) -> FileListResponse:
        """Return list of all uploaded files."""
        files = list(self._files.values())
        return FileListResponse(files=files, total=len(files))

    def get_file(self, file_id: str) -> Optional[FileItem]:
        """Get file metadata by ID. Returns None if not found."""
        return self._files.get(file_id)

    def get_path(self, file_id: str) -> Optional[Path]:
        """Get the path to the file on disk. Returns None if not found."""
        item = self._files.get(file_id)
        if item is None:
            return None
        
        ext = Path(item.filename).suffix
        return self._upload_dir / f"{file_id}{ext}"

    def get_data(self, file_id: str) -> Optional[bytes]:
        """Get file content as bytes. Returns None if not found."""
        return self._file_data.get(file_id)

    def delete(self, file_id: str) -> bool:
        """Delete a file by ID. Returns True if deleted, False if not found."""
        item = self._files.pop(file_id, None)
        if item is None:
            return False
        
        # Remove from disk
        ext = Path(item.filename).suffix
        path = self._upload_dir / f"{file_id}{ext}"
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Failed to delete file from disk: %s", exc)
        
        # Remove from memory
        self._file_data.pop(file_id, None)
        
        logger.info("Deleted file: %s (id=%s)", item.filename, file_id)
        return True

    def cleanup(self, max_age_hours: int = 24) -> int:
        """Remove files older than max_age_hours. Returns count of removed files.
        
        Note: This is a simple MVP implementation. For production, consider
        using a background task with asyncio or APScheduler.
        """
        now = datetime.now(timezone.utc)
        to_remove: list[str] = []
        
        for file_id, item in self._files.items():
            age_hours = (now - item.uploaded_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                to_remove.append(file_id)
        
        count = 0
        for file_id in to_remove:
            if self.delete(file_id):
                count += 1
        
        if count > 0:
            logger.info("Cleaned up %d old files", count)
        return count


# ── Singleton ───────────────────────────────────────────────────────────────

_file_service: Optional[FileService] = None


def get_file_service() -> FileService:
    """Return the global singleton FileService instance."""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service
