"""Asynchronous document ingestion service."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.engine import SessionLocal
from app.db.models import DocumentChunk
from app.db.repositories import ChunkRepository, DocumentRepository
from app.services.chunking import get_chunking_service
from app.services.document_parser import DocumentParser
from app.services.embeddings import get_embedding_service
from app.services.storage import get_storage_service

logger = get_logger(__name__)


class IngestionService:
    """Manages the lifecycle of parsing, chunking, embedding, and storing documents."""

    @classmethod
    def process_document_background(
        cls,
        document_id: UUID,
        owner_id: UUID,
        filename: str,
        content: bytes,
        content_type: str,
        storage_path: str,
    ) -> None:
        """Run asynchronous ingestion in a background task."""
        db: Session = SessionLocal()
        storage = get_storage_service()
        chunker = get_chunking_service()
        embedder = get_embedding_service()

        try:
            logger.info(f"Starting ingestion for document {document_id} ({filename})")

            # 1. Parse document
            parsed_doc = DocumentParser.validate_and_parse(
                filename=filename,
                content=content,
                declared_content_type=content_type,
            )

            # 2. Split into chunks
            chunk_data_list = chunker.chunk_document(parsed_doc)
            chunk_texts = [c.content for c in chunk_data_list]

            # 3. Generate embeddings locally
            logger.info(f"Generating embeddings for {len(chunk_texts)} chunks of doc {document_id}")
            embeddings = embedder.embed_documents(chunk_texts)

            # 4. Construct DocumentChunk ORM models
            db_chunks = []
            for chunk_data, vector in zip(chunk_data_list, embeddings):
                db_chunk = DocumentChunk(
                    document_id=document_id,
                    owner_id=owner_id,
                    chunk_index=chunk_data.chunk_index,
                    page_number=chunk_data.page_number,
                    start_index=chunk_data.start_index,
                    content=chunk_data.content,
                    embedding=vector,
                )
                db_chunks.append(db_chunk)

            # 5. Persist chunks and update status in a single atomic transaction
            DocumentRepository.save_chunks_and_mark_ready(
                db=db,
                document_id=document_id,
                chunks=db_chunks,
            )
            logger.info(
                f"Successfully processed document {document_id} with {len(db_chunks)} chunks"
            )

        except Exception as e:
            logger.error(f"Ingestion failed for document {document_id}: {str(e)}")
            # Cleanup on failure
            try:
                ChunkRepository.delete_by_document(db, document_id)
                DocumentRepository.update_status(
                    db=db,
                    document_id=document_id,
                    status="failed",
                    chunk_count=0,
                    error_code="ingestion_error",
                )
                storage.delete_file(storage_path)
            except Exception as cleanup_err:
                logger.warning(f"Error during failure cleanup: {str(cleanup_err)}")
        finally:
            db.close()
