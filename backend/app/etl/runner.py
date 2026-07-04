"""Async ETL runner — orchestrates all pipeline modules.

Entry point for ETL job execution. Runs sync modules in thread pool executor,
bridges callbacks to WebSocket broadcast via the callbacks module.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from app.etl.callbacks import create_callbacks
from app.schemas.websocket import WSDoneMessage, WSErrorMessage
from app.etl.extractor import extract_all, extract_text
from app.etl.llm_processor import copy_chunks_to_processed, process_with_llm
from app.etl.packer import pack_outputs
from app.etl.splitter import split_to_chunks

if TYPE_CHECKING:
    from app.schemas.job import JobStatus
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
    
    This is the main entry point called by the API when a job is created.
    It runs the sync pipeline in a thread pool and broadcasts progress via WS.
    
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
    callbacks = create_callbacks(ws_manager, job_id, loop, job_service)
    progress_cb = callbacks["progress"]
    log_cb = callbacks["log"]
    stop_cb = callbacks["stop"]
    
    try:
        # Transition job to running
        from app.schemas.job import JobStatus
        job_service.update_status(job_id, JobStatus.running)
        
        log_cb(f"🚀 Starting ETL job with {len(file_paths)} file(s)...")
        
        # Process each file
        total_files = len(file_paths)
        all_success = True
        
        for file_idx, file_path in enumerate(file_paths):
            if stop_cb():
                log_cb("⚠️ Job stopped by user.")
                job_service.update_status(job_id, JobStatus.stopped)
                return
            
            file_name = os.path.basename(file_path)
            log_cb(f"====== 🚀 FILE [{file_idx+1}/{total_files}]: {file_name} ======")
            
            try:
                success = await _process_single_file(
                    file_path=file_path,
                    config=config,
                    file_idx=file_idx,
                    total_files=total_files,
                    progress_cb=progress_cb,
                    log_cb=log_cb,
                    stop_cb=stop_cb,
                )
                
                if not success:
                    all_success = False
                    log_cb(f"🛑 [{file_idx+1}/{total_files}] {file_name} — stopped.")
                else:
                    log_cb(f"====== ✅ FILE DONE [{file_idx+1}/{total_files}]: {file_name} ======\n")
                    
            except Exception as e:
                all_success = False
                log_cb(f"💥 {file_name}: {e}\n⏭️ Moving to next file...\n")
                logger.exception("Error processing file %s", file_path)
        
        # Final status
        if all_success and not stop_cb():
            job_service.update_status(job_id, JobStatus.completed)
            log_cb("🎉 ETL job completed successfully!")
            
            # Broadcast done message
            await ws_manager.broadcast(job_id, WSDoneMessage(
                type="done",
                job_id=job_id,
                output_dir=_get_output_dir(file_paths[0], config) if file_paths else "",
            ).model_dump())
        elif stop_cb():
            job_service.update_status(job_id, JobStatus.stopped)
            log_cb("⚠️ ETL job stopped by user.")
        else:
            job_service.update_status(job_id, JobStatus.completed)
            log_cb("⚠️ ETL job completed with errors.")
            
    except Exception as e:
        logger.exception("Critical error in ETL job %s", job_id)
        job_service.update_status(job_id, JobStatus.error, error_message=str(e))
        
        await ws_manager.broadcast(job_id, WSErrorMessage(
            type="error",
            job_id=job_id,
            message=str(e),
        ).model_dump())


async def _process_single_file(
    file_path: str,
    config: dict,
    file_idx: int,
    total_files: int,
    progress_cb: callable,
    log_cb: callable,
    stop_cb: callable,
) -> bool:
    """Process a single file through the ETL pipeline.
    
    Pipeline: extract → chunks/*.md → (LLM) → processed/*.md → pack → final/
    
    Returns:
        True if successful, False if stopped.
    """
    loop = asyncio.get_event_loop()
    
    # Build file-specific config
    file_name = os.path.basename(file_path)
    base_name = Path(file_name).stem
    
    # Determine output directory
    output_base = config.get("output_dir", "/tmp/SimpleETL/output")
    file_output_dir = os.path.join(output_base, base_name)
    
    chunks_dir = os.path.join(file_output_dir, "chunks")
    processed_dir = os.path.join(file_output_dir, "processed")
    final_dir = os.path.join(file_output_dir, "final")
    
    # Step 1: Extract text (runs in thread pool)
    log_cb("--- Step 1: Extracting text ---")
    
    def _extract():
        return extract_text(file_path, log_cb)
    
    text = await loop.run_in_executor(None, _extract)
    
    if not text.strip():
        raise Exception("File is empty or contains no readable text.")
    
    # Flatten nested config: frontend sends {"llm": {...}, "processing": {...}, "prompt_text": "..."}
    # but pipeline expects flat keys like "model", "base_url", etc.
    llm_cfg = config.get("llm", {})
    proc_cfg = config.get("processing", {})
    flat_config = {**proc_cfg, **llm_cfg}
    if "prompt_text" in config:
        flat_config.setdefault("prompt", config["prompt_text"])

    # Step 2: Split into chunks
    log_cb("--- Step 2: Splitting into chunks ---")
    
    chunk_size = flat_config.get("chunk_size", 10000)
    chunk_overlap = flat_config.get("chunk_overlap", 1500)
    
    def _split():
        return split_to_chunks(
            text=text,
            output_dir=chunks_dir,
            base_name=base_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            log_callback=log_cb,
        )
    
    chunk_files = await loop.run_in_executor(None, _split)
    
    if stop_cb():
        return False
    
    # Step 3: LLM processing (optional)
    skip_llm = flat_config.get("skip_llm", False)
    
    if skip_llm:
        log_cb("--- Step 3: LLM skipped (copying chunks) ---")
        def _copy():
            return copy_chunks_to_processed(chunks_dir, processed_dir, base_name, log_cb)
        await loop.run_in_executor(None, _copy)
    else:
        log_cb("--- Step 3: LLM processing ---")
        
        def _llm():
            return process_with_llm(
                chunks_dir=chunks_dir,
                processed_dir=processed_dir,
                base_name=base_name,
                model=flat_config.get("model", "llama3"),
                base_url=flat_config.get("base_url", "http://localhost:11434/v1"),
                api_key=flat_config.get("api_key", "ollama"),
                prompt=flat_config.get("prompt", "Analyze this text."),
                log_callback=log_cb,
                stop_check_callback=stop_cb,
            )
        
        success = await loop.run_in_executor(None, _llm)
        if not success:
            return False
    
    if stop_cb():
        return False
    
    # Step 4: Pack outputs
    log_cb("--- Step 4: Packing outputs ---")
    output_format = flat_config.get("output_format", "spr")
    
    def _pack():
        return pack_outputs(
            processed_dir=processed_dir,
            output_dir=final_dir,
            base_name=base_name,
            output_format=output_format,
            log_callback=log_cb,
        )
    
    output_files = await loop.run_in_executor(None, _pack)
    
    # Step 5: Cleanup (optional)
    if flat_config.get("cleanup", True):
        log_cb("--- Step 5: Cleanup ---")
        import shutil
        for d in [chunks_dir, processed_dir]:
            if os.path.exists(d):
                try:
                    shutil.rmtree(d)
                except Exception as e:
                    log_cb(f"⚠️ Cleanup warning: {e}")
    
    # Update progress to 100%
    file_weight = 100 / total_files
    global_pct = int((file_idx + 1) * file_weight)
    progress_cb(100, global_pct, file_idx)
    
    return True


def _get_output_dir(file_path: str, config: dict) -> str:
    """Get the output directory for a file."""
    file_name = os.path.basename(file_path)
    base_name = Path(file_name).stem
    output_base = config.get("output_dir", "/tmp/SimpleETL/output")
    return os.path.join(output_base, base_name, "final")
