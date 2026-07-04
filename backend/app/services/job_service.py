"""JobService — create, list, get, stop, delete jobs. In-memory registry."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.schemas.job import JobItem, JobStatus
from app.services.file_service import get_file_service

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing ETL jobs.

    Singleton pattern: use get_job_service() to get the global instance.
    """

    def __init__(self, output_base_dir: Optional[str | Path] = None):
        """Initialize JobService.

        Args:
            output_base_dir: Base directory for job outputs.
                           If None, uses system temp dir + 'SimpleETL/jobs'.
        """
        import tempfile

        if output_base_dir is not None:
            self._output_base = Path(output_base_dir)
        else:
            self._output_base = Path(tempfile.gettempdir()) / "SimpleETL" / "jobs"
        self._output_base.mkdir(parents=True, exist_ok=True)

        # In-memory registry
        self._jobs: dict[str, JobItem] = {}
        # Stop flags: job_id -> True if stop requested
        self._stop_flags: dict[str, bool] = {}

        logger.info("JobService initialized with output_base: %s", self._output_base)

    def create(self, file_ids: list[str], config: dict) -> JobItem:
        """Create a new job. Validates all file_ids exist in FileService.

        Raises:
            ValueError: If any file_id not found or file_ids is empty.
        """
        if not file_ids:
            raise ValueError("At least one file_id is required.")

        # Validate all files exist
        file_service = get_file_service()
        for fid in file_ids:
            if file_service.get_file(fid) is None:
                raise ValueError(f"File with id '{fid}' not found.")

        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        output_dir = str(self._output_base / job_id / "output")

        job = JobItem(
            id=job_id,
            status=JobStatus.pending,
            file_ids=file_ids,
            config=config,
            created_at=now,
            file_count=len(file_ids),
            output_dir=output_dir,
        )

        self._jobs[job_id] = job
        self._stop_flags[job_id] = False
        logger.info("Created job %s with %d files", job_id, len(file_ids))
        return job

    def get(self, job_id: str) -> Optional[JobItem]:
        """Get job by ID. Returns None if not found."""
        return self._jobs.get(job_id)

    def list_all(self) -> list[JobItem]:
        """Return all jobs."""
        return list(self._jobs.values())

    def update_status(self, job_id: str, status: JobStatus, **kwargs) -> JobItem:
        """Update job status and optional fields.

        Raises:
            KeyError: If job_id not found.
        """
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"Job '{job_id}' not found.")

        job.status = status

        if status == JobStatus.running and job.started_at is None:
            job.started_at = datetime.now(timezone.utc)

        if status in (JobStatus.completed, JobStatus.error, JobStatus.stopped):
            job.completed_at = datetime.now(timezone.utc)

        # Update optional fields
        if "error_message" in kwargs:
            job.error_message = kwargs["error_message"]
        if "output_dir" in kwargs:
            job.output_dir = kwargs["output_dir"]

        logger.info("Job %s status -> %s", job_id, status.value)
        return job

    def request_stop(self, job_id: str) -> None:
        """Request graceful stop for a running job.

        Raises:
            KeyError: If job_id not found.
        """
        if job_id not in self._jobs:
            raise KeyError(f"Job '{job_id}' not found.")
        self._stop_flags[job_id] = True
        logger.info("Stop requested for job %s", job_id)

    def is_stopped(self, job_id: str) -> bool:
        """Check if stop was requested. Used by ETL runner stop_check_callback."""
        return self._stop_flags.get(job_id, False)

    def delete(self, job_id: str) -> bool:
        """Delete a job from registry. Returns True if deleted."""
        job = self._jobs.pop(job_id, None)
        if job is None:
            return False
        self._stop_flags.pop(job_id, None)
        logger.info("Deleted job %s", job_id)
        return True

    @property
    def output_base_dir(self) -> Path:
        """Return the base output directory path."""
        return self._output_base


# -- Singleton ---------------------------------------------------------------

_job_service: Optional[JobService] = None


def get_job_service() -> JobService:
    """Return the global singleton JobService instance."""
    global _job_service
    if _job_service is None:
        _job_service = JobService()
    return _job_service
