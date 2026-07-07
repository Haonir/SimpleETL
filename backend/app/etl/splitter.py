"""Text splitting into chunks, saved directly as .md files.

No raw/ staging directory — chunks are saved as .md in the chunks/ directory.
Uses LangChain's RecursiveCharacterTextSplitter for intelligent text splitting.
"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from app.etl.extractor import extract_text
from app.settings import get_settings

logger = logging.getLogger(__name__)

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    RecursiveCharacterTextSplitter = None


def split_to_chunks(
    text: str,
    output_dir: str | Path,
    base_name: str = "chunk",
    chunk_size: int = 10000,
    chunk_overlap: int = 1500,
    log_callback: Optional[callable] = None,
) -> list[str]:
    """Split text into chunks and save as .md files.
    
    Creates output_dir if it doesn't exist. Each chunk is saved as
    {base_name}_{index:03d}.md.
    
    Args:
        text: Input text to split.
        output_dir: Directory to save chunk files.
        base_name: Prefix for chunk filenames.
        chunk_size: Maximum chunk size in characters.
        chunk_overlap: Overlap between consecutive chunks.
        log_callback: Optional logging callback.
        
    Returns:
        List of chunk file paths that were created.
        
    Raises:
        ValueError: If text is empty or whitespace-only.
        ImportError: If langchain-text-splitters is not installed.
    """
    if RecursiveCharacterTextSplitter is None:
        raise ImportError(
            "langchain-text-splitters is required. "
            "Install with: pip install langchain-text-splitters"
        )
    
    if not text.strip():
        raise ValueError("Input text is empty or contains only whitespace.")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    # Split text
    chunks = splitter.split_text(text)
    total_chunks = len(chunks)
    
    # Save chunks as .md files
    chunk_files: list[str] = []
    for i, chunk_text in enumerate(chunks):
        chunk_filename = f"{base_name}_{i:03d}.md"
        chunk_path = output_dir / chunk_filename
        
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(chunk_text)
        
        chunk_files.append(str(chunk_path))
    
    if log_callback:
        log_callback(f"Saved {total_chunks} chunks to {output_dir}")
    
    return chunk_files


def list_chunks(
    chunks_dir: str | Path,
    base_name: str = "chunk",
) -> list[str]:
    """List existing chunk files in a directory.
    
    Args:
        chunks_dir: Directory containing chunk files.
        base_name: Expected prefix for chunk filenames.
        
    Returns:
        Sorted list of chunk file paths.
    """
    chunks_dir = Path(chunks_dir)
    if not chunks_dir.exists():
        return []
    
    chunk_files = sorted(
        str(f) for f in chunks_dir.iterdir()
        if f.is_file() and f.name.startswith(base_name) and f.suffix == ".md"
    )
    return chunk_files


def get_chunk_count(chunks_dir: str | Path, base_name: str = "chunk") -> int:
    """Get the number of chunk files in a directory.
    
    Args:
        chunks_dir: Directory containing chunk files.
        base_name: Expected prefix for chunk filenames.
        
    Returns:
        Number of chunk files found.
    """
    return len(list_chunks(chunks_dir, base_name))


async def run_phase_prepare(
    pool: ThreadPoolExecutor,
    file_paths: list[str],
    flat_config: dict,
    log_cb: callable,
    stop_cb: callable,
    job_id: str,
) -> dict[str, dict] | None:
    """Parallel extract + split for all files.

    Args:
        pool: Thread pool executor.
        file_paths: List of file paths to process.
        flat_config: Flattened ETL configuration dict.
        log_cb: Logging callback (sync).
        stop_cb: Stop-check callback (returns True when stopped).
        job_id: Unique job identifier for directory layout.

    Returns:
        Registry dict mapping base_name -> {chunk_paths, chunks_dir, processed_dir, final_dir},
        or None if stopped.
    """
    loop = asyncio.get_event_loop()
    registry = {}
    futures = {}
    for file_path in file_paths:
        future = loop.run_in_executor(pool, _extract_and_split, file_path, flat_config, log_cb, job_id)
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
            log_cb(f"⚠️ Extract error: {e}", "error")
    return registry


def _extract_and_split(
    file_path: str,
    flat_config: dict,
    log_cb: callable,
    job_id: str,
) -> tuple[str, list[str], dict]:
    """Extract text + split into chunks (sync, runs in thread).

    Args:
        file_path: Path to the input file.
        flat_config: Flattened ETL configuration dict.
        log_cb: Logging callback (sync).
        job_id: Unique job identifier for directory layout.

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
        file_id = base_name
        item = fs.get_file(file_id)
        if item:
            base_name = Path(item.filename).stem
    except Exception:
        pass  # Fall back to UUID-based name

    settings = get_settings()
    # Temp files (chunks, processed) in jobs dir
    work_dir = settings.jobs_dir / job_id / base_name
    chunks_dir = str(work_dir / "chunks")
    processed_dir = str(work_dir / "processed")
    # Final output in output dir
    final_dir = str(settings.output_dir / job_id / base_name)

    # Step 1: Extract text (sync)
    text = extract_text(file_path, log_cb)

    if not text.strip():
        raise Exception("File is empty or contains no readable text.")

    # Step 2: Split into chunks (sync) — or skip chunking
    if flat_config.get("skip_chunking", False):
        log_cb("⏭️ Chunking skipped — processing file as a whole.")
        chunks_dir_path = Path(chunks_dir)
        chunks_dir_path.mkdir(parents=True, exist_ok=True)
        single_chunk_path = chunks_dir_path / f"{base_name}_000.md"
        with open(single_chunk_path, "w", encoding="utf-8") as f:
            f.write(text)
        chunk_files = [str(single_chunk_path)]
    else:
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
