"""Tests for ConfigService."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from app.services.config_service import ConfigService
from app.schemas.config import (
    ConfigResponse,
    ConfigUpdateRequest,
    LLMConfig,
    PromptCreateRequest,
    PromptDeleteResponse,
    PromptEntry,
    ProcessingConfig,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_config_path(tmp_path: Path) -> Path:
    """Return a temporary path for config.json."""
    cfg = tmp_path / "config.json"
    return cfg


@pytest.fixture
def empty_config_file(tmp_path: Path) -> Path:
    """Create an empty config.json file and return its path."""
    cfg = tmp_path / "config.json"
    cfg.write_text("", encoding="utf-8")
    return cfg


@pytest.fixture
def populated_config_file(tmp_path: Path) -> Path:
    """Create a pre-populated config.json with some prompts."""
    cfg = tmp_path / "config.json"
    data = {
        "model": "llama3",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "chunk_size": 5000,
        "chunk_overlap": 200,
        "max_workers": 2,
        "output_format": "spr",
        "prompts": {
            "summarize": "Summarize the following text:",
            "extract": "Extract key points from the text:",
        },
        "current_prompt_name": "summarize",
    }
    cfg.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    return cfg


# ── Test load() ─────────────────────────────────────────────────────────────

class TestLoad:
    def test_load_missing_file_returns_defaults(self):
        svc = ConfigService(config_path="/tmp/nonexistent_config.json_12345")
        resp = svc.load()
        assert isinstance(resp, ConfigResponse)
        assert resp.llm.model == "llama3"
        assert resp.processing.chunk_size == 10_000

    def test_load_from_populated_file(self, populated_config_file: Path):
        svc = ConfigService(config_path=populated_config_file)
        resp = svc.load()
        assert resp.llm.model == "llama3"
        assert resp.processing.chunk_size == 5_000
        assert len(resp.prompts) == 2
        assert resp.current_prompt_name == "summarize"

    def test_load_corrupted_file_returns_defaults(self, tmp_path: Path):
        cfg = tmp_path / "config.json"
        cfg.write_text("{invalid json", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        resp = svc.load()
        assert isinstance(resp, ConfigResponse)

    def test_load_binary_file_returns_defaults(self, tmp_path: Path):
        cfg = tmp_path / "config.json"
        cfg.write_bytes(b"\x00\x01\x02")
        svc = ConfigService(config_path=cfg)
        resp = svc.load()
        assert isinstance(resp, ConfigResponse)


# ── Test save() ─────────────────────────────────────────────────────────────

class TestSave:
    def test_save_partial_update(self, tmp_config_path: Path):
        svc = ConfigService(config_path=tmp_config_path)
        # First load (returns defaults since file doesn't exist yet)
        resp = svc.load()
        # Now save a partial update
        updated = svc.save(
            ConfigUpdateRequest(llm=LLMConfig(model="gpt-4", base_url="https://api.openai.com/v1", api_key="sk-test"))
        )
        assert updated.llm.model == "gpt-4"
        # Other fields should remain at defaults
        assert updated.processing.chunk_size == 10_000

    def test_save_creates_file(self, tmp_config_path: Path):
        svc = ConfigService(config_path=tmp_config_path)
        resp = svc.save(
            ConfigUpdateRequest(llm=LLMConfig(model="test", base_url="http://localhost/v1", api_key="key"))
        )
        assert os.path.exists(tmp_config_path)
        with open(tmp_config_path, "r") as f:
            data = json.load(f)
        assert data["model"] == "test"

    def test_save_overwrites_existing(self, populated_config_file: Path):
        svc = ConfigService(config_path=populated_config_file)
        resp = svc.save(
            ConfigUpdateRequest(processing=ProcessingConfig(chunk_size=3000))
        )
        assert resp.processing.chunk_size == 3000


# ── Test get_prompts() ─────────────────────────────────────────────────────

class TestGetPrompts:
    def test_get_prompts_from_populated_file(self, populated_config_file: Path):
        svc = ConfigService(config_path=populated_config_file)
        resp = svc.get_prompts()
        assert resp.total == 2
        names = {p.name for p in resp.prompts}
        assert "summarize" in names
        assert "extract" in names

    def test_get_prompts_from_missing_file(self, tmp_path: Path):
        svc = ConfigService(config_path=tmp_path / "nonexistent.json")
        resp = svc.get_prompts()
        assert resp.total == 0
        assert resp.prompts == []


# ── Test add_prompt() ───────────────────────────────────────────────────────

class TestAddPrompt:
    def test_add_new_prompt(self, populated_config_file: Path):
        svc = ConfigService(config_path=populated_config_file)
        entry = svc.add_prompt(PromptCreateRequest(name="new_prompt", text="New prompt text."))
        assert entry.name == "new_prompt"
        # Verify it was saved
        resp = svc.get_prompts()
        assert resp.total == 3

    def test_add_duplicate_raises_value_error(self, populated_config_file: Path):
        svc = ConfigService(config_path=populated_config_file)
        with pytest.raises(ValueError, match="already exists"):
            svc.add_prompt(PromptCreateRequest(name="summarize", text="Duplicate."))

    def test_add_to_empty_file(self, empty_config_file: Path):
        svc = ConfigService(config_path=empty_config_file)
        entry = svc.add_prompt(PromptCreateRequest(name="first", text="First prompt"))
        assert entry.name == "first"


# ── Test delete_prompt() ───────────────────────────────────────────────────

class TestDeletePrompt:
    def test_delete_existing_prompt(self, populated_config_file: Path):
        svc = ConfigService(config_path=populated_config_file)
        resp = svc.delete_prompt("summarize")
        assert resp.deleted == "summarize"
        # Verify it was removed
        remaining = svc.get_prompts()
        assert remaining.total == 1

    def test_delete_nonexistent_raises_value_error(self, populated_config_file: Path):
        svc = ConfigService(config_path=populated_config_file)
        with pytest.raises(ValueError, match="not found"):
            svc.delete_prompt("nonexistent")

    def test_delete_clears_current_prompt_name(self, populated_config_file: Path):
        svc = ConfigService(config_path=populated_config_file)
        resp = svc.delete_prompt("summarize")
        assert resp.deleted == "summarize"
        # current_prompt_name should be cleared since summarize was deleted
        data = json.loads(populated_config_file.read_text())
        assert data["current_prompt_name"] == ""


# ── Test end-to-end workflow ───────────────────────────────────────────────

class TestEndToEnd:
    def test_full_workflow(self, tmp_path: Path):
        cfg_path = tmp_path / "config.json"
        svc = ConfigService(config_path=cfg_path)

        # 1. Load (missing file → defaults)
        resp = svc.load()
        assert resp.llm.model == "llama3"

        # 2. Add prompts
        svc.add_prompt(PromptCreateRequest(name="summarize", text="Summarize:"))
        svc.add_prompt(PromptCreateRequest(name="extract", text="Extract:"))

        # 3. Get prompts
        library = svc.get_prompts()
        assert library.total == 2

        # 4. Partial update via save
        updated = svc.save(
            ConfigUpdateRequest(processing=ProcessingConfig(chunk_size=5000))
        )
        assert updated.processing.chunk_size == 5000

        # 5. Delete a prompt
        resp = svc.delete_prompt("extract")
        assert resp.deleted == "extract"

        # 6. Verify final state
        final = svc.get_prompts()
        assert final.total == 1
        assert final.prompts[0].name == "summarize"
