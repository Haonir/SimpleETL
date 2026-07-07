"""Async ETL runner — orchestrates all pipeline modules.

Entry point for ETL job execution. Runs sync modules in thread pool executor,
bridges callbacks to WebSocket broadcast via the callbacks module.

Three-phase parallel pipeline:
  Phase 1: extract + split ALL files in parallel (ThreadPoolExecutor)
  Phase 2: LLM ALL chunks in parallel (ThreadPoolExecutor)
  Phase 3: pack ALL files in parallel (ThreadPoolExecutor)
"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from app.settings import get_settings

from app.etl.callbacks import create_callbacks
from app.services.log_manager import create_job_logger
from app.schemas.job import JobStatus
from app.schemas.websocket import WSLogMessage, WSStatusMessage, WSDoneMessage, WSErrorMessage

from app.etl.splitter import run_phase_prepare
from app.etl.llm_processor import run_phase_llm, copy_chunks_to_processed
from app.etl.packer import run_phase_pack

if TYPE_CHECKING:
    from app.services.job_service import JobService
    from app.services.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)


async def run_etl_job(
    job_id: str,
    file_paths: list[str],
    config: dict,
    job_service: JobService,
    ws_manager: ConnectionManager,
) -> None:
    """Run an ETL job asynchronously.

    Three-phase parallel pipeline:
      Phase 1: extract + split ALL files in parallel (ThreadPoolExecutor)
      Phase 2: LLM ALL chunks in parallel (ThreadPoolExecutor)
      Phase 3: pack ALL files in parallel (ThreadPoolExecutor)

    Args:
        job_id: Unique job identifier.
        file_paths: List of file paths to process.
        config: ETL configuration dict with keys:
            - model, base_url, api_key (LLM settings)
            - chunk_size, chunk_overlap, max_workers, output_format
            - prompt (system prompt text)
            - skip_llm (bool)
        job_service: Job service singleton.
        ws_manager: WebSocket manager singleton.
    """
    loop = asyncio.get_event_loop()

    # Create SQLite logger for this job
    job_logger = create_job_logger(job_id)

    callbacks = create_callbacks(ws_manager, job_id, loop, job_service, job_logger=job_logger)
    progress_cb = callbacks["progress"]
    log_cb = callbacks["log"]
    log_error_cb = callbacks["log_error"]
    stop_cb = callbacks["stop"]

    def log_and_broadcast(message: str, level: str = "info") -> None:
        """Log to SQLite + broadcast via WS with specified level."""
        log_cb(message, level)

    try:
        # Transition job to running
        job_service.update_status(job_id, JobStatus.running)
        await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="running").model_dump())

        if not file_paths:
            log_and_broadcast("⚠️ No files provided.", "warning")
            job_service.update_status(job_id, JobStatus.completed)
            await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="completed").model_dump())
            return

        total_files = len(file_paths)
        log_and_broadcast(f"🚀 Starting ETL job with {total_files} file(s)...")

        # Flatten nested config: frontend sends {"llm": {...}, "processing": {...}}
        # but pipeline expects flat keys like "model", "base_url", etc.
        llm_cfg = config.get("llm", {})
        proc_cfg = config.get("processing", {})
        flat_config = {**proc_cfg, **llm_cfg}
        if "prompt_text" in config:
            flat_config.setdefault("prompt", config["prompt_text"])

        for key in ("output_dir", "output_format", "skip_llm", "skip_chunking"):
            if key in config:
                flat_config.setdefault(key, config[key])

        max_workers = flat_config.get("max_workers", 2)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            # ── Phase 1: extract + split (parallel) ──
            log_and_broadcast("--- Phase 1: Extract & Split ---")

            registry = await run_phase_prepare(pool, file_paths, flat_config, log_cb, stop_cb, job_id)

            if registry is None:
                return

            # Ensure output directory exists for phase 3
            first_base_name = next(iter(registry))
            output_dir_path = Path(_get_output_dir(file_paths[0], job_id))
            output_dir_path.mkdir(parents=True, exist_ok=True)

            llm_errors: set[str] = set()

            # ── Phase 2: LLM (parallel) ──
            if flat_config.get("skip_llm", False):
                log_and_broadcast("--- Phase 2: Skipping LLM (skip_llm=True) ---")
                for base_name, info in registry.items():
                    copy_chunks_to_processed(
                        info["chunks_dir"], info["processed_dir"], base_name, log_cb
                    )
            else:
                log_and_broadcast("--- Phase 2: LLM Processing ---")
                success, llm_errors = await run_phase_llm(pool, registry, flat_config, log_cb, stop_cb, progress_cb)

                if not success and stop_cb():
                    job_service.update_status(job_id, JobStatus.stopped)
                    log_and_broadcast("⚠️ ETL job stopped by user.", "warning")
                    await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="stopped").model_dump())
                    return

            # ── Phase 3: pack (parallel) ──
            log_and_broadcast("--- Phase 3: Packing ---")
            log_and_broadcast(f"Packing as '{flat_config.get('output_format', 'spr')}'")
            output_files = await run_phase_pack(pool, registry, flat_config, log_cb)

            # Save output file records to SQLite
            if output_files:
                from app.services.job_service import get_job_service
                output_records = []
                for fpath in output_files:
                    p = Path(fpath)
                    output_records.append({
                        "filename": p.name,
                        "file_path": str(p),
                        "size_bytes": p.stat().st_size if p.exists() else 0,
                        "format": p.suffix.lstrip(".") or "unknown",
                    })
                get_job_service().save_outputs(job_id, output_records)

        # Final status
        if not stop_cb():
            if llm_errors:
                if output_files:
                    # Some files processed, some failed — partial
                    job_service.update_status(job_id, JobStatus.partial)
                    log_and_broadcast(f"⚠️ ETL job completed with errors in {len(llm_errors)} file(s): {', '.join(sorted(llm_errors))}", "warning")
                    await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="partial").model_dump())
                else:
                    # No output files at all — full error
                    job_service.update_status(job_id, JobStatus.error)
                    log_and_broadcast(f"❌ ETL job failed — no files were processed successfully. Errors in: {', '.join(sorted(llm_errors))}", "error")
                    await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="error").model_dump())
            else:
                # Completed successfully
                job_service.update_status(job_id, JobStatus.completed)
                log_and_broadcast("🎉 ETL job completed!", "info")
                await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="completed").model_dump())

            # Broadcast done message
            await ws_manager.broadcast(
                job_id,
                WSDoneMessage(
                    type="done",
                    job_id=job_id,
                    output_dir=str(output_dir_path),
                ).model_dump(),
            )
        elif stop_cb():
            job_service.update_status(job_id, JobStatus.stopped)
            log_and_broadcast("⚠️ ETL job stopped by user.", "warning")
            await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="stopped").model_dump())

    except Exception as e:
        logger.exception("Critical error in ETL job %s", job_id)
        job_service.update_status(job_id, JobStatus.error, error_message=str(e))
        await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="error").model_dump())

        await ws_manager.broadcast(
            job_id,
            WSErrorMessage(
                type="error",
                job_id=job_id,
                message=str(e),
            ).model_dump(),
        )



def _get_output_dir(file_path: str, job_id: str) -> str:
    """Get the output directory for a file."""
    file_name = os.path.basename(file_path)
    base_name = Path(file_name).stem
    # Try to get original filename from FileService
    try:
        from app.services.file_service import get_file_service
        fs = get_file_service()
        file_id = base_name
        item = fs.get_file(file_id)
        if item:
            base_name = Path(item.filename).stem
    except Exception:
        pass
    settings = get_settings()
    return str(settings.output_dir / job_id / base_name)
