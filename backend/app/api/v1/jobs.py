"""REST endpoints for job management."""

from __future__ import annotations

import logging
import os
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse

from app.schemas.job import (
    JobCreateRequest,
    JobFileItem,
    JobFilesResponse,
    JobItem,
    JobListResponse,
    JobLogEntry,
    JobLogsResponse,
    JobOutputItem,
    JobOutputsResponse,
    JobResponse,
    JobStatus,
)
from app.services.file_service import get_file_service
from app.services.job_service import get_job_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Create a new ETL job and start processing in background.

    Validates that all file_ids reference existing uploaded files.
    Job starts in 'pending' status, then transitions to 'running' via ETL runner.
    """
    from app.etl.runner import run_etl_job
    from app.services.websocket_manager import get_ws_manager

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

    # Resolve file paths from file_ids
    file_service = get_file_service()
    file_paths = []
    for fid in request.file_ids:
        path = file_service.get_path(fid)
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{fid}' not found on disk.",
            )
        file_paths.append(str(path))

    # Add output_dir to config
    config = request.config.copy()
    config["output_dir"] = job.output_dir

    # Launch ETL runner in background
    ws_manager = get_ws_manager()
    background_tasks.add_task(
        run_etl_job,
        job_id=job.id,
        file_paths=file_paths,
        config=config,
        job_service=service,
        ws_manager=ws_manager,
    )

    logger.info("Job %s created and ETL runner launched", job.id)
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
async def stop_job(job_id: str, delete_files: bool = False) -> JobResponse:
    """Stop a running job or delete a completed one.

    - Running/pending: requests graceful stop, returns current state.
    - Completed/stopped/error: removes from registry, returns final state.
    - If delete_files=True: also deletes uploaded and output files.
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
    if delete_files:
        # Delete uploaded files
        file_service = get_file_service()
        for file_id in job.file_ids:
            file_service.delete(file_id)
        # Delete output files and job record
        service.delete_job_files(job_id)
    else:
        service.delete(job_id)
    return JobResponse(job=job)


@router.get("/jobs/{job_id}/files", response_model=JobFilesResponse)
async def list_job_files(job_id: str) -> JobFilesResponse:
    """List output files for a completed job."""
    service = get_job_service()
    job = service.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.output_dir is None or not os.path.exists(job.output_dir):
        return JobFilesResponse(job_id=job_id, files=[], total=0)

    files: list[JobFileItem] = []
    for root, _, filenames in os.walk(job.output_dir):
        for fname in filenames:
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, job.output_dir)
            files.append(JobFileItem(
                filename=fname,
                path=rel_path,
                size_bytes=os.path.getsize(fpath),
            ))

    return JobFilesResponse(job_id=job_id, files=files, total=len(files))


@router.get("/jobs/{job_id}/files/{filename:path}")
async def download_job_file(job_id: str, filename: str):
    """Download a single output file from a job."""
    service = get_job_service()
    job = service.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.output_dir is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job has no output directory.",
        )

    # Search for the file in output directory (files may be in subdirectories)
    target_name = os.path.basename(filename)
    file_path = None
    for root, _, filenames in os.walk(job.output_dir):
        if target_name in filenames:
            file_path = os.path.join(root, target_name)
            break

    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found.",
        )

    return FileResponse(
        path=file_path,
        filename=target_name,
        media_type="application/octet-stream",
    )


@router.get("/jobs/{job_id}/download")
async def download_job_zip(job_id: str):
    """Download all output files for a job as a ZIP archive."""
    service = get_job_service()
    job = service.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.output_dir is None or not os.path.exists(job.output_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job has no output files.",
        )

    # Create ZIP in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, filenames in os.walk(job.output_dir):
            for fname in filenames:
                fpath = os.path.join(root, fname)
                arcname = os.path.relpath(fpath, job.output_dir)
                zf.write(fpath, arcname)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="etl_job_{job_id[:8]}.zip"'
        },
    )


@router.get("/jobs/{job_id}/logs", response_model=JobLogsResponse)
async def get_job_logs(job_id: str) -> JobLogsResponse:
    """Get log entries for a job."""
    service = get_job_service()
    job = service.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    logs = service.get_logs(job_id)
    return JobLogsResponse(logs=logs, total=len(logs))


@router.get("/jobs/{job_id}/outputs", response_model=JobOutputsResponse)
async def get_job_outputs(job_id: str) -> JobOutputsResponse:
    """List output files for a completed job."""
    service = get_job_service()
    job = service.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    outputs = service.get_outputs(job_id)
    return JobOutputsResponse(outputs=outputs, total=len(outputs))


@router.post("/jobs/cleanup")
async def cleanup_jobs(max_age_hours: int = 24) -> dict:
    """Clean up old completed/errored/stopped jobs and their files."""
    service = get_job_service()
    removed = service.cleanup(max_age_hours=max_age_hours)
    return {"removed": removed}
