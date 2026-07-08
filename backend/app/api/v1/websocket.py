"""WebSocket endpoint for real-time job progress/logs streaming."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.job_service import get_job_service
from app.services.websocket_manager import ConnectionManager, get_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{job_id}")  # type: ignore[misc]
async def websocket_endpoint(ws: WebSocket, job_id: str) -> None:
    """Accept a WebSocket connection for *job_id* and stream messages.

    The client can send JSON messages of the form ``{"type": "stop", ...}`` to
    request cancellation.  On disconnect or stop the manager removes the
    connection from the room.
    """
    manager: ConnectionManager = get_ws_manager()

    try:
        await ws.accept()

        # Validate that the job exists before connecting a WS room.
        job = get_job_service().get(job_id)
        if job is None:
            logger.warning("WS rejected for non-existent job %s", job_id)
            await ws.close(code=4004, reason="Job not found")
            return

        await manager.connect(job_id, ws)

        # Send current job status immediately on connect
        await ws.send_text(json.dumps({
            "type": "status",
            "job_id": job_id,
            "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
        }))
        logger.info("WS connected for job %s", job_id)
    except WebSocketDisconnect as exc:  # noqa: BLE001 — accept may raise on close
        logger.warning("WS rejected before accept for job %s: %s", job_id, exc)
        return

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            if msg.get("type") == "stop":
                logger.info("Client requested stop for job %s", job_id)
                try:
                    get_job_service().request_stop(job_id)
                except KeyError:
                    pass  # job not found — nothing to stop
                break
    except WebSocketDisconnect as exc:  # noqa: BLE001 — receive may raise on close
        logger.warning("WS disconnected for job %s: %s", job_id, exc)
    finally:
        await manager.disconnect(job_id, ws)
