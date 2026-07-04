"""Схемы данных (Pydantic v2) для SimpleETL backend."""

from .config import (
    ConfigResponse,
    ConfigUpdateRequest,
    LLMConfig,
    ProcessingConfig,
    PromptCreateRequest,
    PromptDeleteResponse,
    PromptEntry,
    PromptLibraryResponse,
)

from .file import FileItem, FileListResponse, FileUploadResponse

from .job import JobItem, JobListResponse, JobResponse, JobStatus

__all__ = [
    "LLMConfig",
    "ProcessingConfig",
    "PromptEntry",
    "ConfigResponse",
    "ConfigUpdateRequest",
    "PromptCreateRequest",
    "PromptDeleteResponse",
    "PromptLibraryResponse",
    "FileItem",
    "FileListResponse",
    "FileUploadResponse",
    "JobItem",
    "JobListResponse",
    "JobResponse",
    "JobStatus",
]
