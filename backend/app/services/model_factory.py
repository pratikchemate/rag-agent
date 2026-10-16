"""Model factory for OpenRouter free models with fallback allowlist."""

from typing import List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openrouter import ChatOpenRouter
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    LLMDailyBudgetExhaustedError,
    ResponseTruncatedError,
    ServiceUnavailableError,
)
from app.core.logging import get_logger
from app.core.rate_limit import consume_daily_llm_budget
from app.db.engine import SessionLocal

logger = get_logger(__name__)

# Mock model hook for offline unit tests
_test_model_override: Optional[BaseChatModel] = None


def set_test_model(model: Optional[BaseChatModel]) -> None:
    """Set or clear a test model override for offline test execution."""
    global _test_model_override
    _test_model_override = model


def is_retriable_provider_error(e: Exception) -> bool:
    """Determine whether an error represents a retriable provider outage, timeout, or rate-limit."""
    if isinstance(e, (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError)):
        return False

    status_code = getattr(e, "status_code", None) or getattr(e, "code", None)
    if status_code in (404, 429, 500, 502, 503, 504):
        return True

    err_msg = str(e).lower()
    retriable_signals = (
        "429",
        "rate limit",
        "quota",
        "overloaded",
        "timeout",
        "timed out",
        "time out",
        "unavailable",
        "503",
        "502",
        "504",
        "connection error",
        "connect",
        "network",
        "unreachable",
        "reset by peer",
    )
    if any(sig in err_msg for sig in retriable_signals):
        return True

    import httpx

    if isinstance(e, (TimeoutError, httpx.TimeoutException, httpx.NetworkError)):
        return True

    try:
        import httpcore

        if isinstance(e, (httpcore.TimeoutException, httpcore.NetworkError)):
            return True
    except ImportError:
        pass

    return False


class ModelFactory:
    """Creates and manages ChatOpenRouter instances with fallback logic."""

    @classmethod
    def get_chat_model(cls, model_name: Optional[str] = None) -> BaseChatModel:
        """Instantiate ChatOpenRouter with configured parameters."""
        if _test_model_override is not None:
            return _test_model_override

        settings = get_settings()
        models = settings.get_model_allowlist()
        selected_model = model_name or (models[0] if models else None)
        if not selected_model:
            raise ValueError("No model specified and OPENROUTER_MODELS allowlist is empty.")

        # Startup guard check
        if not settings.ALLOW_PAID_MODEL and not selected_model.endswith(":free"):
            raise ValueError(
                f"Model '{selected_model}' does not end in ':free' and ALLOW_PAID_MODEL is False."
            )

        api_key = settings.get_openrouter_api_key()
        if not api_key:
            raise ServiceUnavailableError(
                "OpenRouter API key is not configured. Please set OPENROUTER_API_KEY to enable LLM generation."
            )

        timeout_ms = int(settings.OPENROUTER_TIMEOUT_SECONDS * 1000)
        return ChatOpenRouter(
            model=selected_model,
            api_key=api_key,
            temperature=0.0,
            max_tokens=settings.MAX_OUTPUT_TOKENS,
            request_timeout=timeout_ms,
            max_retries=settings.OPENROUTER_MAX_RETRIES,
            reasoning={"effort": settings.OPENROUTER_REASONING_EFFORT},
            app_url=settings.OPENROUTER_APP_URL,
            app_title=settings.OPENROUTER_APP_TITLE,
            default_headers={
                "HTTP-Referer": settings.OPENROUTER_APP_URL,
                "X-Title": settings.OPENROUTER_APP_TITLE,
            },
        )

    @classmethod
    def invoke_with_fallback(
        cls, messages: List[BaseMessage], db: Optional[Session] = None
    ) -> BaseMessage:
        """Invoke OpenRouter models across the free allowlist in order on failure."""
        if _test_model_override is not None:
            if db is not None:
                consume_daily_llm_budget(db=db, calls_needed=1)
            return _test_model_override.invoke(messages)

        settings = get_settings()
        models = settings.get_model_allowlist()
        last_error = None

        def _consume_budget():
            if db is not None:
                consume_daily_llm_budget(db=db, calls_needed=1)
            else:
                with SessionLocal() as local_db:
                    consume_daily_llm_budget(db=local_db, calls_needed=1)

        for model_id in models:
            _consume_budget()

            try:
                logger.info(f"Invoking model '{model_id}'")
                chat_model = cls.get_chat_model(model_id)
                response = chat_model.invoke(messages)

                # Check for truncated answer
                finish_reason = getattr(response, "response_metadata", {}).get("finish_reason")
                if finish_reason == "length":
                    logger.error(
                        f"Response from '{model_id}' was truncated due to output length cap."
                    )
                    raise ResponseTruncatedError(
                        f"Response from '{model_id}' was truncated due to output length cap."
                    )

                return response
            except Exception as e:
                if isinstance(e, LLMDailyBudgetExhaustedError):
                    # Raise immediately on budget exhaustion
                    logger.error(f"Stopping model invocation: {str(e)}")
                    raise e

                if isinstance(e, ResponseTruncatedError):
                    logger.warning(
                        f"Model '{model_id}' was truncated due to output length cap. Attempting next in allowlist."
                    )
                    last_error = e
                    continue

                err_str = str(e).lower()
                is_auth_error = (
                    "unauthorized" in err_str
                    or "authentication" in err_str
                    or "api key" in err_str
                    or "missing authentication header" in err_str
                    or getattr(e, "status_code", None) == 401
                )
                if is_auth_error:
                    logger.error(f"OpenRouter authentication failed: {str(e)}")
                    raise ServiceUnavailableError(
                        "OpenRouter API key is missing, unauthorized, or invalid. "
                        "Please configure a valid OPENROUTER_API_KEY in your .env file."
                    )

                if not is_retriable_provider_error(e):
                    logger.error(f"Non-retriable exception invoking model '{model_id}': {str(e)}")
                    raise e

                logger.warning(
                    f"Model '{model_id}' failed: {str(e)}. Attempting next in allowlist."
                )
                last_error = e

        if isinstance(last_error, ResponseTruncatedError):
            raise last_error

        raise ServiceUnavailableError(
            f"All configured free models failed or were unavailable. Last error: {str(last_error)}"
        )
