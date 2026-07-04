"""REST endpoints for file upload/listing/deletion."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from app.services.file_service import get_file_service
from app.schemas.file import FileItem, FileListResponse, FileUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["files"])


@router.post(
    "/files/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_files(files: list[UploadFile] = File(...)) -> FileUploadResponse:
    """Upload one or more files.

    Supported extensions: .txt, .md, .docx, .doc, .pdf
    Max file size: 100 MB
    """
    service = get_file_service()
    uploaded: list[FileItem] = []

    for file in files:
        try:
            item = await service.upload(file)
            uploaded.append(item)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    return FileUploadResponse(
        files=uploaded,
        total=service.list_files().total,
        message=f"Successfully uploaded {len(uploaded)} file(s).",
    )


@router.get("/files", response_model=FileListResponse)
async def list_files() -> FileListResponse:
    """Get list of all uploaded files."""
    service = get_file_service()
    return service.list_files()


@router.delete(
    "/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_file(file_id: str) -> None:
    """Delete a file by ID.

    Raises 404 Not Found if file does not exist.
    """
    service = get_file_service()
    if not service.delete(file_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with id '{file_id}' not found.",
        )
