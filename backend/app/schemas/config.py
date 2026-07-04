"""Pydantic v2 schemas for config-related data models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM provider configuration (model name, base URL, API key)."""

    model: str = Field(..., description="Name of the LLM model.")
    base_url: str = Field(..., description="Base URL of the OpenAI-compatible endpoint.")
    api_key: str = Field(..., description="API key for authentication with the LLM provider.")


class ProcessingConfig(BaseModel):
    """ETL processing parameters (chunking, workers, output format)."""

    chunk_size: int = Field(default=10_000, ge=1, le=10_000_000, description="Max tokens/characters per chunk.")
    chunk_overlap: int = Field(default=1_500, ge=0, description="Overlap between adjacent chunks.")
    max_workers: int = Field(default=1, ge=1, description="Number of parallel processing workers.")
    output_format: Literal["spr", "frontmatter", "markdown", "html"] = Field(
        default="spr",
        description="Output format for generated markdown files (spr, frontmatter, markdown, html).",
    )
    skip_llm: bool = Field(default=False, description="Skip LLM processing — chunks are packed directly.")


class PromptEntry(BaseModel):
    """A single prompt entry in the library (name + text)."""

    name: str = Field(..., min_length=1, max_length=200, description="Unique prompt identifier.")
    text: str = Field(..., min_length=1, description="Prompt template text.")


class ConfigResponse(BaseModel):
    """Full configuration response (LLM + processing + prompts)."""

    llm: LLMConfig
    processing: ProcessingConfig
    prompts: list[PromptEntry]
    current_prompt_name: str = Field(..., description="Name of the currently active prompt.")


class ConfigUpdateRequest(BaseModel):
    """Partial configuration update (all fields optional for PATCH semantics)."""

    llm: Optional[LLMConfig] = None
    processing: Optional[ProcessingConfig] = None
    prompts: Optional[list[PromptEntry]] = None
    current_prompt_name: Optional[str] = None


class PromptCreateRequest(BaseModel):
    """Request body for creating a new prompt in the library."""

    name: str = Field(..., min_length=1, max_length=200)
    text: str = Field(..., min_length=1)


class PromptDeleteResponse(BaseModel):
    """Confirmation response after deleting a prompt by name."""

    deleted: str = Field(..., description="Name of the deleted prompt.")
    message: str = Field(default="Prompt removed from library.", description="Human-readable confirmation.")


class PromptLibraryResponse(BaseModel):
    """List of all prompts in the library with total count."""

    prompts: list[PromptEntry]
    total: int = Field(..., description="Total number of prompts in the library.")
