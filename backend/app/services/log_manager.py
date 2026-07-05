"""Thread-safe JSON-line logger for ETL jobs."""

import json
import logging
import threading
from pathlib import Path


_lock = threading.Lock()


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
    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter(
        '{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
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
