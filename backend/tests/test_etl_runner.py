"""Unit tests for etl.runner module — three-phase parallel pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.etl.runner import (
    _get_output_dir,
    run_etl_job,
)
from app.etl.splitter import _extract_and_split, run_phase_prepare
from app.etl.llm_processor import run_phase_llm
from app.etl.packer import run_phase_pack
from app.schemas.job import JobStatus


@pytest.fixture
def mock_ws_manager():
    """Mock WebSocket connection manager."""
    manager = AsyncMock()
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def mock_job_service():
    """Mock JobService."""
    service = MagicMock()
    service.is_stopped = MagicMock(return_value=False)
    return service


@pytest.fixture
def event_loop():
    """Get the running event loop."""
    return asyncio.get_event_loop()


@pytest.fixture
def temp_dir(tmp_path: Path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_text_file(temp_dir: Path):
    """Create a sample text file with enough content for multiple chunks."""
    text = "word " * 2000  # ~10000 chars, should produce multiple chunks at chunk_size=5000
    path = temp_dir / "sample.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.fixture
def sample_docx_file(temp_dir: Path):
    """Create a sample docx file."""
    try:
        from docx import Document

        doc = Document()
        for i in range(10):
            doc.add_paragraph(f"Paragraph {i}: This is test content for document processing.")
        path = temp_dir / "document.docx"
        doc.save(str(path))
        return str(path)
    except ImportError:
        pytest.skip("python-docx not installed")


@pytest.fixture
def flat_config():
    """Default flattened config."""
    return {
        "model": "llama3",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "chunk_size": 5000,
        "chunk_overlap": 500,
        "max_workers": 2,
        "output_format": "spr",
        "prompt": "Analyze this text.",
        "skip_llm": False,
        "cleanup": True,
    }


# ── _get_output_dir tests ────────────────────────────────────────────────────


class TestGetOutputDir:
    """Tests for _get_output_dir helper."""

    def test_default_config(self):
        """Uses default output base when config has no output_dir."""
        result = _get_output_dir("/path/to/file.txt", "job-123")
        assert "file" in result  # stem of file.txt

    def test_custom_output_dir(self):
        """Output dir includes job_id and base_name."""
        result = _get_output_dir("/path/to/document.pdf", "job-456")
        assert "document" in result

    def test_stem_from_path(self):
        """Extracts stem from file path."""
        result = _get_output_dir("/data/report_2024.md", "job-789")
        assert "report_2024" in result


# ── _extract_and_split tests ─────────────────────────────────────────────────


class TestExtractAndSplit:
    """Tests for _extract_and_split sync function."""

    def test_basic_extraction(self, temp_dir: Path):
        """Extracts text and splits into chunks."""
        text = "word " * 2000
        file_path = str(temp_dir / "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        flat_config = {"chunk_size": 5000, "chunk_overlap": 500}
        log_cb = MagicMock()

        base_name, chunk_paths, dirs = _extract_and_split(file_path, flat_config, log_cb, "test-job")

        assert base_name == "test"
        assert len(chunk_paths) > 0
        assert all(p.endswith(".md") for p in chunk_paths)
        assert dirs["chunks_dir"].endswith("chunks")
        assert dirs["processed_dir"].endswith("processed")
        assert "test" in dirs["final_dir"]  # base_name is in the path

    def test_empty_file_raises(self, temp_dir: Path):
        """Empty file raises Exception."""
        empty_path = str(temp_dir / "empty.txt")
        with open(empty_path, "w", encoding="utf-8") as f:
            f.write("")

        flat_config = {"chunk_size": 5000}
        log_cb = MagicMock()

        with pytest.raises(Exception, match="empty"):
            _extract_and_split(empty_path, flat_config, log_cb, "test-job")

    def test_log_callback_called(self, temp_dir: Path):
        """Log callback is called during extraction and splitting."""
        text = "word " * 1000
        file_path = str(temp_dir / "log_test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        flat_config = {"chunk_size": 5000}
        log_cb = MagicMock()

        _extract_and_split(file_path, flat_config, log_cb, "test-job")

        assert log_cb.call_count >= 1  # at least extract + split messages (may be only 1 chunk)


# ── _phase_prepare tests ─────────────────────────────────────────────────────


class TestPhasePrepare:
    """Tests for Phase 1 — parallel extract & split."""

    @pytest.mark.asyncio
    async def test_single_file(self, temp_dir: Path, flat_config):
        """Processes a single file and returns registry with one entry."""
        text = "word " * 2000
        file_path = str(temp_dir / "single.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        log_cb = MagicMock()
        stop_cb = MagicMock(return_value=False)

        pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        try:
            registry = await run_phase_prepare(
                pool=pool,
                file_paths=[file_path],
                flat_config=flat_config,
                log_cb=log_cb,
                stop_cb=stop_cb,
                job_id="test-job",
            )

            assert len(registry) == 1
            base_name = list(registry.keys())[0]
            assert base_name == "single"
            assert "chunk_paths" in registry[base_name]
            assert len(registry[base_name]["chunk_paths"]) > 0
            assert "chunks_dir" in registry[base_name]
            assert "processed_dir" in registry[base_name]
            assert "final_dir" in registry[base_name]
        finally:
            pool.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_multiple_files(self, temp_dir: Path, flat_config):
        """Processes multiple files and returns registry with all entries."""
        file_paths = []
        for i in range(3):
            text = f"text {i} " * 500
            path = str(temp_dir / f"file_{i}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            file_paths.append(path)

        log_cb = MagicMock()
        stop_cb = MagicMock(return_value=False)

        pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        try:
            registry = await run_phase_prepare(
                pool=pool,
                file_paths=file_paths,
                flat_config=flat_config,
                log_cb=log_cb,
                stop_cb=stop_cb,
                job_id="test-job",
            )

            assert len(registry) == 3
            for i in range(3):
                base_name = f"file_{i}"
                assert base_name in registry
                assert len(registry[base_name]["chunk_paths"]) > 0
        finally:
            pool.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_returns_none_when_stopped(self, temp_dir: Path, flat_config):
        """Returns None when stop_cb returns True during processing."""
        text = "word " * 2000
        file_path = str(temp_dir / "stop_test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        log_cb = MagicMock()
        stop_cb = MagicMock(return_value=True)  # immediately stopped

        pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        try:
            registry = await run_phase_prepare(
                pool=pool,
                file_paths=[file_path],
                flat_config=flat_config,
                log_cb=log_cb,
                stop_cb=stop_cb,
                job_id="test-job",
            )

            assert registry is None
        finally:
            pool.shutdown(wait=False)


# ── _phase_llm tests ─────────────────────────────────────────────────────────


class TestPhaseLlm:
    """Tests for Phase 2 — parallel LLM processing."""

    def _create_chunk_files(self, chunks_dir: str, base_name: str, count: int = 3):
        """Create dummy chunk files for testing."""
        Path(chunks_dir).mkdir(parents=True, exist_ok=True)
        paths = []
        for i in range(count):
            chunk_path = Path(chunks_dir) / f"{base_name}_{i:03d}.md"
            chunk_path.write_text(f"chunk {i} content")
            paths.append(chunk_path)
        return paths

    @pytest.mark.asyncio
    async def test_processes_all_chunks(self, tmp_path):
        """Phase 2 processes all chunks in parallel."""
        base_name = "test"
        chunks_dir = str(tmp_path / "chunks")
        processed_dir = str(tmp_path / "processed")
        final_dir = str(tmp_path / "final")

        # Create chunk files
        Path(chunks_dir).mkdir(parents=True, exist_ok=True)
        for i in range(3):
            (Path(chunks_dir) / f"{base_name}_{i:03d}.md").write_text(f"chunk {i}")

        registry = {
            base_name: {
                "chunk_paths": [Path(chunks_dir) / f"{base_name}_{i:03d}.md" for i in range(3)],
                "chunks_dir": chunks_dir,
                "processed_dir": processed_dir,
                "final_dir": final_dir,
            }
        }
        config = {"base_url": "http://test", "api_key": "test", "model": "test", "prompt": "test"}

        # Mock OpenAI to write processed files
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="processed content"))]

        with patch("app.etl.llm_processor.OpenAI", return_value=mock_openai_client):
            pool = ThreadPoolExecutor(max_workers=2)
            try:
                result, errors = await run_phase_llm(pool, registry, config, lambda m, level="info": None, lambda: False, lambda *a: None)
            finally:
                pool.shutdown(wait=False)

        assert result is True
        assert Path(processed_dir).exists()
        for i in range(3):
            assert (Path(processed_dir) / f"{base_name}_{i:03d}.md").exists()

    @pytest.mark.asyncio
    async def test_skips_already_processed(self, tmp_path):
        """Skips chunks that already have a processed file."""
        base_name = "test"
        chunks_dir = str(tmp_path / "chunks2")
        processed_dir = str(tmp_path / "processed2")

        Path(chunks_dir).mkdir(parents=True, exist_ok=True)
        (Path(chunks_dir) / f"{base_name}_001.md").write_text("chunk 1", encoding="utf-8")
        Path(processed_dir).mkdir(parents=True, exist_ok=True)
        (Path(processed_dir) / f"{base_name}_001.md").write_text("Already done", encoding="utf-8")

        registry = {
            base_name: {
                "chunk_paths": [Path(chunks_dir) / f"{base_name}_{i:03d}.md" for i in range(1)],
                "chunks_dir": chunks_dir,
                "processed_dir": processed_dir,
                "final_dir": str(tmp_path / "final2"),
            }
        }
        config = {"base_url": "http://test", "api_key": "test", "model": "test", "prompt": "test"}

        log_cb = MagicMock()
        stop_cb = MagicMock(return_value=False)
        progress_cb = MagicMock()

        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Should not be called"))]

        with patch("app.etl.llm_processor.OpenAI", return_value=mock_openai_client):
            pool = ThreadPoolExecutor(max_workers=2)
            try:
                result, errors = await run_phase_llm(pool, registry, config, log_cb, stop_cb, progress_cb)
            finally:
                pool.shutdown(wait=False)

        assert result is True
        # The processed file should remain unchanged (skip)
        content = (Path(processed_dir) / f"{base_name}_001.md").read_text(encoding="utf-8")
        assert content == "Already done"

    @pytest.mark.asyncio
    async def test_fail_continue_on_llm_error(self, tmp_path):
        """Continues processing other chunks when one chunk fails."""
        base_name = "test"
        chunks_dir = str(tmp_path / "chunks3")
        processed_dir = str(tmp_path / "processed3")

        Path(chunks_dir).mkdir(parents=True, exist_ok=True)
        for i in range(2):
            (Path(chunks_dir) / f"{base_name}_{i:03d}.md").write_text(f"chunk {i}")

        registry = {
            base_name: {
                "chunk_paths": [Path(chunks_dir) / f"{base_name}_{i:03d}.md" for i in range(2)],
                "chunks_dir": chunks_dir,
                "processed_dir": processed_dir,
                "final_dir": str(tmp_path / "final3"),
            }
        }
        config = {"base_url": "http://test", "api_key": "test", "model": "test", "prompt": "test"}

        log_cb = MagicMock()
        stop_cb = MagicMock(return_value=False)
        progress_cb = MagicMock()

        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success"))]

        with patch("app.etl.llm_processor.OpenAI", return_value=mock_openai_client):
            # First call raises, second succeeds
            error_func = MagicMock(side_effect=Exception("LLM API error"))
            mock_openai_client.chat.completions.create.side_effect = [error_func, mock_response]

            pool = ThreadPoolExecutor(max_workers=2)
            try:
                result, errors = await run_phase_llm(pool, registry, config, log_cb, stop_cb, progress_cb)
            finally:
                pool.shutdown(wait=False)

        assert result is True  # fail-continue: still returns True
        assert log_cb.called  # error was logged
        # Second chunk should have been processed
        path = Path(processed_dir) / f"{base_name}_001.md"
        assert path.exists()

    @pytest.mark.asyncio
    async def test_returns_false_when_stopped(self, tmp_path):
        """Returns False when stop_cb returns True during processing."""
        base_name = "test"
        chunks_dir = str(tmp_path / "chunks4")
        processed_dir = str(tmp_path / "processed4")

        Path(chunks_dir).mkdir(parents=True, exist_ok=True)
        (Path(chunks_dir) / f"{base_name}_001.md").write_text("chunk 1", encoding="utf-8")

        registry = {
            base_name: {
                "chunk_paths": [Path(chunks_dir) / f"{base_name}_{i:03d}.md" for i in range(1)],
                "chunks_dir": chunks_dir,
                "processed_dir": processed_dir,
                "final_dir": str(tmp_path / "final4"),
            }
        }
        config = {"base_url": "http://test", "api_key": "test", "model": "test", "prompt": "test"}

        log_cb = MagicMock()
        stop_cb = MagicMock(return_value=True)  # immediately stopped
        progress_cb = MagicMock()

        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Should not be called"))]

        with patch("app.etl.llm_processor.OpenAI", return_value=mock_openai_client):
            pool = ThreadPoolExecutor(max_workers=2)
            try:
                result, errors = await run_phase_llm(pool, registry, config, log_cb, stop_cb, progress_cb)
            finally:
                pool.shutdown(wait=False)

        assert result is False


# ── _phase_pack tests ────────────────────────────────────────────────────────


class TestPhasePack:
    """Tests for Phase 3 — parallel packing."""

    @pytest.mark.asyncio
    async def test_packs_outputs(self, temp_dir: Path, flat_config):
        """Packs processed files into final output format."""
        # Create a mock processed directory with one file
        processed_dir = str(temp_dir / "proc_pack")
        final_dir = str(temp_dir / "final_pack")
        os.makedirs(processed_dir)

        proc_file = Path(processed_dir) / "test_005.md"
        proc_file.write_text("---\ntitle: Test Document\n---\n# Hello\nWorld", encoding="utf-8")

        registry = {
            "test": {
                "chunk_paths": [],
                "chunks_dir": str(temp_dir / "chunks_pack"),
                "processed_dir": processed_dir,
                "final_dir": final_dir,
            }
        }

        log_cb = MagicMock()

        pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        try:
            await run_phase_pack(
                pool=pool,
                registry=registry,
                flat_config=flat_config,
                log_cb=log_cb,
            )

            # Output file should exist
            output_files = list(Path(final_dir).glob("*.md"))
            assert len(output_files) >= 1
        finally:
            pool.shutdown(wait=False)


# ── run_etl_job integration tests ────────────────────────────────────────────


class TestRunEtlJob:
    """Integration tests for the full three-phase pipeline."""

    @pytest.fixture(autouse=True)
    def mock_settings(self, tmp_path):
        """Mock get_settings to use temp directory so output dirs are created."""
        mock = MagicMock()
        mock.output_dir = tmp_path / "output"
        mock.jobs_dir = tmp_path / "jobs"
        mock.max_workers_limit = 0    # disable capping for integration tests
        mock.chunk_size_limit = 0     # disable capping for integration tests
        with patch("app.etl.runner.get_settings", return_value=mock):
            with patch("app.etl.splitter.get_settings", return_value=mock):
                with patch("app.services.job_service.get_job_service") as mock_gjs:
                    mock_gjs.return_value = MagicMock()
                    yield mock

    @pytest.mark.asyncio
    async def test_full_pipeline_single_file(self, temp_dir: Path, mock_ws_manager, mock_job_service):
        """Full pipeline with a single text file — all phases complete successfully."""
        # Create input file
        text = "word " * 2000
        file_path = str(temp_dir / "integration.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        config = {
            "llm": {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
            "processing": {"chunk_size": 5000, "chunk_overlap": 500},
            "prompt_text": "Analyze this text.",
            "output_format": "spr",
            "output_dir": str(temp_dir / "output"),
        }

        log_cb = MagicMock()
        progress_cb = MagicMock()
        stop_cb = MagicMock(return_value=False)

        # Mock openai in the llm_processor module
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "LLM processed output"
        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch("app.etl.llm_processor.OpenAI", return_value=mock_openai_client):
            await run_etl_job(
                job_id="test-job-001",
                file_paths=[file_path],
                config=config,
                job_service=mock_job_service,
                ws_manager=mock_ws_manager,
            )

        # Verify job status was updated to completed
        mock_job_service.update_status.assert_called()
        calls = mock_job_service.update_status.call_args_list
        statuses = [c[0][1] for c in calls if len(c[0]) > 1]
        assert JobStatus.running in statuses
        assert JobStatus.completed in statuses

        # Verify output files were created
        output_dir = temp_dir / "output" / "test-job-001" / "integration"
        assert output_dir.exists()
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) >= 1

        # Verify done message was broadcast (last call)
        last_call = mock_ws_manager.broadcast.call_args_list[-1]
        assert last_call[0][0] == "test-job-001"
        assert last_call[0][1]["type"] == "done"
        call_args = mock_ws_manager.broadcast.call_args[0]
        assert call_args[0] == "test-job-001"
        msg = call_args[1]
        assert msg["type"] == "done"

    @pytest.mark.asyncio
    async def test_empty_file_list(self, temp_dir: Path, mock_ws_manager, mock_job_service):
        """Empty file list completes immediately without processing."""
        config = {"llm": {}, "processing": {}}

        await run_etl_job(
            job_id="test-job-empty",
            file_paths=[],
            config=config,
            job_service=mock_job_service,
            ws_manager=mock_ws_manager,
        )

        # Should transition to completed
        mock_job_service.update_status.assert_called()
        statuses = [c[0][1] for c in mock_job_service.update_status.call_args_list if len(c[0]) > 1]
        assert JobStatus.completed in statuses

    @pytest.mark.asyncio
    async def test_multiple_files_pipeline(self, temp_dir: Path, mock_ws_manager, mock_job_service):
        """Full pipeline with multiple files."""
        file_paths = []
        for i in range(2):
            text = f"text {i} " * 1000
            path = str(temp_dir / f"multi_{i}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            file_paths.append(path)

        config = {
            "llm": {"model": "gpt4", "base_url": "http://localhost:1234/v1", "api_key": "key"},
            "processing": {"chunk_size": 5000, "chunk_overlap": 500},
            "prompt_text": "Summarize.",
            "output_format": "markdown",
            "output_dir": str(temp_dir / "output"),
        }

        log_cb = MagicMock()
        progress_cb = MagicMock()
        stop_cb = MagicMock(return_value=False)

        # Mock openai in the llm_processor module
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Summary"
        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch("app.etl.llm_processor.OpenAI", return_value=mock_openai_client):
            await run_etl_job(
                job_id="test-job-multi",
                file_paths=file_paths,
                config=config,
                job_service=mock_job_service,
                ws_manager=mock_ws_manager,
            )

        # Verify all files produced output
        for i in range(2):
            base_name = f"multi_{i}"
            final_dir = temp_dir / "output" / "test-job-multi" / base_name
            assert final_dir.exists(), f"Final dir missing for {base_name}: {final_dir}"
            outputs = list(final_dir.glob("*.md"))
            assert len(outputs) >= 1, f"Expected at least 1 output for {base_name}, got {len(outputs)}"

    @pytest.mark.asyncio
    async def test_stop_during_pipeline(self, temp_dir: Path, mock_ws_manager, mock_job_service):
        """Pipeline stops when user requests stop."""
        text = "word " * 2000
        file_path = str(temp_dir / "stop_integration.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        config = {
            "llm": {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
            "processing": {"chunk_size": 5000, "chunk_overlap": 500},
            "prompt_text": "Analyze.",
            "output_dir": str(temp_dir / "output"),
        }

        stop_count = {"n": 0}
        def mock_is_stopped(job_id):
            stop_count["n"] += 1
            return stop_count["n"] > 3

        mock_job_service.is_stopped = mock_is_stopped

        # Mock openai in the llm_processor module
        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Should not be called"
        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch("app.etl.llm_processor.OpenAI", return_value=mock_openai_client):
            await run_etl_job(
                job_id="test-job-stop",
                file_paths=[file_path],
                config=config,
                job_service=mock_job_service,
                ws_manager=mock_ws_manager,
            )

        # Should transition to stopped status
        mock_job_service.update_status.assert_called()
        statuses = [c[0][1] for c in mock_job_service.update_status.call_args_list if len(c[0]) > 1]
        assert JobStatus.stopped in statuses
