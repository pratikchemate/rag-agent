"""Health and readiness check endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.engine import get_db

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", status_code=status.HTTP_200_OK)
def live_check():
    """Liveness probe returning 200 when application process is running."""
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
def ready_check(db: Session = Depends(get_db)):
    """Readiness probe checking database connectivity without leaking internals."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "code": "database_unavailable"},
        )
