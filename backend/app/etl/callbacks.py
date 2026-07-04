"""WebSocket callback bridge — connects sync ETL pipeline to async WS broadcast.

The ETL pipeline (process_batch, process_pipeline) uses synchronous callbacks:
  - progress_callback(chunk_pct, global_pct, file_idx)
  - log_callback(message)
  - stop_check_callback() -> bool

These factories create sync callables that bridge to the async ConnectionManager
via asyncio.run_coroutine_threadsafe().
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.schemas.websocket import WSLogMessage, WSProgressMessage

if TYPE_CHECKING:
    from app.services.job_service import JobService
    from app.services.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)


def make_progress_cb(
    ws_manager: ConnectionManager,
    job_id: str,
    loop: asyncio.AbstractEventLoop,
) -> callable:
    """Create a sync progress callback for the ETL pipeline.
    
    The pipeline calls: progress_callback(chunk_pct, global_pct, file_idx)
    This broadcasts a WS progress message to all clients in the job room.
    
    Args:
        ws_manager: The WebSocket connection manager singleton.
        job_id: Current job identifier.
        loop: The running asyncio event loop (for run_coroutine_threadsafe).
        
    Returns:
        Sync callable with signature (chunk_pct: int, global_pct: int, file_idx: int) -> None
    """
    def cb(chunk_pct: int, global_pct: int, file_idx: int) -> None:
        try:
            msg = WSProgressMessage(
                type="progress",
                job_id=job_id,
                file_idx=file_idx,
                chunk_pct=chunk_pct,
                global_pct=global_pct,
            )
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(job_id, msg.model_dump()),
                loop,
            )
        except Exception as e:
            logger.warning("Failed to broadcast progress for job %s: %s", job_id, e)
    
    return cb


def make_log_cb(
    ws_manager: ConnectionManager,
    job_id: str,
    loop: asyncio.AbstractEventLoop,
) -> callable:
    """Create a sync log callback for the ETL pipeline.
    
    The pipeline calls: log_callback(message_text)
    This broadcasts a WS log message to all clients in the job room.
    
    Args:
        ws_manager: The WebSocket connection manager singleton.
        job_id: Current job identifier.
        loop: The running asyncio event loop.
        
    Returns:
        Sync callable with signature (message: str) -> None
    """
    def cb(message: str) -> None:
        try:
            msg = WSLogMessage(
                type="log",
                job_id=job_id,
                level="info",
                message=message,
            )
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(job_id, msg.model_dump()),
                loop,
            )
        except Exception as e:
            logger.warning("Failed to broadcast log for job %s: %s", job_id, e)
    
    return cb


def make_log_error_cb(
    ws_manager: ConnectionManager,
    job_id: str,
    loop: asyncio.AbstractEventLoop,
) -> callable:
    """Create a sync error log callback for the ETL pipeline.
    
    Same as make_log_cb but with level="error".
    
    Returns:
        Sync callable with signature (message: str) -> None
    """
    def cb(message: str) -> None:
        try:
            msg = WSLogMessage(
                type="log",
                job_id=job_id,
                level="error",
                message=message,
            )
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(job_id, msg.model_dump()),
                loop,
            )
        except Exception as e:
            logger.warning("Failed to broadcast error log for job %s: %s", job_id, e)
    
    return cb


def make_stop_cb(
    job_service: JobService,
    job_id: str,
) -> callable:
    """Create a sync stop-check callback for the ETL pipeline.
    
    The pipeline calls: stop_check_callback() -> bool
    This checks the job service's stop flag.
    
    Args:
        job_service: The job service singleton.
        job_id: Current job identifier.
        
    Returns:
        Sync callable with signature () -> bool
    """
    def cb() -> bool:
        return job_service.is_stopped(job_id)
    
    return cb


def create_callbacks(
    ws_manager: ConnectionManager,
    job_id: str,
    loop: asyncio.AbstractEventLoop,
    job_service: JobService,
) -> dict[str, callable]:
    """Create all ETL pipeline callbacks at once.
    
    Returns:
        Dict with keys: progress, log, log_error, stop
    """
    return {
        "progress": make_progress_cb(ws_manager, job_id, loop),
        "log": make_log_cb(ws_manager, job_id, loop),
        "log_error": make_log_error_cb(ws_manager, job_id, loop),
        "stop": make_stop_cb(job_service, job_id),
    }
