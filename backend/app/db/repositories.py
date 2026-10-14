"""Database repositories for documents, chunks, usage counters, and feedback."""

from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.db.models import DailyUsageCounter, Document, DocumentChunk, Feedback


class DocumentRepository:
    """Repository for document metadata and ownership enforcement."""

    @staticmethod
    def get_by_id(
        db: Session,
        document_id: UUID,
        owner_id: UUID,
        allow_public: bool = False,
    ) -> Optional[Document]:
        """Fetch document if owned by user or if public."""
        stmt = select(Document).where(Document.id == document_id)
        if allow_public:
            stmt = stmt.where(or_(Document.owner_id == owner_id, Document.is_public.is_(True)))
        else:
            stmt = stmt.where(Document.owner_id == owner_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_visible_documents(db: Session, owner_id: UUID) -> List[Document]:
        """List documents owned by user plus seeded public demo documents."""
        stmt = (
            select(Document)
            .where(or_(Document.owner_id == owner_id, Document.is_public.is_(True)))
            .order_by(Document.created_at.desc())
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_by_checksum(db: Session, owner_id: UUID, checksum: str) -> Optional[Document]:
        """Find non-failed document by owner and content checksum."""
        stmt = select(Document).where(
            Document.owner_id == owner_id,
            Document.checksum_sha256 == checksum,
            Document.status != "failed",
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def count_by_owner(db: Session, owner_id: UUID) -> int:
        """Count total private documents owned by user."""
        stmt = (
            select(func.count())
            .select_from(Document)
            .where(
                Document.owner_id == owner_id,
                Document.is_public.is_(False),
            )
        )
        return db.execute(stmt).scalar() or 0

    @staticmethod
    def create(db: Session, document: Document) -> Document:
        """Persist new document."""
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    @staticmethod
    def update_status(
        db: Session,
        document_id: UUID,
        status: str,
        chunk_count: int = 0,
        error_code: Optional[str] = None,
    ) -> Optional[Document]:
        """Update status, chunk count, and error code."""
        doc = db.get(Document, document_id)
        if doc:
            doc.status = status
            doc.chunk_count = chunk_count
            doc.error_code = error_code
            doc.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(doc)
        return doc

    @staticmethod
    def save_chunks_and_mark_ready(
        db: Session,
        document_id: UUID,
        chunks: List[DocumentChunk],
    ) -> Optional[Document]:
        """Atomically persist chunks and update document status to ready within a single transaction."""
        doc = db.get(Document, document_id)
        if not doc:
            raise NotFoundError(f"Document {document_id} not found")

        if chunks:
            db.add_all(chunks)

        doc.status = "ready"
        doc.chunk_count = len(chunks)
        doc.error_code = None
        doc.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def delete(db: Session, document_id: UUID, owner_id: UUID) -> Document:
        """Delete user's document. Rejects public demo documents with 403."""
        doc = db.get(Document, document_id)
        if not doc or (doc.owner_id != owner_id and not doc.is_public):
            raise NotFoundError("Document not found")
        if doc.is_public:
            raise ForbiddenError("Public demo corpus documents cannot be deleted")
        if doc.owner_id != owner_id:
            raise NotFoundError("Document not found")

        db.delete(doc)
        db.commit()
        return doc


class ChunkRepository:
    """Repository for document chunks and vector persistence."""

    @staticmethod
    def create_chunks(db: Session, chunks: List[DocumentChunk]) -> None:
        """Batch insert chunks."""
        if not chunks:
            return
        db.add_all(chunks)
        db.commit()

    @staticmethod
    def get_chunks_by_document(
        db: Session,
        document_id: UUID,
        owner_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[DocumentChunk]:
        """Get paginated chunks for preview after verifying document visibility."""
        doc = DocumentRepository.get_by_id(db, document_id, owner_id, allow_public=True)
        if not doc:
            raise NotFoundError("Document not found")

        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def count_chunks_by_document(db: Session, document_id: UUID) -> int:
        """Count total chunks belonging to document."""
        stmt = (
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        return db.execute(stmt).scalar() or 0

    @staticmethod
    def delete_by_document(db: Session, document_id: UUID) -> None:
        """Delete chunks belonging to document."""
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        chunks = db.execute(stmt).scalars().all()
        for chunk in chunks:
            db.delete(chunk)
        db.commit()


class DailyUsageRepository:
    """Repository for tracking global daily LLM calls in Postgres."""

    @staticmethod
    def get_today_count(db: Session, today: Optional[date] = None) -> int:
        """Fetch current call count for today."""
        target_date = today or datetime.now(timezone.utc).date()
        record = db.get(DailyUsageCounter, target_date)
        return record.call_count if record else 0

    @staticmethod
    def try_consume_budget(
        db: Session,
        max_budget: int,
        count: int = 1,
        today: Optional[date] = None,
    ) -> tuple[bool, int]:
        """Atomically increment daily LLM usage counter only if within max_budget.

        Returns:
            (success: bool, new_count: int)
        """
        target_date = today or datetime.now(timezone.utc).date()
        now = datetime.now(timezone.utc)

        stmt = (
            insert(DailyUsageCounter)
            .values(usage_date=target_date, call_count=count, updated_at=now)
            .on_conflict_do_update(
                index_elements=[DailyUsageCounter.usage_date],
                set_={
                    "call_count": DailyUsageCounter.call_count + count,
                    "updated_at": now,
                },
                where=(DailyUsageCounter.call_count + count <= max_budget),
            )
            .returning(DailyUsageCounter.call_count)
        )
        result = db.execute(stmt).scalar()
        if result is not None:
            db.commit()
            return True, result

        db.rollback()
        current = DailyUsageRepository.get_today_count(db, target_date)
        return False, current

    @staticmethod
    def increment(db: Session, count: int = 1, today: Optional[date] = None) -> int:
        """Atomically increment daily LLM usage counter."""
        target_date = today or datetime.now(timezone.utc).date()
        now = datetime.now(timezone.utc)

        stmt = (
            insert(DailyUsageCounter)
            .values(usage_date=target_date, call_count=count, updated_at=now)
            .on_conflict_do_update(
                index_elements=[DailyUsageCounter.usage_date],
                set_={
                    "call_count": DailyUsageCounter.call_count + count,
                    "updated_at": now,
                },
            )
            .returning(DailyUsageCounter.call_count)
        )
        result = db.execute(stmt).scalar()
        db.commit()
        return result or count


class FeedbackRepository:
    """Repository for chat answer feedback."""

    @staticmethod
    def create(
        db: Session,
        owner_id: UUID,
        request_id: UUID,
        rating: int,
        comment: Optional[str] = None,
    ) -> Feedback:
        """Save user feedback."""
        feedback = Feedback(
            owner_id=owner_id,
            request_id=request_id,
            rating=rating,
            comment=comment,
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
