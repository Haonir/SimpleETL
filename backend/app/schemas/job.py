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
    stopped = "stopped"
    error = "error"


class JobItem(BaseModel):
    """Full job metadata stored in the registry."""

    id: str = Field(..., description="Unique job identifier (UUID4).")
    status: JobStatus = Field(default=JobStatus.pending)
    file_ids: list[str] = Field(..., min_length=1, description="IDs of files to process.")
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
