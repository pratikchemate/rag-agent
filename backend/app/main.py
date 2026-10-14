"""Enterprise Knowledge AI FastAPI Application."""

import re
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import chat, documents, feedback, health
from app.core.config import get_settings
from app.core.errors import AppException
from app.core.logging import configure_logging, get_logger, request_id_ctx

settings = get_settings()
configure_logging(level=settings.LOG_LEVEL)
logger = get_logger("enterprise_knowledge_ai")

REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events."""
    logger.info(
        f"Starting Enterprise Knowledge AI (env={settings.ENVIRONMENT}, models={settings.OPENROUTER_MODELS})"
    )
    yield
    logger.info("Shutting down Enterprise Knowledge AI")


app = FastAPI(
    title="Enterprise Knowledge AI API",
    description="Evidence-grounded retrieval-augmented generation (RAG) assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Assign or propagate unique request ID for distributed tracing and logging."""
    raw_header = request.headers.get("X-Request-ID", "").strip()
    if raw_header and REQUEST_ID_REGEX.match(raw_header):
        req_id = raw_header
    else:
        req_id = str(uuid.uuid4())

    token = request_id_ctx.set(req_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
    finally:
        request_id_ctx.reset(token)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions."""
    req_id = request_id_ctx.get()
    content = {
        "request_id": req_id,
        "code": exc.code,
        "message": exc.message,
    }
    if exc.extra:
        content.update(exc.extra)
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic request schema validation errors without echoing raw inputs."""
    req_id = request_id_ctx.get()
    sanitized_errors = []
    for err in exc.errors():
        err_copy = dict(err)
        err_copy.pop("input", None)
        sanitized_errors.append(err_copy)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "request_id": req_id,
            "code": "validation_error",
            "message": "Invalid request parameters.",
            "details": sanitized_errors,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle standard FastAPI HTTP exceptions."""
    req_id = request_id_ctx.get()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "request_id": req_id,
            "code": "http_error",
            "message": str(exc.detail),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler ensuring internal stack traces are never leaked."""
    req_id = request_id_ctx.get()
    logger.error(f"Unhandled server error [req_id={req_id}]: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "request_id": req_id,
            "code": "internal_error",
            "message": "An internal server error occurred. Please try again later.",
        },
    )


# Register Routers
app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(documents.router, prefix=settings.API_PREFIX)
app.include_router(chat.router, prefix=settings.API_PREFIX)
app.include_router(feedback.router, prefix=settings.API_PREFIX)


@app.get("/", tags=["Root"])
def root_info():
    """Root info endpoint."""
    return {
        "name": "Enterprise Knowledge AI API",
        "version": "0.1.0",
        "status": "online",
        "docs_url": "/docs",
    }
