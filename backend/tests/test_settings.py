"""Tests for AppSettings (pydantic-settings configuration)."""

from __future__ import annotations

import json as _json
import os
import tempfile
from pathlib import Path

import pytest

from app.settings import AppSettings, get_settings


# ── AppSettings defaults ────────────────────────────────────────────────────


class TestAppSettingsDefaults:
    def test_default_values(self):
        settings = AppSettings()
        assert settings.llm_model == "llama3"
        assert settings.llm_base_url == "http://localhost:11434/v1"
        assert settings.llm_api_key == "ollama"
        assert settings.chunk_size == 10_000
        assert settings.chunk_overlap == 1_500
        assert settings.max_workers == 1
        assert settings.output_format == "spr"

    def test_default_prompts_dict_empty(self, tmp_path):
        """prompts_dict is empty when config.json does not exist."""
        settings = AppSettings(config_file=str(tmp_path / "nonexistent_config.json"))
        assert settings.prompts_dict == {}


# ── Environment variable overrides ──────────────────────────────────────────


class TestAppSettingsEnvVars:
    def test_env_override_llm_model(self):
        os.environ["APP_LLM_MODEL"] = "gpt-4"
        try:
            settings = AppSettings()
            assert settings.llm_model == "gpt-4"
        finally:
            del os.environ["APP_LLM_MODEL"]

    def test_env_override_chunk_size(self):
        os.environ["APP_CHUNK_SIZE"] = "5000"
        try:
            settings = AppSettings()
            assert settings.chunk_size == 5000
        finally:
            del os.environ["APP_CHUNK_SIZE"]

    def test_env_override_max_workers(self):
        os.environ["APP_MAX_WORKERS"] = "4"
        try:
            settings = AppSettings()
            assert settings.max_workers == 4
        finally:
            del os.environ["APP_MAX_WORKERS"]

    def test_env_prefix_case_insensitive(self):
        """case_sensitive=False allows mixed-case prefix."""
        os.environ["app_llm_base_url"] = "http://custom:8080/v1"
        try:
            settings = AppSettings()
            assert settings.llm_base_url == "http://custom:8080/v1"
        finally:
            del os.environ["app_llm_base_url"]

    # NOTE: env_nested_delimiter '__' only works for nested Pydantic models, not flat fields.
    # Flat fields like llm_model cannot use the nested delimiter pattern (e.g., APP_LLM__MODEL).


# ── Config file path resolution ─────────────────────────────────────────────


class TestAppSettingsConfigPath:
    def test_config_path_default(self):
        """Default config path resolves to backend/config.json (absolute)."""
        settings = AppSettings()
        expected = Path(__file__).resolve().parent.parent.parent / "backend" / "config.json"  # backend/app/ → project root
        assert settings._config_path == expected

    def test_config_path_from_env(self, tmp_path):
        """APP_CONFIG_FILE env var overrides default path."""
        cfg_file = tmp_path / "custom_config.json"
        cfg_file.write_text('{"prompts": {"p1": "prompt 1"}}')
        os.environ["APP_CONFIG_FILE"] = str(cfg_file)
        try:
            settings = AppSettings()
            assert settings.config_file == str(cfg_file)
            assert settings._config_path == cfg_file
        finally:
            del os.environ["APP_CONFIG_FILE"]


# ── Prompts loading ─────────────────────────────────────────────────────────


class TestAppSettingsPrompts:
    def test_load_prompts_from_config(self, tmp_path):
        """prompts_dict loads from config.json."""
        cfg_file = tmp_path / "config.json"
        data = {"prompts": {"p1": "prompt 1", "p2": "prompt 2"}}
        cfg_file.write_text(_json.dumps(data))

        settings = AppSettings()
        settings.config_file = str(cfg_file)
        assert settings.prompts_dict == {"p1": "prompt 1", "p2": "prompt 2"}

    def test_load_prompts_missing_file(self, tmp_path):
        """Missing config.json returns empty dict."""
        settings = AppSettings()
        settings.config_file = str(tmp_path / "nonexistent.json")
        assert settings.prompts_dict == {}

    def test_load_prompts_invalid_json(self, tmp_path):
        """Invalid JSON in config.json returns empty dict (graceful fallback)."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("not valid json{{{")

        settings = AppSettings()
        settings.config_file = str(cfg_file)
        assert settings.prompts_dict == {}


# ── Singleton get_settings ──────────────────────────────────────────────────


class TestGetSettings:
    def test_returns_singleton(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_returns_appsettings_instance(self):
        settings = get_settings()
        assert isinstance(settings, AppSettings)
