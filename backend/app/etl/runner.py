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
from app.schemas.websocket import WSLogMessage, WSStatusMessage, WSDoneMessage, WSErrorMessage, WSFileDoneMessage

import threading

from app.etl.splitter import _extract_and_split
from app.etl.llm_processor import run_phase_llm, copy_chunks_to_processed
from app.etl.packer import pack_outputs

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
    """Run an ETL job with file-level streaming pipeline.

    Each file independently goes through: extract → split → LLM → pack.
    Files are processed in parallel. Output is available as each file completes.
    If one file fails, others continue. On stop, partial output is preserved.

    Args:
        job_id: Unique job identifier.
        file_paths: List of file paths to process.
        config: ETL configuration dict.
        job_service: Job service singleton.
        ws_manager: WebSocket manager singleton.
    """
    loop = asyncio.get_event_loop()

    job_logger = create_job_logger(job_id)
    callbacks = create_callbacks(ws_manager, job_id, loop, job_service, job_logger=job_logger)
    progress_cb = callbacks["progress"]
    log_cb = callbacks["log"]
    log_error_cb = callbacks["log_error"]
    stop_cb = callbacks["stop"]

    def log_and_broadcast(message: str, level: str = "info") -> None:
        log_cb(message, level)

    try:
        job_service.update_status(job_id, JobStatus.running)
        await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="running").model_dump())

        if not file_paths:
            log_and_broadcast("⚠️ No files provided.", "warning")
            job_service.update_status(job_id, JobStatus.completed)
            await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="completed").model_dump())
            return

        total_files = len(file_paths)
        log_and_broadcast(f"🚀 Starting ETL job with {total_files} file(s)...")

        llm_cfg = config.get("llm", {})
        proc_cfg = config.get("processing", {})
        flat_config = {**proc_cfg, **llm_cfg}
        if "prompt_text" in config:
            flat_config.setdefault("prompt", config["prompt_text"])
        for key in ("output_dir", "output_format", "skip_llm", "skip_chunking"):
            if key in config:
                flat_config.setdefault(key, config[key])

        max_workers = flat_config.get("max_workers", 2)

        # Shared state for progress tracking across files
        completed_files_count = [0]
        progress_lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            # Create per-file pipeline tasks
            tasks = []
            for i, fp in enumerate(file_paths):
                task = asyncio.create_task(
                    _process_file(
                        pool, fp, flat_config, log_cb, stop_cb, progress_cb,
                        file_idx=i, total_files=total_files, job_id=job_id,
                        completed_files_count=completed_files_count,
                        progress_lock=progress_lock,
                    )
                )
                tasks.append(task)

            all_output_files: list[str] = []
            all_errors: set[str] = set()

            # Process results as each file completes
            for coro in asyncio.as_completed(tasks):
                if stop_cb():
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    break
                try:
                    file_idx, base_name, output_files, errors = await coro
                    if output_files:
                        all_output_files.extend(output_files)
                        _save_outputs(job_id, output_files)
                        # Notify frontend that output files are now available
                        await ws_manager.broadcast(
                            job_id,
                            WSFileDoneMessage(
                                type="file_done",
                                job_id=job_id,
                                file_idx=file_idx,
                                base_name=base_name,
                            ).model_dump(),
                        )
                    if errors:
                        all_errors.update(errors)
                except asyncio.CancelledError:
                    pass

        # Final status
        settings = get_settings()
        output_dir_path = settings.output_dir / job_id

        if not stop_cb():
            if all_errors:
                if all_output_files:
                    job_service.update_status(job_id, JobStatus.partial)
                    log_and_broadcast(f"⚠️ ETL job completed with errors in {len(all_errors)} file(s): {', '.join(sorted(all_errors))}", "warning")
                    await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="partial").model_dump())
                else:
                    job_service.update_status(job_id, JobStatus.error)
                    log_and_broadcast(f"❌ ETL job failed — no files were processed successfully. Errors in: {', '.join(sorted(all_errors))}", "error")
                    await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="error").model_dump())
            else:
                job_service.update_status(job_id, JobStatus.completed)
                log_and_broadcast("🎉 ETL job completed!", "info")
                await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="completed").model_dump())

            await ws_manager.broadcast(
                job_id,
                WSDoneMessage(
                    type="done",
                    job_id=job_id,
                    output_dir=str(output_dir_path),
                ).model_dump(),
            )
        elif stop_cb():
            if all_output_files:
                job_service.update_status(job_id, JobStatus.partial)
                log_and_broadcast(f"⚠️ ETL job stopped. Partial output: {len(all_output_files)} file(s).", "warning")
                await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="partial").model_dump())
                await ws_manager.broadcast(
                    job_id,
                    WSDoneMessage(type="done", job_id=job_id, output_dir=str(output_dir_path)).model_dump(),
                )
            else:
                job_service.update_status(job_id, JobStatus.stopped)
                log_and_broadcast("⚠️ ETL job stopped by user.", "warning")
                await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="stopped").model_dump())

    except Exception as e:
        logger.exception("Critical error in ETL job %s", job_id)
        job_service.update_status(job_id, JobStatus.error, error_message=str(e))
        await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="error").model_dump())
        await ws_manager.broadcast(
            job_id,
            WSErrorMessage(type="error", job_id=job_id, message=str(e)).model_dump(),
        )


async def _process_file(
    pool: ThreadPoolExecutor,
    file_path: str,
    flat_config: dict,
    log_cb: callable,
    stop_cb: callable,
    progress_cb: callable,
    file_idx: int,
    total_files: int,
    job_id: str,
    completed_files_count: list[int],
    progress_lock: threading.Lock,
) -> tuple[int, str, list[str], set[str]]:
    """Full pipeline for one file: extract → split → LLM → pack.

    Args:
        pool: Thread pool executor.
        file_path: Path to the input file.
        flat_config: Flattened ETL configuration dict.
        log_cb: Logging callback (sync).
        stop_cb: Stop-check callback.
        progress_cb: Progress callback (chunk_pct, global_pct, file_idx).
        file_idx: Index of this file in the job.
        total_files: Total number of files in the job.
        job_id: Unique job identifier.
        completed_files_count: Mutable list [int] tracking completed files.
        progress_lock: Lock for thread-safe progress updates.

    Returns:
        Tuple of (file_idx, base_name, output_files, errors_set).
    """
    loop = asyncio.get_event_loop()

    def file_progress(chunk_pct: int, global_pct: int, _: int) -> None:
        """Adjust global_pct to account for completed files."""
        with progress_lock:
            adjusted = int((completed_files_count[0] * 100 + chunk_pct) / total_files)
        progress_cb(chunk_pct, adjusted, file_idx)

    try:
        log_cb(f"📄 Processing file {file_idx + 1}/{total_files}: {Path(file_path).name}")

        # Step 1: Extract + split
        base_name, chunk_paths, dirs = await loop.run_in_executor(
            pool, _extract_and_split, file_path, flat_config, log_cb, job_id
        )
        registry = {base_name: {"chunk_paths": chunk_paths, **dirs}}

        errors: set[str] = set()

        # Step 2: LLM
        if stop_cb():
            return file_idx, base_name, [], errors

        if flat_config.get("skip_llm", False):
            copy_chunks_to_processed(dirs["chunks_dir"], dirs["processed_dir"], base_name, log_cb)
        else:
            success, errors = await run_phase_llm(
                pool, registry, flat_config, log_cb, stop_cb, file_progress
            )

        # Step 3: Pack
        if stop_cb():
            return file_idx, base_name, [], errors

        output_files = await loop.run_in_executor(
            None, pack_outputs,
            dirs["processed_dir"], dirs["final_dir"], base_name,
            flat_config.get("output_format", "spr"), log_cb,
        )

        # Mark file as completed for progress tracking
        with progress_lock:
            completed_files_count[0] += 1

        log_cb(f"✅ File {file_idx + 1}/{total_files} done: {base_name} ({len(output_files)} output files)")
        return file_idx, base_name, output_files, errors

    except Exception as e:
        log_cb(f"⚠️ Error processing {Path(file_path).name}: {e}", "error")
        base_name = Path(file_path).stem
        return file_idx, base_name, [], {base_name}


def _save_outputs(job_id: str, output_files: list[str]) -> None:
    """Save output file records to SQLite."""
    try:
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
    except Exception as e:
        logger.warning("Failed to save outputs for job %s: %s", job_id, e)



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
