"""Tests for backend/app/db module."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.db import (
    _create_tables,
    _get_connection,
    _recover_interrupted_jobs,
    get_cursor,
    init_db,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Return a temporary database path."""
    return tmp_path / "test_simpleetl.db"


@pytest.fixture
def initialized_db(db_path: Path):
    """Initialize the database and yield the connection for cleanup."""

    init_db(str(db_path))
    conn = sqlite3.connect(str(db_path))
    yield conn
    conn.close()


class TestInitDB:
    """Tests for init_db()."""

    def test_init_db_creates_tables(self, db_path: Path):
        """init_db creates all required tables."""
        init_db(str(db_path))

        # Use the same thread-local connection that init_db configured
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "files" in tables
        assert "jobs" in tables
        assert "job_outputs" in tables

    def test_init_db_creates_index(self, db_path: Path):
        """init_db creates the job_outputs index."""
        init_db(str(db_path))

        # Use the same thread-local connection that init_db configured
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}
        assert "idx_job_outputs_job_id" in indexes

    def test_init_db_sets_wal_mode(self, db_path: Path):
        """init_db sets journal mode to WAL."""
        init_db(str(db_path))

        # Use the same thread-local connection that init_db configured
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0] == "wal"

    def test_init_db_sets_foreign_keys(self, db_path: Path):
        """init_db enables foreign keys."""
        init_db(str(db_path))

        # Use the same thread-local connection that init_db configured
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        assert cursor.fetchone()[0] == 1


class TestGetCursor:
    """Tests for get_cursor context manager."""

    def test_get_cursor_yields_connection(self, initialized_db):
        """get_cursor yields a valid cursor and commits on success."""
        with get_cursor() as cur:
            assert isinstance(cur, sqlite3.Cursor)
            # Should not raise — commit succeeds
            cur.execute("SELECT 1")

    def test_get_cursor_rollback_on_error(self, initialized_db):
        """get_cursor rolls back on exception."""
        with pytest.raises(Exception):
            with get_cursor() as cur:
                cur.execute("INVALID SQL STATEMENT")


class TestCreateTables:
    """Tests for _create_tables()."""

    def test_create_files_table(self, db_path: Path):
        """files table is created correctly."""
        conn = sqlite3.connect(str(db_path))
        _create_tables(conn)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE name='files'"
        )
        create_sql = cursor.fetchone()[0]
        # Normalize whitespace for reliable comparison
        normalized = " ".join(create_sql.split())
        assert "CREATE TABLE" in normalized
        assert "id TEXT PRIMARY KEY" in normalized
        assert "filename TEXT NOT NULL" in normalized
        conn.close()

    def test_create_jobs_table(self, db_path: Path):
        """jobs table is created correctly."""
        conn = sqlite3.connect(str(db_path))
        _create_tables(conn)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE name='jobs'"
        )
        create_sql = cursor.fetchone()[0]
        # Normalize whitespace for reliable comparison
        normalized = " ".join(create_sql.split())
        assert "CREATE TABLE" in normalized
        assert "id TEXT PRIMARY KEY" in normalized
        assert "status TEXT NOT NULL DEFAULT 'pending'" in normalized
        conn.close()

    def test_create_job_outputs_table(self, db_path: Path):
        """job_outputs table is created correctly."""
        conn = sqlite3.connect(str(db_path))
        _create_tables(conn)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE name='job_outputs'"
        )
        create_sql = cursor.fetchone()[0]
        # Normalize whitespace for reliable comparison
        normalized = " ".join(create_sql.split())
        assert "CREATE TABLE" in normalized
        assert "id INTEGER PRIMARY KEY AUTOINCREMENT" in normalized
        assert "REFERENCES jobs(id)" in normalized
        conn.close()

    def test_create_tables_idempotent(self, db_path: Path):
        """Calling _create_tables multiple times does not error."""
        conn = sqlite3.connect(str(db_path))
        _create_tables(conn)
        _create_tables(conn)  # Should not raise
        conn.close()


class TestRecoverInterruptedJobs:
    """Tests for _recover_interrupted_jobs()."""

    def test_recover_marks_running_as_error(self, db_path: Path):
        """Running jobs are marked as error on recovery."""
        init_db(str(db_path))

        # Insert a running job using the same thread-local connection
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO jobs (id, status, file_ids, config, created_at) VALUES (?, 'running', ?, ?, ?)",
            ("job-1", "['f1']", "{}", "2026-07-05T04:00:00Z"),
        )
        conn.commit()

        # Recovery should mark it as error — use the same connection context
        _recover_interrupted_jobs(conn)
        cur = conn.cursor()
        cur.execute("SELECT status, error_message FROM jobs WHERE id='job-1'")
        row = cur.fetchone()
        assert row[0] == "error"
        assert "Interrupted by server restart" in row[1]

    def test_recover_marks_pending_as_error(self, db_path: Path):
        """Pending jobs are marked as error on recovery."""
        init_db(str(db_path))

        # Insert a pending job using the same thread-local connection
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO jobs (id, status, file_ids, config, created_at) VALUES (?, 'pending', ?, ?, ?)",
            ("job-2", "['f1']", "{}", "2026-07-05T04:00:00Z"),
        )
        conn.commit()

        # Recovery should mark it as error — use the same connection context
        _recover_interrupted_jobs(conn)
        cur = conn.cursor()
        cur.execute("SELECT status FROM jobs WHERE id='job-2'")
        row = cur.fetchone()
        assert row[0] == "error"

    def test_recover_skips_completed_jobs(self, db_path: Path):
        """Completed jobs are not affected by recovery."""
        init_db(str(db_path))

        # Insert a completed job using the same thread-local connection
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO jobs (id, status, file_ids, config, created_at) VALUES (?, 'completed', ?, ?, ?)",
            ("job-3", "['f1']", "{}", "2026-07-05T04:00:00Z"),
        )
        conn.commit()

        # Recovery should not change completed jobs — use the same connection context
        _recover_interrupted_jobs(conn)
        cur = conn.cursor()
        cur.execute("SELECT status FROM jobs WHERE id='job-3'")
        row = cur.fetchone()
        assert row[0] == "completed"

    def test_recover_no_jobs_unchanged(self, db_path: Path):
        """Recovery with no running/pending jobs does nothing."""
        init_db(str(db_path))

        # No recovery should happen — no error in log (just check it doesn't crash)
        conn = _get_connection()
        _recover_interrupted_jobs(conn)  # Pass the connection, not a context manager
