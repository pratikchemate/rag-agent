"""Feedback endpoint for answer ratings."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.errors import BadRequestError
from app.core.logging import get_logger
from app.db.engine import get_db
from app.db.repositories import FeedbackRepository
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record user rating and optional comment for a chat answer."""
    if payload.rating not in (-1, 1):
        raise BadRequestError("Rating must be either 1 (positive) or -1 (negative).")

    feedback = FeedbackRepository.create(
        db=db,
        owner_id=user.user_id,
        request_id=payload.request_id,
        rating=payload.rating,
        comment=payload.comment,
    )

    logger.info(
        f"Feedback recorded for request {payload.request_id} by user {user.user_id}: {payload.rating}"
    )
    return FeedbackResponse(
        id=feedback.id,
        request_id=feedback.request_id,
        status="success",
        message="Feedback successfully recorded.",
    )
