"""Rate limiting and daily LLM quota enforcement."""

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import LLMDailyBudgetExhaustedError, RateLimitExceededError
from app.db.repositories import DailyUsageRepository


class InMemoryRateLimiter:
    """Sliding-window rate limiter for requests per minute."""

    def __init__(self, requests_per_minute: int):
        self.rpm = requests_per_minute
        self.window = 60.0  # seconds
        self._history: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        """Check if key is within rate limit; raises RateLimitExceededError if exceeded."""
        now = time.time()
        timestamps = self._history[key]

        # Purge timestamps outside the window
        self._history[key] = [t for t in timestamps if now - t < self.window]

        if len(self._history[key]) >= self.rpm:
            raise RateLimitExceededError(
                f"Rate limit exceeded: maximum {self.rpm} requests per minute."
            )
        self._history[key].append(now)

    def clear(self) -> None:
        """Clear all rate limit history."""
        self._history.clear()


# Global instances for chat and upload endpoints
_chat_limiter: Optional[InMemoryRateLimiter] = None
_upload_limiter: Optional[InMemoryRateLimiter] = None


def get_chat_limiter() -> InMemoryRateLimiter:
    """Return chat rate limiter."""
    global _chat_limiter
    if _chat_limiter is None:
        settings = get_settings()
        _chat_limiter = InMemoryRateLimiter(settings.CHAT_RATE_LIMIT_PER_MINUTE)
    return _chat_limiter


def get_upload_limiter() -> InMemoryRateLimiter:
    """Return upload rate limiter."""
    global _upload_limiter
    if _upload_limiter is None:
        settings = get_settings()
        _upload_limiter = InMemoryRateLimiter(settings.UPLOAD_RATE_LIMIT_PER_MINUTE)
    return _upload_limiter


def consume_daily_llm_budget(db: Session, calls_needed: int = 1) -> None:
    """Check and atomically consume shared free-tier daily LLM quota; raises 429 if exhausted."""
    settings = get_settings()
    success, current = DailyUsageRepository.try_consume_budget(
        db, max_budget=settings.LLM_DAILY_REQUEST_BUDGET, count=calls_needed
    )
    if not success:
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).date()
        reset_at = f"{tomorrow.isoformat()}T00:00:00Z"
        raise LLMDailyBudgetExhaustedError(
            reset_at=reset_at,
            message=f"The shared demo quota for today has been used. It resets at {reset_at}.",
        )


# Backward-compatibility alias
check_daily_llm_budget = consume_daily_llm_budget
