"""Application settings using pydantic-settings (env vars + config.json fallback)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Centralized app configuration.

    Reads from environment variables (with optional ``APP_`` prefix) and falls back
    to ``config.json`` located next to the config file on disk.
    Handles both development and PyInstaller frozen modes.
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Paths ────────────────────────────────────────────────────────────────
    config_file: str = ""  # populated from disk or env; empty → default path
    data_dir: Path = Path(".")  # base directory for output files (raw/, processed/, final/)

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_model: str = "llama3"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"

    # ── Processing ───────────────────────────────────────────────────────────
    chunk_size: int = 10_000
    chunk_overlap: int = 1_500
    max_workers: int = 1
    output_format: str = "spr"  # spr | frontmatter | markdown

    # ── Prompts ──────────────────────────────────────────────────────────────
    prompts_file: Optional[str] = None  # path to prompts JSON (optional)

    @property
    def _config_path(self) -> Path:
        """Resolve config.json path — handles frozen (PyInstaller) mode."""
        if self.config_file:
            return Path(self.config_file)
        if getattr(sys, "frozen", False):
            # PyInstaller --onefile: use sys._MEIPASS / sys.executable
            base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable)
        else:
            base = Path(__file__).resolve().parent.parent.parent  # backend/ → project root
        return base / "core" / "config.json"

    @classmethod
    def from_env(cls, config_file: Optional[str] | None = None) -> AppSettings:
        """Create settings with explicit config file path (e.g. for tests)."""
        if config_file is not None:
            os.environ["APP_CONFIG_FILE"] = str(config_file)
        return cls()

    def model_post_init(self, __context: object) -> None:  # type: ignore[no-untyped-def]
        """After init — resolve config file path from disk if env var is set."""
        cfg_path_str = os.environ.get("APP_CONFIG_FILE", "")
        if cfg_path_str:
            self.config_file = cfg_path_str

    @property
    def prompts_dict(self) -> dict[str, str]:
        """Load prompt library from config.json (prompts field)."""
        import json as _json

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            return data.get("prompts", {})
        except (FileNotFoundError, OSError, _json.JSONDecodeError):
            return {}


# ── Singleton instance ─────────────────────────────────────────────────────

_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Return the global settings singleton, creating it on first call."""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings
