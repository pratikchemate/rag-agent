"""Seed demo corpus fixtures into database with is_public=True for testing and demo portfolios."""

import hashlib
import sys
import uuid
from pathlib import Path
from uuid import UUID

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.engine import SessionLocal
from app.db.models import Document
from app.services.ingestion import IngestionService
from app.services.storage import get_storage_service

DEMO_OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "evaluation" / "fixtures"


def seed_demo_corpus() -> int:
    """Ingest evaluation/fixtures/*.md as public documents under DEMO_OWNER_ID."""
    if not FIXTURES_DIR.exists():
        print(f"Error: Fixtures directory not found at {FIXTURES_DIR}")
        sys.exit(1)

    db = SessionLocal()
    ingested_count = 0

    try:
        fixture_files = sorted(FIXTURES_DIR.glob("*.md"))
        print(f"Found {len(fixture_files)} fixtures in {FIXTURES_DIR}")

        for file_path in fixture_files:
            with open(file_path, "rb") as f:
                content = f.read()

            checksum = hashlib.sha256(content).hexdigest()

            # Idempotency check: skip if identical checksum already exists for DEMO_OWNER_ID
            existing = (
                db.query(Document)
                .filter(
                    Document.owner_id == DEMO_OWNER_ID,
                    Document.checksum_sha256 == checksum,
                )
                .first()
            )
            if existing:
                print(f"Skipping '{file_path.name}' (already seeded with id={existing.id})")
                continue

            doc_id = uuid.uuid4()
            storage_path = f"demo/{file_path.name}"
            doc = Document(
                id=doc_id,
                owner_id=DEMO_OWNER_ID,
                filename=file_path.name,
                storage_path=storage_path,
                content_type="text/markdown",
                file_size_bytes=len(content),
                checksum_sha256=checksum,
                status="processing",
                is_public=True,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            # Upload original file to storage under demo/...
            try:
                storage = get_storage_service()
                storage.upload_file(storage_path, content, doc.content_type)
            except Exception as e:
                print(f"Warning: Storage upload for '{file_path.name}' failed: {e}")

            print(f"Ingesting '{file_path.name}' (id={doc_id})...")
            IngestionService.process_document_background(
                document_id=doc.id,
                owner_id=DEMO_OWNER_ID,
                filename=doc.filename,
                content=content,
                content_type=doc.content_type,
                storage_path=doc.storage_path,
            )
            ingested_count += 1

        print(f"Successfully seeded {ingested_count} new document(s).")
        return ingested_count
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_corpus()
