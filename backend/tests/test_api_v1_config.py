"""Tests for REST endpoints in app/api/v1/config.py."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


# ── GET /config ─────────────────────────────────────────────────────────────

def test_get_config_default(client):
    """GET /api/v1/config returns defaults when no config file exists."""
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "llm" in data
    assert "processing" in data
    assert "prompts" in data
    assert data["llm"]["model"] == "llama3"


def test_get_config_with_file(client, isolated_config):
    """GET /api/v1/config returns saved config."""
    cfg = {
        "model": "gpt-4",
        "base_url": "http://custom:8080/v1",
        "api_key": "secret",
        "chunk_size": 5_000,
        "current_prompt_name": "",
    }
    with open(isolated_config["path"], "w") as f:
        json.dump(cfg, f)

    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm"]["model"] == "gpt-4"
    assert data["processing"]["chunk_size"] == 5_000


# ── POST /config ────────────────────────────────────────────────────────────

def test_post_config_full_update(client, isolated_config):
    """POST /api/v1/config saves a full configuration."""
    body = {
        "llm": {"model": "claude", "base_url": "http://localhost:1234/v1", "api_key": "key"},
        "processing": {"chunk_size": 8_000, "output_format": "frontmatter"},
    }
    resp = client.post("/api/v1/config", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm"]["model"] == "claude"

    # Verify file was written
    with open(isolated_config["path"]) as f:
        saved = json.load(f)
    assert saved["llm"]["model"] == "claude"


def test_post_config_partial_update(client, isolated_config):
    """POST /api/v1/config performs a partial update."""
    # First save something with full LLM config
    client.post("/api/v1/config", json={
        "llm": {"model": "old", "base_url": "http://localhost:8080/v1", "api_key": "key"},
        "processing": {"chunk_size": 5_000, "output_format": "spr"}
    })

    # Then update only model (keeping other LLM fields)
    resp = client.post("/api/v1/config", json={
        "llm": {"model": "new", "base_url": "http://localhost:8080/v1", "api_key": "key"}
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm"]["model"] == "new"


# ── GET /prompts ────────────────────────────────────────────────────────────

def test_get_prompts_empty(client, isolated_config):
    """GET /api/v1/prompts returns empty list when no prompts exist."""
    resp = client.get("/api/v1/prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["prompts"] == []


def test_get_prompts_with_data(client, isolated_config):
    """GET /api/v1/prompts returns prompts from config file."""
    cfg = {"model": "llama3", "base_url": "http://localhost:11434/v1", "api_key": "ollama"}
    with open(isolated_config["path"], "w") as f:
        json.dump(cfg, f)

    resp = client.get("/api/v1/prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


# ── POST /prompts ───────────────────────────────────────────────────────────

def test_post_prompt_create(client, isolated_config):
    """POST /api/v1/prompts creates a new prompt with 201."""
    body = {"name": "summarize", "text": "Summarize the following text."}
    resp = client.post("/api/v1/prompts", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "summarize"

    # Verify it persists in config file
    with open(isolated_config["path"]) as f:
        saved = json.load(f)
    assert "prompts" in saved
    assert saved["prompts"]["summarize"] == "Summarize the following text."


def test_post_prompt_duplicate(client, isolated_config):
    """POST /api/v1/prompts returns 409 for duplicate prompt name."""
    body = {"name": "test-prompt", "text": "First version"}
    client.post("/api/v1/prompts", json=body)

    resp = client.post("/api/v1/prompts", json={"name": "test-prompt", "text": "Second version"})
    assert resp.status_code == 409


# ── DELETE /prompts/{name} ──────────────────────────────────────────────────

def test_delete_prompt(client, isolated_config):
    """DELETE /api/v1/prompts/{name} removes a prompt and returns 200."""
    body = {"name": "to-delete", "text": "Will be removed"}
    client.post("/api/v1/prompts", json=body)

    resp = client.delete("/api/v1/prompts/to-delete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] == "to-delete"


def test_delete_prompt_not_found(client):
    """DELETE /api/v1/prompts/{name} returns 404 for nonexistent prompt."""
    resp = client.delete("/api/v1/prompts/nonexistent")
    assert resp.status_code == 404
