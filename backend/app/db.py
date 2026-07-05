"""SQLite database initialization and connection management."""

from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

_local = threading.local()
_db_path: Path | None = None


def init_db(db_path: str = "simpleetl.db") -> None:
    """Initialize the SQLite database.

    Creates tables if they don't exist and recovers interrupted jobs.

    Args:
        db_path: Path to the SQLite database file. Defaults to 'simpleetl.db'.
    """
    global _db_path
    _db_path = Path(db_path)
    # Reset existing connection so _get_connection() creates a new one with the new path
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
    conn = _get_connection()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_tables(conn)
    _recover_interrupted_jobs(conn)


def _get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection.

    Returns:
        sqlite3.Connection with row_factory set to sqlite3.Row.
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(_db_path), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


@contextmanager
def get_cursor():
    """Context manager for database operations with automatic commit/rollback.

    Yields:
        sqlite3.Cursor

    Raises:
        Any exception from the cursor operation, with rollback on failure.
    """
    conn = _get_connection()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _create_tables(conn) -> None:
    """Create database tables if they don't exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS files (
            id            TEXT PRIMARY KEY,
            filename      TEXT NOT NULL,
            size_bytes    INTEGER NOT NULL,
            content_type  TEXT NOT NULL DEFAULT '',
            uploaded_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id              TEXT PRIMARY KEY,
            status          TEXT NOT NULL DEFAULT 'pending',
            file_ids        TEXT NOT NULL DEFAULT '[]',
            config          TEXT NOT NULL DEFAULT '{}',
            output_dir      TEXT,
            log_path        TEXT,
            file_count      INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL,
            started_at      TEXT,
            completed_at    TEXT,
            error_message   TEXT
        );

        CREATE TABLE IF NOT EXISTS job_outputs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id      TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            filename    TEXT NOT NULL,
            file_path   TEXT NOT NULL,
            size_bytes  INTEGER NOT NULL DEFAULT 0,
            format      TEXT NOT NULL DEFAULT '',
            created_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_job_outputs_job_id ON job_outputs(job_id);
        """
    )


def ensure_tables(db_path: str) -> None:
    """Ensure tables exist without running recovery.

    Used by JobService._ensure_db() which must not run recovery,
    because recovery marks all pending/running jobs as 'error' —
    and _ensure_db() is called on every method invocation, not just startup.
    """
    global _db_path
    if _db_path != Path(db_path):
        _db_path = Path(db_path)
        # Reset existing connection so _get_connection() creates a new one with the new path
        if hasattr(_local, "conn") and _local.conn is not None:
            _local.conn.close()
            _local.conn = None
    conn = _get_connection()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_tables(conn)


def _recover_interrupted_jobs(conn) -> None:
    """Mark any 'running' or 'pending' jobs as 'error' on startup.

    This recovers from server restarts that interrupted in-progress jobs.
    Only call this once at application startup (via init_db), never inside
    per-method _ensure_db() calls.
    """
    cur = conn.cursor()
    cur.execute(
        "UPDATE jobs SET status='error', error_message='Interrupted by server restart' "
        "WHERE status IN ('running', 'pending')"
    )
    count = cur.rowcount
    if count > 0:
        logger.info("Recovered %d interrupted job(s) on startup", count)
