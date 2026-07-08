"""LLM processing of text chunks via OpenAI-compatible API.

Reads chunk files from chunks/ directory, processes them through LLM,
and saves results to processed/ directory.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor


async def run_phase_llm(
    pool: ThreadPoolExecutor,
    registry: dict[str, dict],
    flat_config: dict,
    log_cb: callable,
    stop_cb: callable,
    progress_cb: callable,
) -> tuple[bool, set[str]]:
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
        Tuple of (success_bool, files_with_errors_set).
        success_bool is True if processing completed (even with some errors), False if stopped.
        files_with_errors_set contains base names of files that had LLM errors.
    """
    loop = asyncio.get_event_loop()
    # Per-file chunk tracking
    file_list = list(registry.items())  # [(base_name, info), ...]
    file_chunk_counts = {i: len(info["chunk_paths"]) for i, (_, info) in enumerate(file_list)}
    file_counters = {i: 0 for i in range(len(file_list))}
    lock = threading.Lock()

    def _process_one_chunk(chunk_path: Path, processed_path: Path, config: dict, file_idx: int, log_cb: callable, files_with_errors: set) -> Optional[str]:
        """Process one chunk (sync, runs in thread pool via run_in_executor)."""
        chunk_name = chunk_path.name
        base_name = file_list[file_idx][0]  # Get base_name from file_list
        if processed_path.exists():
            log_cb(f"⏭ Chunk {chunk_name} already processed, skipping.", "llm")
            return "skip"

        processed_path.parent.mkdir(parents=True, exist_ok=True)

        # Check stop flag before making the (potentially long) API call
        if stop_cb():
            return None

        log_cb(f"🤖 Processing chunk {chunk_name}...", "llm")
        try:
            client = OpenAI(
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
            
            log_cb(f"✅ Chunk {chunk_name} done ({file_counters[file_idx]}/{total_chunks} for file)", "llm")
        except Exception as e:
            files_with_errors.add(base_name)
            err_detail = f"{type(e).__name__}: {e}"
            log_cb(f"⚠️ LLM error for {base_name}: {err_detail} (base_url={config.get('base_url', 'N/A')}, model={config.get('model', 'N/A')})", "error")

    # Submit chunks one at a time, checking stop between each submission.
    futures = []
    files_with_errors = set()  # Track files that had errors
    
    for file_idx, (base_name, info) in enumerate(file_list):
        for chunk_path_str in info["chunk_paths"]:
            if stop_cb():
                # Don't submit more chunks if stop was requested
                for f in futures:
                    try:
                        f.cancel()
                    except Exception:
                        logger.debug("Failed to cancel future during stop")
                return False, files_with_errors
            processed_path = Path(info["processed_dir"]) / Path(chunk_path_str).name
            future = loop.run_in_executor(
                pool,
                _process_one_chunk,
                Path(chunk_path_str),
                processed_path,
                flat_config,
                file_idx,
                log_cb,
                files_with_errors,
            )
            futures.append(future)

    for future in asyncio.as_completed(futures):
        if stop_cb():
            for f in futures:
                try:
                    f.cancel()
                except Exception:
                    logger.debug("Failed to cancel future during stop")
            return False, files_with_errors

        try:
            await future  # Non-blocking — event loop processes heartbeats while waiting
        except Exception as e:
            log_cb(f"⚠️ Unexpected LLM error: {e}", "error")

    # Report files with errors
    if files_with_errors:
        log_cb(f"⚠️ LLM errors occurred for {len(files_with_errors)} file(s): {', '.join(sorted(files_with_errors))}", "warning")
    
    return True, files_with_errors


def copy_chunks_to_processed(
    chunks_dir: str | Path,
    processed_dir: str | Path,
    base_name: str = "chunk",
    log_callback: Optional[Callable[[str], None]] = None,
) -> int:
    """Copy chunk files to processed directory (for skip_llm mode).
    
    Args:
        chunks_dir: Directory containing chunk .md files.
        processed_dir: Directory to copy chunks to.
        base_name: Prefix for chunk filenames.
        log_callback: Optional logging callback.
        
    Returns:
        Number of files copied.
    """
    chunks_dir = Path(chunks_dir)
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    chunk_files = sorted(
        f for f in chunks_dir.iterdir()
        if f.is_file() and f.name.startswith(base_name) and f.suffix == ".md"
    )
    
    count = 0
    resolved_chunks_dir = chunks_dir.resolve()
    for chunk_path in chunk_files:
        resolved_chunk = chunk_path.resolve()
        if not str(resolved_chunk).startswith(str(resolved_chunks_dir)):
            logger.warning("Skipping chunk outside expected directory: %s", chunk_path)
            continue
        dest = processed_dir / chunk_path.name
        if not dest.exists():
            shutil.copy2(chunk_path, dest)
            count += 1
    
    return count
