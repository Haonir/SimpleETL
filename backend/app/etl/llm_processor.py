"""LLM processing of text chunks via OpenAI-compatible API.

Reads chunk files from chunks/ directory, processes them through LLM,
and saves results to processed/ directory.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def process_with_llm(
    chunks_dir: str | Path,
    processed_dir: str | Path,
    base_name: str = "chunk",
    model: str = "llama3",
    base_url: str = "http://localhost:11434/v1",
    api_key: str = "ollama",
    prompt: str = "Analyze this text and create a structured summary.",
    log_callback: Optional[callable] = None,
    stop_check_callback: Optional[callable] = None,
) -> bool:
    """Process all chunk files through LLM and save results.
    
    Reads from chunks_dir, writes to processed_dir.
    Skips chunks that already have corresponding processed files.
    
    Args:
        chunks_dir: Directory containing chunk .md files.
        processed_dir: Directory to save processed .md files.
        base_name: Prefix for chunk filenames.
        model: LLM model name.
        base_url: OpenAI-compatible API base URL.
        api_key: API key for the LLM provider.
        prompt: System prompt for LLM analysis.
        log_callback: Optional logging callback.
        stop_check_callback: Optional stop check callback (returns True to stop).
        
    Returns:
        True if all chunks processed successfully, False if stopped or failed.
        
    Raises:
        ImportError: If openai package is not installed.
    """
    if OpenAI is None:
        raise ImportError(
            "openai package is required for LLM processing. "
            "Install with: pip install openai"
        )
    
    chunks_dir = Path(chunks_dir)
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all chunk files
    chunk_files = sorted(
        f for f in chunks_dir.iterdir()
        if f.is_file() and f.name.startswith(base_name) and f.suffix == ".md"
    )
    
    if not chunk_files:
        if log_callback:
            log_callback("⚠️ No chunk files found to process.")
        return True
    
    total_chunks = len(chunk_files)
    
    if log_callback:
        log_callback(f"--- LLM Processing: {total_chunks} chunks ---")
    
    # Initialize LLM client
    client = OpenAI(base_url=base_url, api_key=api_key)
    
    for idx, chunk_path in enumerate(chunk_files):
        # Check stop flag
        if stop_check_callback and stop_check_callback():
            if log_callback:
                log_callback("⚠️ LLM processing stopped by user.", "warning")
            return False
        
        processed_path = processed_dir / chunk_path.name
        
        # Skip if already processed
        if processed_path.exists():
            if log_callback:
                log_callback(f"[{idx+1}/{total_chunks}] {chunk_path.name} already processed, skipping.")
            continue
        
        # Read chunk
        with open(chunk_path, "r", encoding="utf-8") as f:
            chunk_text = f.read()
        
        if log_callback:
            log_callback(f"[{idx+1}/{total_chunks}] Processing {chunk_path.name} with {model}...")
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Process this text:\n\n{chunk_text}"},
                ],
                temperature=0.2,
            )
            llm_output = response.choices[0].message.content
            
            # Save processed output
            with open(processed_path, "w", encoding="utf-8") as f:
                f.write(llm_output)
            
            if log_callback:
                log_callback(f"[{idx+1}/{total_chunks}] ✅ {chunk_path.name} processed.")
                
        except Exception as e:
            error_msg = f"LLM error on chunk {chunk_path.name}: {e}"
            if log_callback:
                log_callback(f"💥 {error_msg}")
            raise Exception(error_msg)
    
    if log_callback:
        log_callback(f"--- LLM Processing complete: {total_chunks} chunks ---")
    
    return True


def copy_chunks_to_processed(
    chunks_dir: str | Path,
    processed_dir: str | Path,
    base_name: str = "chunk",
    log_callback: Optional[callable] = None,
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
    for chunk_path in chunk_files:
        dest = processed_dir / chunk_path.name
        if not dest.exists():
            shutil.copy2(chunk_path, dest)
            count += 1
    
    if log_callback:
        log_callback(f"Copied {count} chunks to processed directory.")
    
    return count
