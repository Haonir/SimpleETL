"""Thread-safe JSON-line logger for ETL jobs."""

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path


_lock = threading.Lock()


class SQLiteLogHandler(logging.Handler):
    """Write log entries to the job_logs SQLite table."""

    def __init__(self, job_id: str) -> None:
        super().__init__()
        self.job_id = job_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from app.db import get_cursor
            timestamp = datetime.now(timezone.utc).isoformat()
            message = record.getMessage()
            level = record.levelname
            with get_cursor() as cur:
                cur.execute(
                    "INSERT INTO job_logs (job_id, timestamp, level, message) VALUES (?, ?, ?, ?)",
                    (self.job_id, timestamp, level, message),
                )
        except Exception:
            pass  # Don't let DB errors break logging


def create_job_logger(job_id: str, job_dir: Path) -> logging.Logger:
    """Create a thread-safe logger that writes JSON lines to {job_dir}/logs.json.

    Args:
        job_id: Unique job identifier used as the logger name prefix.
        job_dir: Directory where logs.json will be written.

    Returns:
        A configured Logger instance named "etl.{job_id}".
    """
    logger = logging.getLogger(f"etl.{job_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path = Path(job_dir) / "logs.json"
    Path(job_dir).mkdir(parents=True, exist_ok=True)
    from app.db import get_cursor
    with get_cursor() as cur:
        cur.execute("UPDATE jobs SET log_path = ? WHERE id = ?", (str(log_path), job_id))

    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter(
        '{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    sqlite_handler = SQLiteLogHandler(job_id)
    logger.addHandler(sqlite_handler)
    return logger


def make_log_cb(logger: logging.Logger) -> callable:
    """Create a thread-safe log callback for the ETL pipeline.

    Args:
        logger: A Logger instance (typically from create_job_logger).

    Returns:
        Sync callable with signature (message: str) -> None that writes to the logger.
    """
    def cb(message: str) -> None:
        with _lock:
            logger.info(message)
    return cb
