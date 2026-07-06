"""JobService — create, list, get, stop, delete jobs. SQLite-backed registry."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.db import ensure_tables, get_cursor
from app.schemas.job import JobItem, JobStatus
from app.services.file_service import get_file_service

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing ETL jobs.

    Singleton pattern: use get_job_service() to get the global instance.
    Jobs are persisted in SQLite; stop flags remain in RAM for performance.
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

        # Stop flags: job_id -> True if stop requested (kept in RAM for performance)
        self._stop_flags: dict[str, bool] = {}

        logger.info("JobService initialized with output_base: %s", self._output_base)

    def _ensure_db(self):
        """Ensure the SQLite database tables exist.

        Uses ensure_tables() without a path argument to use the already-initialized
        DB (set by init_db() at startup). This avoids switching to a different DB file.
        """
        from app.db import ensure_tables
        ensure_tables()

    def _get_log_path(self, job_id: str) -> Path:
        """Return the log file path for a given job."""
        return self._output_base / job_id / "logs.json"

    def create(self, file_ids: list[str], config: dict) -> JobItem:
        """Create a new job. Validates all file_ids exist in FileService.

        Raises:
            ValueError: If any file_id not found or file_ids is empty.
        """
        self._ensure_db()
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

        # Resolve file names for display
        file_names = []
        for fid in file_ids:
            f = file_service.get_file(fid)
            file_names.append(f.filename if f else fid)

        # Persist job to SQLite
        with get_cursor() as cur:
            cur.execute(
                """INSERT INTO jobs (id, status, file_ids, file_names, config, created_at, file_count, output_dir)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, JobStatus.pending.value, json.dumps(file_ids),
                 json.dumps(file_names), json.dumps(config), now.isoformat(), len(file_ids), output_dir),
            )

        job = JobItem(
            id=job_id,
            status=JobStatus.pending,
            file_ids=file_ids,
            file_names=file_names,
            config=config,
            created_at=now,
            file_count=len(file_ids),
            output_dir=output_dir,
        )

        self._stop_flags[job_id] = False
        logger.info("Created job %s with %d files", job_id, len(file_ids))
        return job

    def get(self, job_id: str) -> Optional[JobItem]:
        """Get job by ID. Returns None if not found."""
        self._ensure_db()
        try:
            with get_cursor() as cur:
                cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
                row = cur.fetchone()
        except sqlite3.Error:
            return None

        if row is None:
            return None

        data = dict(row)
        # Parse JSON fields
        file_ids = json.loads(data["file_ids"])
        config = json.loads(data["config"])
        output_dir = data.get("output_dir") or None
        log_path_str = data.get("log_path") or None
        if log_path_str:
            log_path = Path(log_path_str)
            if log_path.exists():
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        entries = [json.loads(line) for line in f.read().splitlines() if line.strip()]
                    data["log_entries"] = entries
                except (json.JSONDecodeError, OSError):
                    data["log_entries"] = []

        return JobItem(
            id=data["id"],
            status=JobStatus(data["status"]),
            file_ids=file_ids,
            file_names=json.loads(data.get("file_names", "[]")),
            config=config,
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=(datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None),
            output_dir=output_dir,
            error_message=data.get("error_message"),
            file_count=int(data["file_count"]),
        )

    def list_all(self) -> list[JobItem]:
        """Return all jobs ordered by created_at DESC."""
        self._ensure_db()
        try:
            with get_cursor() as cur:
                cur.execute("SELECT * FROM jobs ORDER BY created_at DESC")
                rows = cur.fetchall()
        except sqlite3.Error:
            return []

        results = []
        for row in rows:
            data = dict(row)
            file_ids = json.loads(data["file_ids"])
            config = json.loads(data["config"])
            output_dir = data.get("output_dir") or None
            log_path_str = data.get("log_path") or None
            if log_path_str:
                log_path = Path(log_path_str)
                if log_path.exists():
                    try:
                        with open(log_path, "r", encoding="utf-8") as f:
                            entries = [json.loads(line) for line in f.read().splitlines() if line.strip()]
                        data["log_entries"] = entries
                    except (json.JSONDecodeError, OSError):
                        data["log_entries"] = []

            results.append(JobItem(
                id=data["id"],
                status=JobStatus(data["status"]),
                file_ids=file_ids,
                file_names=json.loads(data.get("file_names", "[]")),
                config=config,
                created_at=datetime.fromisoformat(data["created_at"]),
                started_at=(datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None),
                completed_at=(datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None),
                output_dir=output_dir,
                error_message=data.get("error_message"),
                file_count=int(data["file_count"]),
            ))

        return results

    def update_status(self, job_id: str, status: JobStatus, **kwargs) -> JobItem:
        """Update job status and optional fields.

        Raises:
            KeyError: If job_id not found.
        """
        self._ensure_db()
        now = datetime.now(timezone.utc).isoformat()
        try:
            with get_cursor() as cur:
                if status == JobStatus.running:
                    cur.execute(
                        """UPDATE jobs SET status = ?, started_at = ?,
                           completed_at = CASE WHEN completed_at IS NOT NULL THEN completed_at ELSE ? END,
                           error_message = ? WHERE id = ?""",
                        (status.value, now, None, kwargs.get("error_message"), job_id),
                    )
                else:
                    cur.execute(
                        """UPDATE jobs SET status = ?, started_at = COALESCE(started_at, ?),
                           completed_at = CASE WHEN completed_at IS NOT NULL THEN completed_at ELSE ? END,
                           error_message = ? WHERE id = ?""",
                        (status.value, None, now if status in (JobStatus.completed, JobStatus.error, JobStatus.stopped) else None,
                         kwargs.get("error_message"), job_id),
                    )
        except sqlite3.Error as e:
            raise KeyError(f"Failed to update job '{job_id}': {e}")

        # Reload the full record
        job = self.get(job_id)
        if job is None:
            raise KeyError(f"Job '{job_id}' not found.")

        logger.info("Job %s status -> %s", job_id, status.value)
        return job

    def request_stop(self, job_id: str) -> None:
        """Request graceful stop for a running job.

        Raises:
            KeyError: If job_id not found.
        """
        if self.get(job_id) is None:
            raise KeyError(f"Job '{job_id}' not found.")
        self._stop_flags[job_id] = True
        logger.info("Stop requested for job %s", job_id)

    def is_stopped(self, job_id: str) -> bool:
        """Check if stop was requested. Used by ETL runner stop_check_callback."""
        return self._stop_flags.get(job_id, False)

    def delete(self, job_id: str) -> bool:
        """Delete a job from registry. Returns True if deleted."""
        self._ensure_db()
        job = self.get(job_id)
        if job is None:
            return False
        with get_cursor() as cur:
            cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        # Also clean up stop flag in RAM
        self._stop_flags.pop(job_id, None)
        logger.info("Deleted job %s", job_id)
        return True

    def get_logs(self, job_id: str) -> list[dict]:
        """Read log entries from the job_logs table."""
        try:
            with get_cursor() as cur:
                cur.execute(
                    "SELECT timestamp, level, message FROM job_logs WHERE job_id = ? ORDER BY id",
                    (job_id,)
                )
                rows = cur.fetchall()
            return [{"timestamp": r["timestamp"], "level": r["level"].lower(), "message": r["message"]} for r in rows]
        except Exception:
            return []

    def get_outputs(self, job_id: str) -> list[dict]:
        """List output files from the job_outputs table."""
        try:
            with get_cursor() as cur:
                cur.execute(
                    "SELECT filename, file_path, size_bytes, format FROM job_outputs WHERE job_id = ? ORDER BY id",
                    (job_id,)
                )
                rows = cur.fetchall()
            return [{"filename": r["filename"], "file_path": r["file_path"], "size_bytes": r["size_bytes"], "format": r["format"]} for r in rows]
        except Exception:
            return []

    def save_outputs(self, job_id: str, outputs: list[dict]) -> None:
        """Save output file records to the job_outputs table.

        Args:
            job_id: Job identifier.
            outputs: List of dicts with keys: filename, file_path, size_bytes, format
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        try:
            with get_cursor() as cur:
                for output in outputs:
                    cur.execute(
                        """INSERT INTO job_outputs (job_id, filename, file_path, size_bytes, format, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (job_id, output["filename"], output["file_path"],
                         output.get("size_bytes", 0), output.get("format", ""), now)
                    )
        except Exception as e:
            logger.warning("Failed to save outputs for job %s: %s", job_id, e)

    def delete_job_files(self, job_id: str) -> None:
        """Delete job directory from disk + DB records."""
        self._ensure_db()
        job = self.get(job_id)
        if job and job.output_dir:
            shutil.rmtree(job.output_dir, ignore_errors=True)
        with get_cursor() as cur:
            cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


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
