"""Pydantic v2 schemas for file upload/listing data models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FileItem(BaseModel):
    """Metadata for a single uploaded file."""

    id: str = Field(..., min_length=1, description="Unique file identifier (UUID4).")
    filename: str = Field(..., min_length=1, description="Original filename with extension.")
    size_bytes: int = Field(..., ge=0, description="File size in bytes.")
    content_type: str = Field(..., description="MIME type of the file.")
    uploaded_at: datetime = Field(..., description="Upload timestamp (UTC).")


class FileListResponse(BaseModel):
    """List of uploaded files with total count."""

    files: list[FileItem] = Field(default_factory=list, description="List of file metadata.")
    total: int = Field(..., description="Total number of uploaded files.")


class FileUploadResponse(BaseModel):
    """Response after uploading one or more files."""

    files: list[FileItem] = Field(..., description="Metadata of uploaded files.")
    total: int = Field(..., description="Total number of uploaded files.")
    message: str = Field(default="Files uploaded successfully.", description="Human-readable confirmation.")
