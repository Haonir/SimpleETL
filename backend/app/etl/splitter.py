"""Text splitting into chunks, saved directly as .md files.

No raw/ staging directory — chunks are saved as .md in the chunks/ directory.
Uses LangChain's RecursiveCharacterTextSplitter for intelligent text splitting.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

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
    
    if log_callback:
        log_callback(f"Text split into {total_chunks} chunks.")
    
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
