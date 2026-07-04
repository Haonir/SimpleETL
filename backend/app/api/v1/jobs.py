"""REST endpoints for job management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.job import (
    JobCreateRequest,
    JobItem,
    JobListResponse,
    JobResponse,
    JobStatus,
)
from app.services.job_service import get_job_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(request: JobCreateRequest) -> JobResponse:
    """Create a new ETL job.

    Validates that all file_ids reference existing uploaded files.
    Job starts in 'pending' status; ETL runner transitions to 'running'.
    """
    service = get_job_service()
    try:
        job = service.create(
            file_ids=request.file_ids,
            config=request.config,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return JobResponse(job=job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs() -> JobListResponse:
    """Get list of all jobs."""
    service = get_job_service()
    jobs = service.list_all()
    return JobListResponse(jobs=jobs, total=len(jobs))


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Get job by ID."""
    service = get_job_service()
    job = service.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return JobResponse(job=job)


@router.delete("/jobs/{job_id}", response_model=JobResponse)
async def stop_job(job_id: str) -> JobResponse:
    """Stop a running job or delete a completed one.

    - Running/pending: requests graceful stop, returns current state.
    - Completed/stopped/error: removes from registry, returns final state.
    """
    service = get_job_service()
    job = service.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.status in (JobStatus.running, JobStatus.pending):
        service.request_stop(job_id)
        return JobResponse(job=job)

    # Terminal state: remove from registry
    service.delete(job_id)
    return JobResponse(job=job)
