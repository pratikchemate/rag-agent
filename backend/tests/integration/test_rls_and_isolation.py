"""Integration tests for tenant isolation, partial unique index, and Row-Level Security (RLS)."""

import uuid

from sqlalchemy import text

from app.db.models import Document
from app.db.repositories import DocumentRepository
from tests.conftest import TEST_USER_A, TEST_USER_B


def test_row_level_security_enabled_on_all_tables(db_session):
    """Verify that Row Level Security (RLS) is enabled on all tables in postgres."""
    tables = ["documents", "document_chunks", "feedback", "daily_usage_counters"]
    for table_name in tables:
        sql = f"""
            SELECT relrowsecurity
            FROM pg_class
            WHERE relname = '{table_name}' AND relnamespace = 'public'::regnamespace;
        """
        row = db_session.execute(text(sql)).fetchone()
        assert row is not None, f"Table {table_name} not found"
        assert row[0] is True, f"RLS is NOT enabled on table {table_name}"


def test_anon_role_cannot_read_rows_via_rls(db_session):
    """Verify that a client query executed as 'anon' role returns 0 rows due to RLS."""
    # Create anon role in postgres if it does not exist (simulating Supabase anon role)
    db_session.execute(
        text(
            "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN CREATE ROLE anon; END IF; END $$;"
        )
    )
    db_session.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;"))
    db_session.commit()

    # Insert a document as postgres superuser
    doc_id = uuid.uuid4()
    db_session.execute(
        text("""
            INSERT INTO documents (id, owner_id, filename, storage_path, content_type, file_size_bytes, checksum_sha256, status, is_public)
            VALUES (:id, :owner, 'secret.txt', 'p/secret.txt', 'text/plain', 100, 'sec_hash', 'ready', false)
        """),
        {"id": str(doc_id), "owner": str(TEST_USER_A)},
    )
    db_session.commit()

    # Execute query as 'anon' role
    db_session.execute(text("SET LOCAL ROLE anon;"))
    anon_rows = db_session.execute(text("SELECT * FROM documents;")).fetchall()
    db_session.execute(text("RESET ROLE;"))

    assert len(anon_rows) == 0, (
        "Anon role must get 0 rows back because RLS default posture is deny-all"
    )


def test_tenant_isolation_user_a_cannot_access_user_b_documents(
    client, db_session, auth_headers_user_a, auth_headers_user_b
):
    """Verify that User A cannot read, preview, or delete User B's documents."""
    # User B creates a private document
    doc_b_id = uuid.uuid4()
    doc_b = Document(
        id=doc_b_id,
        owner_id=TEST_USER_B,
        filename="user_b_confidential.pdf",
        storage_path="b/doc.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        checksum_sha256="checksum_b_123",
        status="ready",
        chunk_count=2,
        is_public=False,
    )
    DocumentRepository.create(db_session, doc_b)

    # 1. User A tries to GET document B -> 404
    resp_get = client.get(f"/api/v1/documents/{doc_b_id}", headers=auth_headers_user_a)
    assert resp_get.status_code == 404

    # 2. User A tries to PREVIEW document B -> 404
    resp_preview = client.get(f"/api/v1/documents/{doc_b_id}/preview", headers=auth_headers_user_a)
    assert resp_preview.status_code == 404

    # 3. User A tries to DELETE document B -> 404
    resp_delete = client.delete(f"/api/v1/documents/{doc_b_id}", headers=auth_headers_user_a)
    assert resp_delete.status_code == 404

    # 4. User B can access own document -> 200
    resp_b = client.get(f"/api/v1/documents/{doc_b_id}", headers=auth_headers_user_b)
    assert resp_b.status_code == 200
    assert resp_b.json()["filename"] == "user_b_confidential.pdf"


def test_partial_unique_index_allows_reupload_after_failed(db_session):
    """Verify partial unique index on (owner_id, checksum_sha256) permits re-upload after a failed ingest."""
    owner_id = uuid.uuid4()
    checksum = "identical_checksum_456"

    # 1. First upload fails
    failed_doc = Document(
        id=uuid.uuid4(),
        owner_id=owner_id,
        filename="broken.pdf",
        storage_path="b/broken.pdf",
        content_type="application/pdf",
        file_size_bytes=100,
        checksum_sha256=checksum,
        status="failed",
    )
    DocumentRepository.create(db_session, failed_doc)

    # 2. Re-upload of same checksum for same owner succeeds because status <> 'failed' filter
    retry_doc = Document(
        id=uuid.uuid4(),
        owner_id=owner_id,
        filename="retry.pdf",
        storage_path="b/retry.pdf",
        content_type="application/pdf",
        file_size_bytes=100,
        checksum_sha256=checksum,
        status="processing",
    )
    DocumentRepository.create(db_session, retry_doc)
    assert retry_doc.id is not None


def test_public_demo_corpus_visible_and_immutable(client, db_session, auth_headers_user_a):
    """Verify that public demo documents are visible in listings to any user but cannot be deleted (HTTP 403)."""
    demo_owner = uuid.UUID("00000000-0000-0000-0000-000000000001")
    demo_doc = Document(
        id=uuid.uuid4(),
        owner_id=demo_owner,
        filename="public_demo_guide.md",
        storage_path="demo/public_demo_guide.md",
        content_type="text/markdown",
        file_size_bytes=512,
        checksum_sha256="public_demo_sha_12345",
        status="ready",
        chunk_count=1,
        is_public=True,
    )
    DocumentRepository.create(db_session, demo_doc)

    # 1. User A lists documents -> sees public demo doc
    resp_list = client.get("/api/v1/documents", headers=auth_headers_user_a)
    assert resp_list.status_code == 200
    filenames = [d["filename"] for d in resp_list.json()]
    assert "public_demo_guide.md" in filenames

    # 2. User A gets metadata for public demo doc -> 200
    resp_get = client.get(f"/api/v1/documents/{demo_doc.id}", headers=auth_headers_user_a)
    assert resp_get.status_code == 200
    assert resp_get.json()["is_public"] is True

    # 3. User A attempts DELETE on public demo doc -> 403 Forbidden
    resp_del = client.delete(f"/api/v1/documents/{demo_doc.id}", headers=auth_headers_user_a)
    assert resp_del.status_code == 403
    assert resp_del.json()["code"] == "forbidden"

