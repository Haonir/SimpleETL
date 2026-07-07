"""Thread-safe JSON-line logger for ETL jobs."""

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

# Custom log level for LLM processing
LLM_LEVEL = 25  # Between INFO (20) and WARNING (30)
logging.addLevelName(LLM_LEVEL, "LLM")


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
            level = record.levelname.lower()
            with get_cursor() as cur:
                cur.execute(
                    "INSERT INTO job_logs (job_id, timestamp, level, message) VALUES (?, ?, ?, ?)",
                    (self.job_id, timestamp, level, message),
                )
        except Exception:
            pass  # Don't let DB errors break logging


def create_job_logger(job_id: str) -> logging.Logger:
    """Create a thread-safe logger that writes to the job_logs SQLite table.

    Args:
        job_id: Unique job identifier used as the logger name prefix.

    Returns:
        A configured Logger instance named "etl.{job_id}".
    """
    logger = logging.getLogger(f"etl.{job_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    sqlite_handler = SQLiteLogHandler(job_id)
    logger.addHandler(sqlite_handler)
    return logger


def make_log_cb(logger: logging.Logger) -> callable:
    """Create a thread-safe log callback for the ETL pipeline.

    Args:
        logger: A Logger instance (typically from create_job_logger).

    Returns:
        Sync callable with signature (message: str, level: str | None = None) -> None
        that writes to the logger with the specified level.
    """
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "llm": LLM_LEVEL,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def cb(message: str, level: str | None = None) -> None:
        with _lock:
            log_level = level_map.get(level, logging.INFO) if level else logging.INFO
            logger.log(log_level, message)
    return cb
