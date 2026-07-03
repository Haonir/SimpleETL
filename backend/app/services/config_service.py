"""ConfigService — load/save/get_prompts/add_prompt/delete_prompt.

Works with nested config.json format matching Pydantic schemas directly.
Handles legacy flat format via auto-migration on read.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Union

from app.schemas.config import (
    ConfigResponse,
    ConfigUpdateRequest,
    LLMConfig,
    PromptCreateRequest,
    PromptDeleteResponse,
    PromptEntry,
    PromptLibraryResponse,
    ProcessingConfig,
)

logger = logging.getLogger(__name__)


# ── Defaults ────────────────────────────────────────────────────────────────

_DEFAULTS = ConfigResponse(
    llm=LLMConfig(model="llama3", base_url="http://localhost:11434/v1", api_key="ollama"),
    processing=ProcessingConfig(),
    prompts=[],
    current_prompt_name="",
)


# ── Legacy flat format detection & migration ────────────────────────────────

def _is_flat_format(data: dict) -> bool:
    """Check if config.json uses the old flat format (no 'llm' key)."""
    return "llm" not in data and "model" in data


def _migrate_flat_to_nested(data: dict) -> dict:
    """Convert old flat config.json to nested format."""
    return {
        "llm": {
            "model": data.get("model", "llama3"),
            "base_url": data.get("base_url", "http://localhost:11434/v1"),
            "api_key": data.get("api_key", "ollama"),
        },
        "processing": {
            "chunk_size": data.get("chunk_size", 10_000),
            "chunk_overlap": data.get("chunk_overlap", 1_500),
            "max_workers": data.get("max_workers", 1),
            "output_format": data.get("output_format", "spr"),
        },
        "prompts": data.get("prompts", {}),
        "current_prompt_name": data.get("current_prompt_name", ""),
    }


def _normalize_prompts(data: dict) -> dict:
    """Normalize prompts to list-of-dicts format for Pydantic parsing."""
    raw = data.get("prompts") or {}
    if isinstance(raw, dict):
        data["prompts"] = [{"name": k, "text": v} for k, v in raw.items()]
    return data


# ── ConfigService ───────────────────────────────────────────────────────────


class ConfigService:
    """Service for loading, saving and managing the application config."""

    def __init__(self, config_path: Union[str, Path, None] = None):
        if config_path is not None:
            self._config_path = Path(config_path)
        else:
            from app.settings import get_settings
            settings = get_settings()
            self._config_path = settings._config_path

    # ── Internal helpers ────────────────────────────────────────────────────

    def _read_raw(self) -> dict | None:
        """Read raw JSON dict from disk. Returns None if missing/corrupt."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None

    def _write(self, cfg: ConfigResponse) -> None:
        """Write ConfigResponse to disk as nested JSON."""
        data = cfg.model_dump()
        # Prompts: list[dict] → dict for compact storage
        data["prompts"] = {p["name"]: p["text"] for p in data["prompts"]}
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _parse(self, data: dict) -> ConfigResponse:
        """Parse raw dict into ConfigResponse, auto-migrating flat format."""
        if _is_flat_format(data):
            logger.info("Auto-migrating flat config format to nested")
            data = _migrate_flat_to_nested(data)
        data = _normalize_prompts(data)
        # Merge with defaults so partial dicts (e.g. from add_prompt) still parse
        merged = {**_DEFAULTS.model_dump(), **data}
        return ConfigResponse.model_validate(merged)

    # ── Public API ──────────────────────────────────────────────────────────

    def load(self) -> ConfigResponse:
        """Load configuration from config.json. Returns defaults if file missing."""
        data = self._read_raw()
        if data is None:
            return _DEFAULTS.model_copy()
        return self._parse(data)

    def save(self, update: ConfigUpdateRequest) -> ConfigResponse:
        """Save config with partial update. Merges with existing config."""
        current = self.load()
        update_data = update.model_dump(exclude_unset=True)

        # Merge: nested dicts are updated field-by-field, not replaced wholesale
        merged = current.model_dump()
        for key, value in update_data.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value

        result = ConfigResponse.model_validate(merged)
        self._write(result)
        return result

    def get_prompts(self) -> PromptLibraryResponse:
        """Return all prompts in the library."""
        data = self._read_raw()
        if data is None:
            return PromptLibraryResponse(prompts=[], total=0)

        data = _normalize_prompts(data)
        prompts = [PromptEntry.model_validate(p) for p in data["prompts"]]
        return PromptLibraryResponse(prompts=prompts, total=len(prompts))

    def add_prompt(self, req: PromptCreateRequest) -> PromptEntry:
        """Add a new prompt. Raises ValueError if name already exists."""
        data = self._read_raw() or {}

        raw = data.get("prompts") or {}
        prompts_dict = {p["name"]: p["text"] for p in raw} if isinstance(raw, list) else dict(raw)

        if req.name in prompts_dict:
            raise ValueError(
                f"Prompt with name '{req.name}' already exists. "
                f"Available: {', '.join(sorted(prompts_dict.keys()))}"
            )

        prompts_dict[req.name] = req.text
        data["prompts"] = prompts_dict

        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return PromptEntry(name=req.name, text=req.text)

    def delete_prompt(self, name: str) -> PromptDeleteResponse:
        """Delete a prompt by name. Raises ValueError if not found."""
        data = self._read_raw()
        if data is None:
            raise ValueError("Config file not found.")

        raw = data.get("prompts") or {}
        prompts_dict = {p["name"]: p["text"] for p in raw} if isinstance(raw, list) else dict(raw)

        if name not in prompts_dict:
            raise ValueError(
                f"Prompt '{name}' not found. "
                f"Available: {', '.join(sorted(prompts_dict.keys()))}"
            )

        del prompts_dict[name]
        data["prompts"] = prompts_dict

        if data.get("current_prompt_name") == name:
            data["current_prompt_name"] = ""

        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return PromptDeleteResponse(deleted=name, message=f"Prompt '{name}' removed.")
