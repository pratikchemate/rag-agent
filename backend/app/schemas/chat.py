"""Pydantic schemas for chat requests and responses."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat question payload."""

    question: str = Field(..., min_length=1, max_length=2000, description="User question")
    document_ids: Optional[List[UUID]] = Field(
        default=None, description="Optional filter for specific documents"
    )
    top_k: int = Field(default=5, ge=1, le=8, description="Number of source chunks to retrieve")


class Citation(BaseModel):
    """Citation verified and linked to an actual retrieved chunk."""

    label: str
    document_id: UUID
    chunk_id: UUID
    filename: str
    page_number: Optional[int] = None
    excerpt: str


class RetrievalMetadata(BaseModel):
    """Metadata about retrieval execution."""

    mode: str = "hybrid_rrf"
    attempts: int = 1
    returned_chunks: int = 0


class TimingsMetadata(BaseModel):
    """Measured stage execution times in milliseconds."""

    retrieval: float = 0.0
    generation: float = 0.0
    total: float = 0.0


class ChatResponse(BaseModel):
    """Grounded chat response adhering to the API specification."""

    request_id: UUID
    answer: str
    abstained: bool
    citations: List[Citation]
    retrieval: RetrievalMetadata
    timings_ms: TimingsMetadata
