"""WebSocket message schemas for SimpleETL backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Server → Client messages ────────────────────────────────────────────────

class WSProgressMessage(BaseModel):
    """Chunk processing progress update."""

    type: Literal["progress"] = "progress"
    job_id: str
    file_name: str
    chunk_index: int
    total_chunks: int
    percent: float


class WSLogMessage(BaseModel):
    """Log line emitted during processing."""

    type: Literal["log"] = "log"
    job_id: str
    level: Literal["info", "warning", "error"] = "info"
    message: str


class WSStatusMessage(BaseModel):
    """Job status change (started, running, etc.)."""

    type: Literal["status"] = "status"
    job_id: str
    status: Literal["queued", "running", "paused", "stopped"]
    file_name: str | None = None


class WSDoneMessage(BaseModel):
    """Job completed successfully."""

    type: Literal["done"] = "done"
    job_id: str
    file_name: str
    total_chunks: int
    processed_chunks: int
    error_count: int = 0


class WSErrorMessage(BaseModel):
    """Job failed with an error."""

    type: Literal["error"] = "error"
    job_id: str
    file_name: str | None = None
    message: str


# ── Client → Server messages ────────────────────────────────────────────────

class WSStopMessage(BaseModel):
    """Client request to stop processing."""

    type: Literal["stop"] = "stop"
    job_id: str
