"""Pydantic schemas for document operations."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    """Document metadata returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    file_size_bytes: int
    status: str
    chunk_count: int
    error_code: Optional[str] = None
    is_public: bool
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    """Asynchronous upload response (HTTP 202)."""

    document_id: UUID
    filename: str
    status: str = "processing"
    message: str = "File accepted for ingestion. Poll status for readiness."


class ChunkPreview(BaseModel):
    """Document chunk for preview/citation drill-down."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    page_number: Optional[int] = None
    start_index: Optional[int] = None
    content: str


class DocumentPreviewResponse(BaseModel):
    """Document preview with chunks."""

    document: DocumentRead
    chunks: List[ChunkPreview]
    total_chunks: int
