"""Shared fixtures for API tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.config import router


@pytest.fixture
def isolated_config(tmp_path: Path) -> dict:
    """Create an isolated config.json in tmp and set env var."""
    cfg_path = tmp_path / "config.json"
    old = os.environ.get("APP_CONFIG_FILE")
    os.environ["APP_CONFIG_FILE"] = str(cfg_path)

    # Reset the AppSettings singleton so it picks up the new env var
    import app.settings as _settings_mod
    _settings_mod._settings = None

    yield {"path": str(cfg_path)}

    if old is not None:
        os.environ["APP_CONFIG_FILE"] = old
    else:
        os.environ.pop("APP_CONFIG_FILE", None)
    # Reset again after test
    _settings_mod._settings = None


@pytest.fixture
def client(isolated_config: dict) -> TestClient:
    """Create a FastAPI TestClient with only the config router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)
