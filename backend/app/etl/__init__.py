"""ETL pipeline modules for SimpleETL backend.

Modular async architecture — no imports from core/ (deprecated).

Modules:
    - extractor: Text and image extraction from documents
    - splitter: Text splitting into chunks
    - llm_processor: LLM analysis of chunks
    - packer: Output formatting (spr/frontmatter/markdown/html)
    - image_utils: Image utilities
    - runner: Async entry point for ETL jobs
    - callbacks: WebSocket callback bridge
"""

from app.etl.extractor import extract_text
from app.etl.splitter import split_to_chunks, list_chunks, run_phase_prepare
from app.etl.llm_processor import run_phase_llm, copy_chunks_to_processed
from app.etl.packer import pack_outputs, run_phase_pack
from app.etl.runner import run_etl_job
from app.etl.callbacks import create_callbacks

__all__ = [
    "extract_text",
    "split_to_chunks",
    "list_chunks",
    "run_phase_prepare",
    "run_phase_llm",
    "copy_chunks_to_processed",
    "pack_outputs",
    "run_phase_pack",
    "run_etl_job",
    "create_callbacks",
]
