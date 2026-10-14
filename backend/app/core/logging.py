"""Structured logging configuration for Enterprise Knowledge AI."""

import contextvars
import json
import logging
import sys
from typing import Any, Dict, Optional

# Context variable for tracing request IDs across async boundaries
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)

SENSITIVE_KEYS = {
    "authorization",
    "bearer",
    "token",
    "api_key",
    "secret",
    "password",
    "openrouter_api_key",
    "supabase_secret_key",
}


def sanitize_data(data: Any) -> Any:
    """Recursively mask sensitive values in dictionaries and lists."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(s in str(k).lower() for s in SENSITIVE_KEYS):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = sanitize_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON without leaking sensitive information."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_ctx.get() or getattr(record, "request_id", None)
        log_payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if req_id:
            log_payload["request_id"] = req_id

        # Attach custom extra fields if provided
        if hasattr(record, "stage"):
            log_payload["stage"] = record.stage
        if hasattr(record, "timings_ms"):
            log_payload["timings_ms"] = record.timings_ms
        if hasattr(record, "metadata"):
            log_payload["metadata"] = sanitize_data(record.metadata)

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            log_payload["exception"] = record.exc_text

        return json.dumps(log_payload)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with structured JSON formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # Avoid duplicate handlers on reload
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for the application."""
    return logging.getLogger(name)
