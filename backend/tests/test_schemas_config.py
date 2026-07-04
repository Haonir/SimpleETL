"""Validation tests for config-related Pydantic schemas."""

from __future__ import annotations

import pytest

from app.schemas.config import (
    ConfigResponse,
    ConfigUpdateRequest,
    LLMConfig,
    ProcessingConfig,
    PromptCreateRequest,
    PromptDeleteResponse,
    PromptEntry,
    PromptLibraryResponse,
)


# ── LLMConfig ───────────────────────────────────────────────────────────────

class TestLLMConfig:
    def test_valid(self):
        cfg = LLMConfig(model="llama3", base_url="http://localhost:11434/v1", api_key="ollama")
        assert cfg.model == "llama3"
        assert cfg.base_url == "http://localhost:11434/v1"
        assert cfg.api_key == "ollama"

    def test_missing_fields_raises(self):
        with pytest.raises(Exception):  # pydantic.ValidationError
            LLMConfig()


# ── ProcessingConfig ────────────────────────────────────────────────────────

class TestProcessingConfig:
    def test_defaults(self):
        cfg = ProcessingConfig()
        assert cfg.chunk_size == 10_000
        assert cfg.chunk_overlap == 1_500
        assert cfg.max_workers == 1
        assert cfg.output_format == "spr"

    def test_custom_values(self):
        cfg = ProcessingConfig(
            chunk_size=2000,
            chunk_overlap=300,
            max_workers=4,
            output_format="frontmatter",
        )
        assert cfg.chunk_size == 2000
        assert cfg.chunk_overlap == 300
        assert cfg.max_workers == 4
        assert cfg.output_format == "frontmatter"

    def test_invalid_output_format(self):
        with pytest.raises(Exception):
            ProcessingConfig(output_format="xml")

    def test_valid_html_format(self):
        cfg = ProcessingConfig(output_format="html")
        assert cfg.output_format == "html"


# ── PromptEntry ─────────────────────────────────────────────────────────────

class TestPromptEntry:
    def test_valid(self):
        entry = PromptEntry(name="summarize", text="Summarize the following text:")
        assert entry.name == "summarize"
        assert entry.text == "Summarize the following text:"

    def test_empty_name_raises(self):
        with pytest.raises(Exception):
            PromptEntry(name="", text="some prompt")


# ── ConfigResponse ──────────────────────────────────────────────────────────

class TestConfigResponse:
    def test_valid_full_config(self):
        resp = ConfigResponse(
            llm=LLMConfig(model="gpt-4", base_url="https://api.openai.com/v1", api_key="sk-test"),
            processing=ProcessingConfig(chunk_size=5000, chunk_overlap=200),
            prompts=[PromptEntry(name="p1", text="prompt 1")],
            current_prompt_name="p1",
        )
        assert resp.llm.model == "gpt-4"
        assert len(resp.prompts) == 1
        assert resp.current_prompt_name == "p1"

    def test_empty_prompts_list(self):
        resp = ConfigResponse(
            llm=LLMConfig(model="test", base_url="http://localhost/v1", api_key="key"),
            processing=ProcessingConfig(),
            prompts=[],
            current_prompt_name="",
        )
        assert resp.prompts == []


# ── ConfigUpdateRequest ─────────────────────────────────────────────────────

class TestConfigUpdateRequest:
    def test_full_update(self):
        req = ConfigUpdateRequest(
            llm=LLMConfig(model="new-model", base_url="http://new/v1", api_key="key"),
            processing=ProcessingConfig(chunk_size=3000),
            prompts=[PromptEntry(name="p2", text="prompt 2")],
            current_prompt_name="p2",
        )
        assert req.llm.model == "new-model"

    def test_partial_update(self):
        req = ConfigUpdateRequest(llm=LLMConfig(model="updated", base_url="http://localhost:11434/v1", api_key="ollama"))
        assert req.processing is None
        assert req.prompts is None
        assert req.current_prompt_name is None


# ── PromptCreateRequest ─────────────────────────────────────────────────────

class TestPromptCreateRequest:
    def test_valid(self):
        req = PromptCreateRequest(name="extract", text="Extract key points:")
        assert req.name == "extract"
        assert req.text == "Extract key points:"


# ── PromptDeleteResponse ────────────────────────────────────────────────────

class TestPromptDeleteResponse:
    def test_valid(self):
        resp = PromptDeleteResponse(deleted="old_prompt", message="Removed.")
        assert resp.deleted == "old_prompt"
        assert resp.message == "Removed."


# ── PromptLibraryResponse ───────────────────────────────────────────────────

class TestPromptLibraryResponse:
    def test_valid(self):
        resp = PromptLibraryResponse(
            prompts=[PromptEntry(name="p1", text="t1"), PromptEntry(name="p2", text="t2")],
            total=2,
        )
        assert len(resp.prompts) == 2
        assert resp.total == 2

    def test_empty_library(self):
        resp = PromptLibraryResponse(prompts=[], total=0)
        assert resp.total == 0
