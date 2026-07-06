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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from app.etl.callbacks import create_callbacks
from app.services.log_manager import create_job_logger
from app.schemas.job import JobStatus
from app.schemas.websocket import WSLogMessage, WSStatusMessage, WSDoneMessage, WSErrorMessage
try:
    import openai
except ImportError:
    openai = None

from app.etl.extractor import extract_text
from app.etl.packer import pack_outputs
from app.etl.splitter import split_to_chunks

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
            - skip_llm (bool), cleanup (bool)
        job_service: Job service singleton.
        ws_manager: WebSocket manager singleton.
    """
    loop = asyncio.get_event_loop()

    # Create file-based JSON logger for this job
    # Use job_dir (parent of output/) so logs.json lives alongside output/
    job = job_service.get(job_id)
    if job and job.output_dir:
        job_dir = Path(job.output_dir).parent
    else:
        job_dir = Path("/tmp/SimpleETL/jobs") / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    job_logger = create_job_logger(job_id, job_dir)

    callbacks = create_callbacks(ws_manager, job_id, loop, job_service, job_logger=job_logger)
    progress_cb = callbacks["progress"]
    log_cb = callbacks["log"]
    stop_cb = callbacks["stop"]

    def log_and_broadcast(message: str, level: str = "info") -> None:
        """Log to SQLite + broadcast via WS (handled by log_cb internally)."""
        log_cb(message)

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

        for key in ("output_dir", "output_format", "skip_llm", "cleanup"):
            if key in config:
                flat_config.setdefault(key, config[key])

        max_workers = flat_config.get("max_workers", 2)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            # ── Phase 1: extract + split (parallel) ──
            log_and_broadcast("--- Phase 1: Extract & Split ---")

            registry = await _phase_prepare(pool, file_paths, flat_config, log_cb, stop_cb)

            if registry is None:
                return

            # Ensure output directory exists for phase 3
            first_base_name = next(iter(registry))
            output_dir_path = Path(_get_output_dir(file_paths[0], config))
            output_dir_path.mkdir(parents=True, exist_ok=True)

            # ── Phase 2: LLM (parallel) ──
            if flat_config.get("skip_llm", False):
                log_and_broadcast("--- Phase 2: Skipping LLM (skip_llm=True) ---")
                from app.etl.llm_processor import copy_chunks_to_processed
                for base_name, info in registry.items():
                    copy_chunks_to_processed(
                        info["chunks_dir"], info["processed_dir"], base_name, log_cb
                    )
            else:
                log_and_broadcast("--- Phase 2: LLM Processing ---")
                success = await _phase_llm(pool, registry, flat_config, log_cb, stop_cb, progress_cb)

                if not success and stop_cb():
                    job_service.update_status(job_id, JobStatus.stopped)
                    log_and_broadcast("⚠️ ETL job stopped by user.")
                    await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="stopped").model_dump())
                    return

            # ── Phase 3: pack (parallel) ──
            log_and_broadcast("--- Phase 3: Packing ---")
            output_files = await _phase_pack(pool, registry, flat_config, log_cb)

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
            job_service.update_status(job_id, JobStatus.completed)
            await ws_manager.broadcast(job_id, WSLogMessage(type="log", job_id=job_id, level="info", message="🎉 ETL job completed!").model_dump())
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
            await ws_manager.broadcast(job_id, WSLogMessage(type="log", job_id=job_id, level="info", message="⚠️ ETL job stopped by user.").model_dump())
            await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="stopped").model_dump())
        else:
            job_service.update_status(job_id, JobStatus.completed)
            await ws_manager.broadcast(job_id, WSLogMessage(type="log", job_id=job_id, level="info", message="⚠️ ETL job completed with errors.").model_dump())
            await ws_manager.broadcast(job_id, WSStatusMessage(type="status", job_id=job_id, status="completed").model_dump())

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


async def _phase_prepare(pool, file_paths, flat_config, log_cb, stop_cb):
    """Parallel extract + split for all files."""
    loop = asyncio.get_event_loop()
    registry = {}
    futures = {}
    for file_path in file_paths:
        future = loop.run_in_executor(pool, _extract_and_split, file_path, flat_config, log_cb)
        futures[future] = file_path
    for future in asyncio.as_completed(list(futures.keys())):
        if stop_cb():
            for f in futures:
                try:
                    f.cancel()
                except Exception:
                    pass
            return None
        try:
            base_name, chunk_paths, dirs = await future
            registry[base_name] = {"chunk_paths": chunk_paths, **dirs}
        except Exception as e:
            log_cb(f"⚠️ Extract error: {e}")
    return registry


def _extract_and_split(
    file_path: str,
    flat_config: dict,
    log_cb: callable,
) -> tuple[str, list[str], dict]:
    """Extract text + split into chunks (sync, runs in thread).

    Args:
        file_path: Path to the input file.
        flat_config: Flattened ETL configuration dict.
        log_cb: Logging callback (sync).

    Returns:
        Tuple of (base_name, chunk_file_paths, dirs_dict) where dirs_dict contains
        chunks_dir, processed_dir, final_dir paths.
    """
    file_name = os.path.basename(file_path)
    base_name = Path(file_name).stem

    # Try to get original filename from FileService
    try:
        from app.services.file_service import get_file_service
        fs = get_file_service()
        for f in fs.list_files().files:
            stored_path = fs.get_path(f.id)
            if stored_path and str(stored_path) == str(file_path):
                base_name = Path(f.filename).stem
                break
    except Exception:
        pass  # Fall back to UUID-based name

    output_base = flat_config.get("output_dir", "/tmp/SimpleETL/output")
    file_output_dir = os.path.join(output_base, base_name)

    chunks_dir = os.path.join(file_output_dir, "chunks")
    processed_dir = os.path.join(file_output_dir, "processed")
    final_dir = os.path.join(file_output_dir, "final")

    # Step 1: Extract text (sync)
    log_cb("--- Extracting text ---")
    text = extract_text(file_path, log_cb)

    if not text.strip():
        raise Exception("File is empty or contains no readable text.")

    # Step 2: Split into chunks (sync)
    log_cb("--- Splitting into chunks ---")
    chunk_size = flat_config.get("chunk_size", 10000)
    chunk_overlap = flat_config.get("chunk_overlap", 1500)

    chunk_files = split_to_chunks(
        text=text,
        output_dir=chunks_dir,
        base_name=base_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        log_callback=log_cb,
    )

    return base_name, chunk_files, {
        "chunks_dir": chunks_dir,
        "processed_dir": processed_dir,
        "final_dir": final_dir,
    }


async def _phase_llm(
    pool: ThreadPoolExecutor,
    registry: dict[str, dict],
    flat_config: dict,
    log_cb: callable,
    stop_cb: callable,
    progress_cb: callable,
) -> bool:
    """Parallel LLM processing for all chunks.

    Each chunk is processed individually in the thread pool for true parallelism.
    Failures on individual chunks are logged but do not stop the pipeline (fail-continue).

    Args:
        pool: Thread pool executor.
        registry: Registry from Phase 1 with chunk_paths per file.
        flat_config: Flattened ETL configuration dict.
        log_cb: Logging callback (sync).
        stop_cb: Stop-check callback (returns True when stopped).
        progress_cb: Progress callback (chunk_pct, global_pct, file_idx).

    Returns:
        True if processing completed (even with some errors), False if stopped.
    """
    loop = asyncio.get_event_loop()
    # Per-file chunk tracking
    file_list = list(registry.items())  # [(base_name, info), ...]
    file_chunk_counts = {i: len(info["chunk_paths"]) for i, (_, info) in enumerate(file_list)}
    file_counters = {i: 0 for i in range(len(file_list))}
    lock = threading.Lock()

    def _process_one_chunk(chunk_path: Path, processed_path: Path, config: dict, file_idx: int) -> Optional[str]:
        """Process one chunk (sync, runs in thread pool via run_in_executor)."""
        if processed_path.exists():
            return "skip"

        processed_path.parent.mkdir(parents=True, exist_ok=True)

        # Check stop flag before making the (potentially long) API call
        if stop_cb():
            return None

        client = openai.OpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
        )
        response = client.chat.completions.create(
            model=config.get("model", "llama3"),
            messages=[
                {"role": "system", "content": config.get("prompt", "Analyze this text.")},
                {
                    "role": "user",
                    "content": (Path(chunk_path)).read_text(encoding='utf-8'),
                },
            ],
            temperature=0.2,
        )
        with open(processed_path, "w") as f:
            f.write(response.choices[0].message.content)

        with lock:
            file_counters[file_idx] += 1
            total_chunks = file_chunk_counts[file_idx]
            file_pct = file_counters[file_idx] * 100 // max(total_chunks, 1)
            global_done = sum(file_counters.values())
            global_total = sum(file_chunk_counts.values())
            global_pct = global_done * 100 // max(global_total, 1)
            progress_cb(file_pct, global_pct, file_idx)

    # Submit chunks one at a time, checking stop between each submission.
    futures = []
    for file_idx, (base_name, info) in enumerate(file_list):
        for chunk_path_str in info["chunk_paths"]:
            if stop_cb():
                # Don't submit more chunks if stop was requested
                for f in futures:
                    try:
                        f.cancel()
                    except Exception:
                        pass
                return False
            processed_path = Path(info["processed_dir"]) / Path(chunk_path_str).name
            future = loop.run_in_executor(
                pool,
                _process_one_chunk,
                Path(chunk_path_str),
                processed_path,
                flat_config,
                file_idx,
            )
            futures.append(future)

    for future in asyncio.as_completed(futures):
        if stop_cb():
            for f in futures:
                try:
                    f.cancel()
                except Exception:
                    pass
            return False

        try:
            await future  # Non-blocking — event loop processes heartbeats while waiting
        except Exception as e:
            log_cb(f"⚠️ LLM error: {e}")  # fail-continue

    return True


async def _phase_pack(pool, registry, flat_config, log_cb) -> list[str]:
    """Parallel pack for all files. Returns list of output file paths."""
    loop = asyncio.get_event_loop()
    output_format = flat_config.get("output_format", "spr")
    all_outputs = []
    futures = []
    for base_name, info in registry.items():
        future = loop.run_in_executor(
            pool, pack_outputs,
            info["processed_dir"], info["final_dir"], base_name, output_format, log_cb,
        )
        futures.append(future)
    for future in asyncio.as_completed(futures):
        try:
            result = await future
            if result:
                all_outputs.extend(result)
        except Exception as e:
            log_cb(f"⚠️ Pack error: {e}")
    return all_outputs


def _get_output_dir(file_path: str, config: dict) -> str:
    """Get the output directory for a file."""
    file_name = os.path.basename(file_path)
    base_name = Path(file_name).stem
    output_base = config.get("output_dir", "/tmp/SimpleETL/output")
    return os.path.join(output_base, base_name, "final")
