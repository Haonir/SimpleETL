"""Pydantic v2 schemas for job data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job lifecycle states."""

    pending = "pending"
    running = "running"
    completed = "completed"
    partial = "partial"
    stopped = "stopped"
    error = "error"


class JobItem(BaseModel):
    """Full job metadata stored in the registry."""

    id: str = Field(..., description="Unique job identifier (UUID4).")
    status: JobStatus = Field(default=JobStatus.pending)
    file_ids: list[str] = Field(..., min_length=1, description="IDs of files to process.")
    file_names: list[str] = Field(default_factory=list, description="Original filenames for display.")
    config: dict = Field(..., description="ETL config snapshot (llm + processing + prompt_text).")
    created_at: datetime = Field(..., description="Job creation timestamp (UTC).")
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    output_dir: Optional[str] = Field(default=None, description="Path to output directory.")
    error_message: Optional[str] = Field(default=None)
    file_count: int = Field(..., ge=1, description="Number of files in the job.")


class JobCreateRequest(BaseModel):
    """Request body for POST /jobs."""

    file_ids: list[str] = Field(..., min_length=1)
    config: dict = Field(..., description="Full ETL config (llm + processing + prompt_text).")


class JobResponse(BaseModel):
    """Single job response wrapper."""

    job: JobItem


class JobListResponse(BaseModel):
    """List of jobs with total count."""

    jobs: list[JobItem] = Field(default_factory=list)
    total: int = Field(..., ge=0)


class JobFileItem(BaseModel):
    """Represents a single output file from a completed job."""

    filename: str = Field(..., description="Output filename.")
    path: str = Field(..., description="Relative path from job output dir.")
    size_bytes: int = Field(..., ge=0, description="File size in bytes.")


class JobFilesResponse(BaseModel):
    """List of output files for a job."""

    job_id: str = Field(..., description="Job identifier.")
    files: list[JobFileItem] = Field(default_factory=list)
    total: int = Field(..., ge=0)


# -- Log schemas -------------------------------------------------------------


class JobLogEntry(BaseModel):
    """A single log entry from a job's logs.json."""

    timestamp: str = Field(..., min_length=1, description="ISO 8601 UTC timestamp.")
    level: str = Field(..., description="Log level (INFO, WARNING, ERROR).")
    message: str = Field(..., description="Human-readable log message.")


class JobLogsResponse(BaseModel):
    """List of log entries for a job."""

    logs: list[JobLogEntry] = Field(default_factory=list)
    total: int = Field(..., ge=0)


# -- Output schemas ----------------------------------------------------------


class JobOutputItem(BaseModel):
    """Represents a single output file from a completed job."""

    filename: str = Field(..., description="Output filename.")
    file_path: str = Field(..., description="Relative path from job output dir.")
    size_bytes: int = Field(..., ge=0, description="File size in bytes.")
    format: str = Field(..., description="Output format (e.g. spr, markdown).")


class JobOutputsResponse(BaseModel):
    """List of output files for a job."""

    outputs: list[JobOutputItem] = Field(default_factory=list)
    total: int = Field(..., ge=0)
