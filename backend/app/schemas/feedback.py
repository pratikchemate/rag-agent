"""Pydantic schemas for feedback operations."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """Payload for submitting feedback on a chat answer."""

    request_id: UUID = Field(..., description="Request ID of the chat response")
    rating: int = Field(..., description="Rating score: 1 (positive) or -1 (negative)")
    comment: Optional[str] = Field(
        default=None, max_length=1000, description="Optional feedback comment"
    )


class FeedbackResponse(BaseModel):
    """Response confirming saved feedback."""

    id: UUID
    request_id: UUID
    status: str = "success"
    message: str = "Feedback recorded"
