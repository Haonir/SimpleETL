"""Config file API endpoints."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/config", tags=["config"])

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "static" / "config.json"


class ConfigData(BaseModel):
    """Config data - accepts any JSON object."""
    class Config:
        extra = "allow"


@router.get("")
async def get_config():
    """Get current config from file."""
    try:
        if not CONFIG_PATH.exists():
            return {}
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to read config: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def save_config(data: ConfigData):
    """Save config to file."""
    try:
        logger.info("Saving config to: %s", CONFIG_PATH)
        logger.info("Config data: %s", data.model_dump())
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data.model_dump(), f, indent=2, ensure_ascii=False)
        logger.info("Config saved successfully")
        return {"status": "ok"}
    except Exception as e:
        logger.error("Failed to save config: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
