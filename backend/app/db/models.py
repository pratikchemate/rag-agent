"""SQLAlchemy ORM models matching database migrations."""

import uuid
from datetime import date, datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.engine import Base


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Document(Base):
    """Document metadata model."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="processing")
    chunk_count = Column(Integer, nullable=False, default=0)
    error_code = Column(String, nullable=True)
    is_public = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Document chunk with text content, embedding vector, and full-text search vector."""

    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    start_index = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    document = relationship("Document", back_populates="chunks")


class Feedback(Base):
    """User feedback for chat responses."""

    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rating = Column(SmallInteger, nullable=False)
    comment = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class DailyUsageCounter(Base):
    """Tracks global daily LLM calls in Postgres to enforce shared free-tier demo quota."""

    __tablename__ = "daily_usage_counters"

    usage_date = Column(Date, primary_key=True, default=date.today)
    call_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
