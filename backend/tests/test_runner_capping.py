"""Unit tests for ETL runner capping logic (max_workers and chunk_size limits)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.etl.runner import run_etl_job


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


@pytest.mark.asyncio
async def test_max_workers_capped_when_user_requests_higher(
    tmp_path, mock_ws_manager, mock_job_service
):
    """When flat_config has max_workers=8 and settings.max_workers_limit=4, result is 4."""
    text = "word " * 2000
    file_path = str(tmp_path / "cap_test.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    config = {
        "llm": {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
        "processing": {"chunk_size": 5000, "chunk_overlap": 500, "max_workers": 8},
        "prompt_text": "Analyze this text.",
        "output_format": "spr",
    }

    mock_settings = MagicMock()
    mock_settings.max_workers_limit = 4
    mock_settings.chunk_size_limit = 10_000
    mock_settings.output_dir = tmp_path / "output"
    mock_settings.jobs_dir = tmp_path / "jobs"

    with patch("app.etl.runner.get_settings", return_value=mock_settings):
        # Mock _extract_and_split and run_phase_llm to avoid real I/O
        with patch("app.etl.runner._extract_and_split") as mock_extract:
            mock_extract.return_value = ("cap_test", [], {})
            with patch("app.etl.runner.run_phase_llm", return_value=(True, set())):
                # Capture ThreadPoolExecutor creation to verify capped value
                captured_executor_kwargs = {}

                def capture_kwarg(*args, **kwargs):
                    captured_executor_kwargs.update(kwargs)
                    return _create_pool(*args, **kwargs)

                with patch("app.etl.runner.ThreadPoolExecutor", side_effect=capture_kwarg):
                    await run_etl_job(
                        job_id="test-cap-workers-high",
                        file_paths=[file_path],
                        config=config,
                        job_service=mock_job_service,
                        ws_manager=mock_ws_manager,
                    )

    # Verify the capped value was applied (8 -> 4)
    assert captured_executor_kwargs["max_workers"] == 4


@pytest.mark.asyncio
async def test_max_workers_not_capped_when_user_requests_lower(
    tmp_path, mock_ws_manager, mock_job_service
):
    """When flat_config has max_workers=2 and settings.max_workers_limit=4, result is 2."""
    text = "word " * 2000
    file_path = str(tmp_path / "cap_test.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    config = {
        "llm": {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
        "processing": {"chunk_size": 5000, "chunk_overlap": 500, "max_workers": 2},
        "prompt_text": "Analyze this text.",
        "output_format": "spr",
    }

    mock_settings = MagicMock()
    mock_settings.max_workers_limit = 4
    mock_settings.chunk_size_limit = 10_000
    mock_settings.output_dir = tmp_path / "output"
    mock_settings.jobs_dir = tmp_path / "jobs"

    with patch("app.etl.runner.get_settings", return_value=mock_settings):
        # Mock _extract_and_split and run_phase_llm to avoid real I/O
        with patch("app.etl.runner._extract_and_split") as mock_extract:
            mock_extract.return_value = ("cap_test", [], {})
            with patch("app.etl.runner.run_phase_llm", return_value=(True, set())):
                captured_executor_kwargs = {}

                def capture_kwarg(*args, **kwargs):
                    captured_executor_kwargs.update(kwargs)
                    return _create_pool(*args, **kwargs)

                with patch("app.etl.runner.ThreadPoolExecutor", side_effect=capture_kwarg):
                    await run_etl_job(
                        job_id="test-cap-workers-low",
                        file_paths=[file_path],
                        config=config,
                        job_service=mock_job_service,
                        ws_manager=mock_ws_manager,
                    )

    # Verify the value was not capped (2 stays 2)
    assert captured_executor_kwargs["max_workers"] == 2


@pytest.mark.asyncio
async def test_chunk_size_capped_when_user_requests_higher(
    tmp_path, mock_ws_manager, mock_job_service
):
    """When flat_config has chunk_size=50000 and settings.chunk_size_limit=10000, result is 10000."""
    text = "word " * 2000
    file_path = str(tmp_path / "cap_test.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    config = {
        "llm": {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
        "processing": {"chunk_size": 50_000, "chunk_overlap": 500, "max_workers": 2},
        "prompt_text": "Analyze this text.",
        "output_format": "spr",
    }

    mock_settings = MagicMock()
    mock_settings.max_workers_limit = 4
    mock_settings.chunk_size_limit = 10_000
    mock_settings.output_dir = tmp_path / "output"
    mock_settings.jobs_dir = tmp_path / "jobs"

    with patch("app.etl.runner.get_settings", return_value=mock_settings):
        # Mock _extract_and_split and run_phase_llm to avoid real I/O
        with patch("app.etl.runner._extract_and_split") as mock_extract:
            mock_extract.return_value = ("cap_test", [], {})
            with patch("app.etl.runner.run_phase_llm", return_value=(True, set())):
                captured_executor_kwargs = {}

                def capture_kwarg(*args, **kwargs):
                    captured_executor_kwargs.update(kwargs)
                    return _create_pool(*args, **kwargs)

                with patch("app.etl.runner.ThreadPoolExecutor", side_effect=capture_kwarg):
                    await run_etl_job(
                        job_id="test-cap-chunks-high",
                        file_paths=[file_path],
                        config=config,
                        job_service=mock_job_service,
                        ws_manager=mock_ws_manager,
                    )

    # Verify the capped value was applied (50000 -> 10000)
    assert captured_executor_kwargs["max_workers"] == 2


@pytest.mark.asyncio
async def test_chunk_size_not_capped_when_user_requests_lower(
    tmp_path, mock_ws_manager, mock_job_service
):
    """When flat_config has chunk_size=500 and settings.chunk_size_limit=10000, result is 500."""
    text = "word " * 2000
    file_path = str(tmp_path / "cap_test.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    config = {
        "llm": {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
        "processing": {"chunk_size": 500, "chunk_overlap": 500, "max_workers": 2},
        "prompt_text": "Analyze this text.",
        "output_format": "spr",
    }

    mock_settings = MagicMock()
    mock_settings.max_workers_limit = 4
    mock_settings.chunk_size_limit = 10_000
    mock_settings.output_dir = tmp_path / "output"
    mock_settings.jobs_dir = tmp_path / "jobs"

    with patch("app.etl.runner.get_settings", return_value=mock_settings):
        # Mock _extract_and_split and run_phase_llm to avoid real I/O
        with patch("app.etl.runner._extract_and_split") as mock_extract:
            mock_extract.return_value = ("cap_test", [], {})
            with patch("app.etl.runner.run_phase_llm", return_value=(True, set())):
                captured_executor_kwargs = {}

                def capture_kwarg(*args, **kwargs):
                    captured_executor_kwargs.update(kwargs)
                    return _create_pool(*args, **kwargs)

                with patch("app.etl.runner.ThreadPoolExecutor", side_effect=capture_kwarg):
                    await run_etl_job(
                        job_id="test-cap-chunks-low",
                        file_paths=[file_path],
                        config=config,
                        job_service=mock_job_service,
                        ws_manager=mock_ws_manager,
                    )

    # Verify the value was not capped (2 stays 2)
    assert captured_executor_kwargs["max_workers"] == 2


@pytest.mark.asyncio
async def test_both_values_capped_simultaneously(
    tmp_path, mock_ws_manager, mock_job_service
):
    """Both max_workers and chunk_size are capped when both exceed limits."""
    text = "word " * 2000
    file_path = str(tmp_path / "cap_test.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    config = {
        "llm": {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
        "processing": {"chunk_size": 50_000, "chunk_overlap": 500, "max_workers": 8},
        "prompt_text": "Analyze this text.",
        "output_format": "spr",
    }

    mock_settings = MagicMock()
    mock_settings.max_workers_limit = 4
    mock_settings.chunk_size_limit = 10_000
    mock_settings.output_dir = tmp_path / "output"
    mock_settings.jobs_dir = tmp_path / "jobs"

    with patch("app.etl.runner.get_settings", return_value=mock_settings):
        # Mock _extract_and_split and run_phase_llm to avoid real I/O
        with patch("app.etl.runner._extract_and_split") as mock_extract:
            mock_extract.return_value = ("cap_test", [], {})
            with patch("app.etl.runner.run_phase_llm", return_value=(True, set())):
                captured_executor_kwargs = {}

                def capture_kwarg(*args, **kwargs):
                    captured_executor_kwargs.update(kwargs)
                    return _create_pool(*args, **kwargs)

                with patch("app.etl.runner.ThreadPoolExecutor", side_effect=capture_kwarg):
                    await run_etl_job(
                        job_id="test-cap-both",
                        file_paths=[file_path],
                        config=config,
                        job_service=mock_job_service,
                        ws_manager=mock_ws_manager,
                    )

    # Verify both values were capped (8 -> 4, chunk_size stays at default since not in flat_config)
    assert captured_executor_kwargs["max_workers"] == 4


def _create_pool(*args, **kwargs):
    """Create a real ThreadPoolExecutor with the given kwargs."""
    from concurrent.futures import ThreadPoolExecutor as _TE
    return _TE(*args, **kwargs)
