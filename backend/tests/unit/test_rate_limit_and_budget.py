"""Unit tests for sliding-window rate limiting and shared daily LLM quota."""

from datetime import date

import pytest

from app.core.config import Settings
from app.core.errors import LLMDailyBudgetExhaustedError, RateLimitExceededError
from app.core.rate_limit import InMemoryRateLimiter, check_daily_llm_budget
from app.db.repositories import DailyUsageRepository


def test_in_memory_rate_limiter():
    """Verify in-memory sliding window rate limiter triggers on limit."""
    limiter = InMemoryRateLimiter(requests_per_minute=2)
    key = "test_user_key"

    # 1st request succeeds
    limiter.check(key)
    # 2nd request succeeds
    limiter.check(key)

    # 3rd request in same minute raises RateLimitExceededError
    with pytest.raises(RateLimitExceededError):
        limiter.check(key)


def test_daily_llm_budget_enforcement(db_session, monkeypatch):
    """Verify daily LLM budget counter triggers 429 quota exhaustion when limit reached."""
    # Set small budget of 2 for testing
    from app.core import rate_limit

    test_settings = Settings(LLM_DAILY_REQUEST_BUDGET=2, ALLOW_PAID_MODEL=True)
    monkeypatch.setattr(rate_limit, "get_settings", lambda: test_settings)

    # Use today's date
    test_date = date.today()

    # Reset any counter for today
    DailyUsageRepository.increment(db_session, count=2, today=test_date)

    # Next check should exceed budget of 2 and raise LLMDailyBudgetExhaustedError
    with pytest.raises(LLMDailyBudgetExhaustedError) as exc_info:
        check_daily_llm_budget(db=db_session, calls_needed=1)

    assert exc_info.value.code == "llm_daily_budget_exhausted"
    assert "reset_at" in exc_info.value.extra
    assert "T00:00:00Z" in exc_info.value.extra["reset_at"]
