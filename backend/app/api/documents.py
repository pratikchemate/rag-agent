"""Document management API endpoints."""

import hashlib
import uuid
from typing import List
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser, get_current_user, get_current_user_optional
from app.core.config import get_settings
from app.core.errors import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.core.logging import get_logger
from app.core.rate_limit import get_upload_limiter
from app.db.engine import get_db
from app.db.models import Document
from app.db.repositories import ChunkRepository, DocumentRepository
from app.schemas.documents import (
    ChunkPreview,
    DocumentPreviewResponse,
    DocumentRead,
    DocumentUploadResponse,
)
from app.services.document_parser import DocumentParser
from app.services.ingestion import IngestionService
from app.services.storage import get_storage_service

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUploadResponse,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload document for asynchronous ingestion pipeline (HTTP 202)."""
    if user.role == "anonymous":
        raise UnauthorizedError(
            "Authentication required to upload documents. Please sign in with an invited reviewer account."
        )

    settings = get_settings()

    # 1. Rate limiting
    upload_limiter = get_upload_limiter()
    upload_limiter.check(str(user.user_id))

    # 2. Check user document quota
    current_doc_count = DocumentRepository.count_by_owner(db, user.user_id)
    if current_doc_count >= settings.MAX_DOCUMENTS_PER_USER:
        raise BadRequestError(
            f"Document quota reached ({settings.MAX_DOCUMENTS_PER_USER} documents maximum per user)."
        )

    # 3. Stream content with maximum byte threshold
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    chunk_size = 64 * 1024
    total_read = 0
    chunks = []

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > max_bytes:
            raise PayloadTooLargeError(
                f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_MB}MB."
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    file_size = len(content)
    if file_size == 0:
        raise BadRequestError("Uploaded file is empty.")

    filename = file.filename or "uploaded_document"
    declared_type = file.content_type or "application/octet-stream"

    # 4. Immediate format & magic bytes validation (returns 415 before async 202)
    resolved_content_type = DocumentParser.validate_file_format(
        filename=filename, content=content, declared_content_type=declared_type
    )

    # 5. Deduplication by SHA-256
    checksum = hashlib.sha256(content).hexdigest()
    existing_doc = DocumentRepository.get_by_checksum(db, user.user_id, checksum)
    if existing_doc:
        raise ConflictError(
            message=f"A document with identical content already exists: '{existing_doc.filename}'",
            extra={"existing_document_id": str(existing_doc.id)},
        )

    # 6. Database insertion before storage upload (prevents orphaned object on conflict)
    doc_id = uuid.uuid4()
    storage = get_storage_service()
    storage_path = storage.generate_storage_path(user.user_id, doc_id, filename)

    doc = Document(
        id=doc_id,
        owner_id=user.user_id,
        filename=filename,
        storage_path=storage_path,
        content_type=resolved_content_type,
        file_size_bytes=file_size,
        checksum_sha256=checksum,
        status="processing",
        chunk_count=0,
        is_public=False,
    )
    DocumentRepository.create(db, doc)

    # 7. Upload to object storage
    try:
        storage.upload_file(storage_path, content, resolved_content_type)
    except Exception as upload_err:
        DocumentRepository.delete(db, doc_id, user.user_id)
        raise ServiceUnavailableError(f"Failed to persist file to storage: {str(upload_err)}")

    # 8. Dispatch background ingestion task
    background_tasks.add_task(
        IngestionService.process_document_background,
        document_id=doc_id,
        owner_id=user.user_id,
        filename=filename,
        content=content,
        content_type=resolved_content_type,
        storage_path=storage_path,
    )

    logger.info(f"Accepted upload for document {doc_id} from user {user.user_id}")
    return DocumentUploadResponse(
        document_id=doc_id,
        filename=filename,
        status="processing",
        message="Document accepted for processing. Poll status for readiness.",
    )


@router.get("", response_model=List[DocumentRead])
def list_documents(
    user: AuthenticatedUser = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """List documents owned by the user plus seeded public demo documents."""
    docs = DocumentRepository.list_visible_documents(db, user.user_id)
    return docs


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get metadata for a specific document."""
    doc = DocumentRepository.get_by_id(db, document_id, user.user_id, allow_public=True)
    if not doc:
        raise NotFoundError("Document not found")
    return doc


@router.get("/{document_id}/preview", response_model=DocumentPreviewResponse)
def preview_document(
    document_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get chunks preview for citation drill-down."""
    doc = DocumentRepository.get_by_id(db, document_id, user.user_id, allow_public=True)
    if not doc:
        raise NotFoundError("Document not found")

    chunks = ChunkRepository.get_chunks_by_document(
        db=db,
        document_id=document_id,
        owner_id=user.user_id,
        limit=limit,
        offset=offset,
    )
    total_chunks = ChunkRepository.count_chunks_by_document(db, document_id)

    return DocumentPreviewResponse(
        document=DocumentRead.model_validate(doc),
        chunks=[ChunkPreview.model_validate(c) for c in chunks],
        total_chunks=total_chunks,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document and its stored chunks/file. Rejects public corpus with 403."""
    if user.role == "anonymous":
        raise UnauthorizedError("Authentication required to delete documents.")
    doc = DocumentRepository.get_by_id(db, document_id, user.user_id, allow_public=True)
    if not doc:
        raise NotFoundError("Document not found")

    storage_path = doc.storage_path
    # Delete from database (validates not public)
    DocumentRepository.delete(db, document_id, user.user_id)

    # Clean up storage object
    storage = get_storage_service()
    storage.delete_file(storage_path)

    logger.info(f"Deleted document {document_id} by user {user.user_id}")
    return None
