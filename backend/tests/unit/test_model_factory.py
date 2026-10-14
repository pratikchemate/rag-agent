"""Unit tests for ModelFactory fallback, length truncation, and error handling."""

from datetime import date
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.core import rate_limit
from app.core.config import Settings
from app.core.errors import (
    LLMDailyBudgetExhaustedError,
    ResponseTruncatedError,
    ServiceUnavailableError,
)
from app.db.repositories import DailyUsageRepository
from app.services import model_factory
from app.services.model_factory import ModelFactory


def test_finish_reason_length_raises_response_truncated_error(monkeypatch):
    """Verify that finish_reason='length' raises ResponseTruncatedError instead of returning broken response."""
    # Ensure test model override is None
    monkeypatch.setattr(model_factory, "_test_model_override", None)

    mock_chat = MagicMock()
    truncated_msg = AIMessage(
        content="Incomplete sentence citing [S1] but clip",
        response_metadata={"finish_reason": "length"},
    )
    mock_chat.invoke.return_value = truncated_msg
    monkeypatch.setattr(ModelFactory, "get_chat_model", lambda name=None: mock_chat)

    with pytest.raises(ResponseTruncatedError, match="truncated due to output length cap"):
        ModelFactory.invoke_with_fallback([HumanMessage(content="Hello")])


def test_non_retriable_error_raises_immediately(monkeypatch):
    """Verify that non-retriable programming errors (e.g. TypeError) are not caught by provider fallback."""
    monkeypatch.setattr(model_factory, "_test_model_override", None)

    mock_chat = MagicMock()
    mock_chat.invoke.side_effect = TypeError("Invalid argument type")
    monkeypatch.setattr(ModelFactory, "get_chat_model", lambda name=None: mock_chat)

    with pytest.raises(TypeError, match="Invalid argument type"):
        ModelFactory.invoke_with_fallback([HumanMessage(content="Hello")])


def test_retriable_error_cascades_to_fallback(monkeypatch):
    """Verify that 429 rate limit errors cascade to next model in allowlist."""
    monkeypatch.setattr(model_factory, "_test_model_override", None)

    settings = Settings(
        OPENROUTER_MODELS="model1:free,model2:free",
        ALLOW_PAID_MODEL=True,
    )
    monkeypatch.setattr(model_factory, "get_settings", lambda: settings)

    m1 = MagicMock()
    m1.invoke.side_effect = RuntimeError("429 Too Many Requests: Rate limit exceeded")

    m2 = MagicMock()
    m2.invoke.return_value = AIMessage(
        content="Success from model 2 [S1]",
        response_metadata={"finish_reason": "stop"},
    )

    def mock_get_chat_model(name):
        return m1 if name == "model1:free" else m2

    monkeypatch.setattr(ModelFactory, "get_chat_model", mock_get_chat_model)

    res = ModelFactory.invoke_with_fallback([HumanMessage(content="Hello")])
    assert res.content == "Success from model 2 [S1]"


def test_all_models_failing_raises_service_unavailable(monkeypatch):
    """Verify that when all models in allowlist fail with provider errors, 503 is raised."""
    monkeypatch.setattr(model_factory, "_test_model_override", None)

    settings = Settings(
        OPENROUTER_MODELS="model1:free,model2:free",
        ALLOW_PAID_MODEL=True,
    )
    monkeypatch.setattr(model_factory, "get_settings", lambda: settings)

    m = MagicMock()
    m.invoke.side_effect = RuntimeError("503 Service Unavailable: upstream timeout")
    monkeypatch.setattr(ModelFactory, "get_chat_model", lambda name: m)

    with pytest.raises(ServiceUnavailableError, match="All configured free models failed"):
        ModelFactory.invoke_with_fallback([HumanMessage(content="Hello")])


def test_fallback_attempts_charge_daily_budget_per_model(db_session, monkeypatch):
    """Verify that each fallback attempt consumes one unit of the daily LLM budget."""
    monkeypatch.setattr(model_factory, "_test_model_override", None)

    settings = Settings(
        OPENROUTER_MODELS="model1:free,model2:free",
        ALLOW_PAID_MODEL=True,
        LLM_DAILY_REQUEST_BUDGET=10,
    )
    monkeypatch.setattr(model_factory, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limit, "get_settings", lambda: settings)

    m1 = MagicMock()
    m1.invoke.side_effect = RuntimeError("503 Service Unavailable: upstream timeout")

    m2 = MagicMock()
    m2.invoke.return_value = AIMessage(
        content="Success from model 2 [S1]",
        response_metadata={"finish_reason": "stop"},
    )

    def mock_get_chat_model(name):
        return m1 if name == "model1:free" else m2

    monkeypatch.setattr(ModelFactory, "get_chat_model", mock_get_chat_model)

    today = date.today()
    initial_usage = DailyUsageRepository.get_today_count(db_session, today=today)

    res = ModelFactory.invoke_with_fallback([HumanMessage(content="Hello")], db=db_session)
    assert res.content == "Success from model 2 [S1]"

    # Usage must have increased by 2 (1 for model1 failure + 1 for model2 success)
    new_usage = DailyUsageRepository.get_today_count(db_session, today=today)
    assert new_usage == initial_usage + 2


def test_budget_exhaustion_during_fallback_stops_mid_loop(db_session, monkeypatch):
    """Verify that when budget is exhausted before fallback attempt, 429 error is raised."""
    monkeypatch.setattr(model_factory, "_test_model_override", None)

    # Budget of exactly 1
    settings = Settings(
        OPENROUTER_MODELS="model1:free,model2:free",
        ALLOW_PAID_MODEL=True,
        LLM_DAILY_REQUEST_BUDGET=1,
    )
    monkeypatch.setattr(model_factory, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limit, "get_settings", lambda: settings)

    m1 = MagicMock()
    m1.invoke.side_effect = RuntimeError("503 Service Unavailable: upstream timeout")

    m2 = MagicMock()
    m2.invoke.return_value = AIMessage(
        content="Should never reach here [S1]",
        response_metadata={"finish_reason": "stop"},
    )

    def mock_get_chat_model(name):
        return m1 if name == "model1:free" else m2

    monkeypatch.setattr(ModelFactory, "get_chat_model", mock_get_chat_model)

    # Attempt 1 consumes the 1 allowed call, fails with 503.
    # Attempt 2 tries to consume budget, finds budget exhausted, raises LLMDailyBudgetExhaustedError
    with pytest.raises(LLMDailyBudgetExhaustedError) as exc_info:
        ModelFactory.invoke_with_fallback([HumanMessage(content="Hello")], db=db_session)

    assert exc_info.value.code == "llm_daily_budget_exhausted"
