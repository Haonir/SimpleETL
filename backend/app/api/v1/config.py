"""REST endpoints for config and prompt management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from app.services.config_service import ConfigService
from app.schemas.config import (
    ConfigResponse,
    ConfigUpdateRequest,
    PromptCreateRequest,
    PromptDeleteResponse,
    PromptEntry,
    PromptLibraryResponse,
)

router = APIRouter(prefix="/api/v1", tags=["config"])


@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Get the current application configuration."""
    service = ConfigService()
    return service.load()


@router.post(
    "/config",
    response_model=ConfigResponse,
    status_code=status.HTTP_200_OK,
)
async def post_config(update: ConfigUpdateRequest) -> ConfigResponse:
    """Save (or partially update) the application configuration."""
    service = ConfigService()
    return service.save(update)


@router.get("/prompts", response_model=PromptLibraryResponse)
async def get_prompts() -> PromptLibraryResponse:
    """Get all prompts in the library."""
    service = ConfigService()
    return service.get_prompts()


@router.post(
    "/prompts",
    response_model=PromptEntry,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(req: PromptCreateRequest) -> PromptEntry:
    """Add a new prompt to the library.

    Raises 409 Conflict if a prompt with the same name already exists.
    """
    service = ConfigService()
    try:
        return service.add_prompt(req)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete("/prompts/{name}", response_model=PromptDeleteResponse)
async def delete_prompt(name: str) -> PromptDeleteResponse:
    """Delete a prompt by name.

    Raises 404 Not Found if the prompt does not exist.
    """
    service = ConfigService()
    try:
        return service.delete_prompt(name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
