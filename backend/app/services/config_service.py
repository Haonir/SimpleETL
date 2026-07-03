"""ConfigService — load/save/get_prompts/add_prompt/delete_prompt."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Union

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


# ── Flat defaults used when config.json is missing or fields are absent ─────

_FLAT_DEFAULTS = {
    "model": "llama3",
    "base_url": "http://localhost:11434/v1",
    "api_key": "ollama",
    "chunk_size": 10_000,
    "chunk_overlap": 1_500,
    "max_workers": 1,
    "output_format": "spr",
    "prompts": {},
    "current_prompt_name": "",
}


def _make_defaults() -> ConfigResponse:
    """Build a ConfigResponse from flat defaults (JSON-serializable)."""
    return ConfigResponse(
        llm=LLMConfig(model="llama3", base_url="http://localhost:11434/v1", api_key="ollama"),
        processing=ProcessingConfig(),
        prompts=[],
        current_prompt_name="",
    )


# ── Flat JSON ↔ Nested Pydantic mapping helpers ─────────────────────────────

def _flat_to_nested(data: dict) -> ConfigResponse:
    """Convert flat config.json dict to nested ConfigResponse."""
    llm = LLMConfig(
        model=data.get("model", "llama3"),
        base_url=data.get("base_url", "http://localhost:11434/v1"),
        api_key=data.get("api_key", "ollama"),
    )
    processing = ProcessingConfig(
        chunk_size=data.get("chunk_size", 10_000),
        chunk_overlap=data.get("chunk_overlap", 1_500),
        max_workers=data.get("max_workers", 1),
        output_format=data.get("output_format", "spr"),
    )
    raw_prompts = data.get("prompts") or {}
    prompts_list = [PromptEntry(name=k, text=v) for k, v in raw_prompts.items()]

    return ConfigResponse(
        llm=llm,
        processing=processing,
        prompts=prompts_list,
        current_prompt_name=data.get("current_prompt_name", ""),
    )


def _nested_to_flat(cfg: ConfigResponse) -> dict:
    """Convert nested ConfigResponse to flat config.json dict."""
    return {
        "model": cfg.llm.model,
        "base_url": cfg.llm.base_url,
        "api_key": cfg.llm.api_key,
        "chunk_size": cfg.processing.chunk_size,
        "chunk_overlap": cfg.processing.chunk_overlap,
        "max_workers": cfg.processing.max_workers,
        "output_format": cfg.processing.output_format,
        "prompts": {p.name: p.text for p in cfg.prompts},
        "current_prompt_name": cfg.current_prompt_name,
    }


def _flat_to_nested_with_prompts(data: dict) -> ConfigResponse:
    """Convert flat config.json dict to nested ConfigResponse.
    
    Handles both dict format {name: text} and list format [PromptEntry(...)] for prompts.
    """
    llm = LLMConfig(
        model=data.get("model", "llama3"),
        base_url=data.get("base_url", "http://localhost:11434/v1"),
        api_key=data.get("api_key", "ollama"),
    )
    processing = ProcessingConfig(
        chunk_size=data.get("chunk_size", 10_000),
        chunk_overlap=data.get("chunk_overlap", 1_500),
        max_workers=data.get("max_workers", 1),
        output_format=data.get("output_format", "spr"),
    )
    raw_prompts = data.get("prompts") or {}
    # Handle both dict format {name: text} and legacy list format [PromptEntry(...)]
    if isinstance(raw_prompts, list):
        prompts_list = [PromptEntry(name=p.name, text=p.text) for p in raw_prompts]
    else:
        prompts_list = [PromptEntry(name=k, text=v) for k, v in raw_prompts.items()]

    return ConfigResponse(
        llm=llm,
        processing=processing,
        prompts=prompts_list,
        current_prompt_name=data.get("current_prompt_name", ""),
    )


def _merge_flat(existing: dict, update: ConfigUpdateRequest) -> dict:
    """Merge partial ConfigUpdateRequest into existing flat config."""
    merged = dict(existing)

    if update.llm is not None:
        merged["model"] = update.llm.model
        merged["base_url"] = update.llm.base_url
        merged["api_key"] = update.llm.api_key

    if update.processing is not None:
        merged["chunk_size"] = update.processing.chunk_size
        merged["chunk_overlap"] = update.processing.chunk_overlap
        merged["max_workers"] = update.processing.max_workers
        merged["output_format"] = update.processing.output_format

    if update.prompts is not None:
        new_dict = {p.name: p.text for p in update.prompts}
        existing_names = set(existing.get("prompts", {}).keys())
        new_names = set(new_dict.keys())
        if existing_names - new_names and "current_prompt_name" in merged:
            removed = existing_names - new_names
            if merged["current_prompt_name"] in removed:
                pass  # current_prompt_name will be lost; caller should handle

    if update.current_prompt_name is not None:
        merged["current_prompt_name"] = update.current_prompt_name

    return merged


# ── ConfigService class ─────────────────────────────────────────────────────

class ConfigService:
    """Service for loading, saving and managing the application config."""

    def __init__(self, config_path: Union[str, Path, None] = None):
        if config_path is not None:
            self._config_path = Path(config_path)
        else:
            from app.settings import get_settings

            self._config_path = Path(get_settings().config_file)

    # ── load() ──────────────────────────────────────────────────────────────

    def load(self) -> ConfigResponse:
        """Load configuration from config.json. Returns defaults if file missing."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _flat_to_nested_with_prompts(data)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return _make_defaults()

    # ── save() ───────────────────────────────────────────────────────────────

    def save(self, update: ConfigUpdateRequest) -> ConfigResponse:
        """Save config with partial update. Merges with existing config."""
        try:
            existing = self.load()
            # Convert nested response back to flat dict for merging
            existing_flat = _nested_to_flat(existing)
        except Exception:
            # If we can't load at all, start from defaults
            existing_flat = dict(_FLAT_DEFAULTS)

        merged = _merge_flat(existing_flat, update)
        # Convert flat dict back to nested for file writing and response
        cfg_response = _flat_to_nested_with_prompts(merged)
        flat_data = _nested_to_flat(cfg_response)

        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(flat_data, f, ensure_ascii=False, indent=4)
        except OSError as exc:
            raise OSError(f"Failed to write config file: {exc}") from exc

        return cfg_response

    # ── get_prompts() ────────────────────────────────────────────────────────

    def get_prompts(self) -> PromptLibraryResponse:
        """Return all prompts in the library."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return PromptLibraryResponse(prompts=[], total=0)

        raw_prompts = data.get("prompts") or {}
        # Handle both dict format {name: text} and legacy list format [PromptEntry(...)]
        if isinstance(raw_prompts, list):
            prompts_list = [PromptEntry(name=p.name, text=p.text) for p in raw_prompts]
        else:
            prompts_list = [PromptEntry(name=k, text=v) for k, v in raw_prompts.items()]
        return PromptLibraryResponse(prompts=prompts_list, total=len(prompts_list))

    # ── add_prompt() ────────────────────────────────────────────────────────

    def add_prompt(self, req: PromptCreateRequest) -> PromptEntry:
        """Add a new prompt. Raises ValueError if name already exists."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            # Create file from defaults if missing or invalid JSON
            data = dict(_FLAT_DEFAULTS)

        raw_prompts = data.get("prompts") or {}
        # Handle both dict format {name: text} and legacy list format [PromptEntry(...)]
        if isinstance(raw_prompts, list):
            existing_dict = {p.name: p.text for p in raw_prompts}
        else:
            existing_dict = dict(raw_prompts)

        existing_names = set(existing_dict.keys())
        if req.name in existing_names:
            raise ValueError(
                f"Prompt with name '{req.name}' already exists. "
                f"Available names: {', '.join(sorted(existing_names))}"
            )

        existing_dict[req.name] = req.text
        data["prompts"] = existing_dict

        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except OSError as exc:
            raise OSError(f"Failed to write config file: {exc}") from exc

        return PromptEntry(name=req.name, text=req.text)

    # ── delete_prompt() ─────────────────────────────────────────────────────

    def delete_prompt(self, name: str) -> PromptDeleteResponse:
        """Delete a prompt by name. Raises ValueError if not found."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, OSError):
            raise ValueError("Config file not found.")

        raw_prompts = data.get("prompts") or {}
        # Handle both dict format {name: text} and legacy list format [PromptEntry(...)]
        if isinstance(raw_prompts, list):
            prompts_dict = {p.name: p.text for p in raw_prompts}
        else:
            prompts_dict = dict(raw_prompts)

        if name not in prompts_dict:
            raise ValueError(
                f"Prompt '{name}' not found. "
                f"Available names: {', '.join(sorted(prompts_dict.keys()))}"
            )

        del prompts_dict[name]
        data["prompts"] = prompts_dict

        # If the deleted prompt was current, clear it
        if data.get("current_prompt_name") == name:
            data["current_prompt_name"] = ""

        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except OSError as exc:
            raise OSError(f"Failed to write config file: {exc}") from exc

        return PromptDeleteResponse(deleted=name, message=f"Prompt '{name}' removed.")
