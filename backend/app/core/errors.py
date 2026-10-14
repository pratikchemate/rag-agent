"""Application exceptions and error definitions."""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception with structured error details."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.extra = extra or {}
        super().__init__(message)


class UnauthorizedError(AppException):
    """401 Unauthorized."""

    def __init__(
        self, message: str = "Authentication required or token invalid", code: str = "unauthorized"
    ):
        super().__init__(status_code=401, code=code, message=message)


class ForbiddenError(AppException):
    """403 Forbidden."""

    def __init__(
        self, message: str = "Access denied to requested resource", code: str = "forbidden"
    ):
        super().__init__(status_code=403, code=code, message=message)


class NotFoundError(AppException):
    """404 Not Found."""

    def __init__(self, message: str = "Resource not found", code: str = "not_found"):
        super().__init__(status_code=404, code=code, message=message)


class ConflictError(AppException):
    """409 Conflict (e.g. duplicate document)."""

    def __init__(
        self,
        message: str = "Resource already exists",
        code: str = "conflict",
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=409, code=code, message=message, extra=extra)


class BadRequestError(AppException):
    """400 Bad Request."""

    def __init__(self, message: str = "Invalid request", code: str = "bad_request"):
        super().__init__(status_code=400, code=code, message=message)


class PayloadTooLargeError(AppException):
    """413 Payload Too Large."""

    def __init__(
        self, message: str = "Payload exceeds maximum allowed size", code: str = "payload_too_large"
    ):
        super().__init__(status_code=413, code=code, message=message)


class UnsupportedMediaTypeError(AppException):
    """415 Unsupported Media Type."""

    def __init__(
        self,
        message: str = "Unsupported media type or format",
        code: str = "unsupported_media_type",
    ):
        super().__init__(status_code=415, code=code, message=message)


class RateLimitExceededError(AppException):
    """429 Rate Limit Exceeded (per-user or IP)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        code: str = "rate_limit_exceeded",
    ):
        super().__init__(status_code=429, code=code, message=message)


class LLMDailyBudgetExhaustedError(AppException):
    """429 Shared Free-Tier LLM Quota Exhausted."""

    def __init__(self, reset_at: str, message: Optional[str] = None):
        msg = message or f"The shared demo quota for today has been used. It resets at {reset_at}."
        super().__init__(
            status_code=429,
            code="llm_daily_budget_exhausted",
            message=msg,
            extra={"reset_at": reset_at},
        )


class ServiceUnavailableError(AppException):
    """503 Service Unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable. Please retry later.",
        code: str = "service_unavailable",
    ):
        super().__init__(status_code=503, code=code, message=message)


class ResponseTruncatedError(AppException):
    """502 Bad Gateway / Model Output Truncated."""

    def __init__(
        self,
        message: str = "Language model response was truncated due to output length limits",
        code: str = "response_truncated",
    ):
        super().__init__(status_code=502, code=code, message=message)
