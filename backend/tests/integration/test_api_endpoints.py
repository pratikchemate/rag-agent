"""Integration tests for all REST API endpoints."""

import io
import uuid

import pytest
from sqlalchemy import text

from app.db.models import Document
from app.db.repositories import DocumentRepository
from tests.conftest import TEST_USER_A


def test_health_endpoints(client):
    """Test health live and readiness endpoints."""
    # 1. Live
    live_resp = client.get("/api/v1/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json() == {"status": "ok"}

    # 2. Ready
    ready_resp = client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"


def test_unauthenticated_request_rejected(client):
    """Verify write endpoints require authentication (401) while GET returns public docs."""
    # Upload requires authentication
    content = b"Sample upload content"
    upload_resp = client.post(
        "/api/v1/documents",
        files={"file": ("unauth.txt", io.BytesIO(content), "text/plain")},
    )
    assert upload_resp.status_code == 401
    assert upload_resp.json()["code"] == "unauthorized"

    # Delete requires authentication
    delete_resp = client.delete(f"/api/v1/documents/{uuid.uuid4()}")
    assert delete_resp.status_code == 401
    assert delete_resp.json()["code"] == "unauthorized"

    # GET /documents allows unauthenticated demo access and returns 200 list
    list_resp = client.get("/api/v1/documents")
    assert list_resp.status_code == 200
    assert isinstance(list_resp.json(), list)


def test_upload_and_list_documents(client, auth_headers_user_a):
    """Verify document upload returns 202 and appears in user document list."""
    content = b"This is a test document content for knowledge assistant."
    file_tuple = ("test_doc.txt", io.BytesIO(content), "text/plain")

    # 1. Upload
    upload_resp = client.post(
        "/api/v1/documents",
        files={"file": file_tuple},
        headers=auth_headers_user_a,
    )
    assert upload_resp.status_code == 202
    data = upload_resp.json()
    assert data["status"] == "processing"
    assert "document_id" in data
    doc_id = data["document_id"]

    # 2. List
    list_resp = client.get("/api/v1/documents", headers=auth_headers_user_a)
    assert list_resp.status_code == 200
    docs = list_resp.json()
    assert any(d["id"] == doc_id for d in docs)


def test_public_demo_document_cannot_be_deleted(client, db_session, auth_headers_user_a):
    """Verify that seeded public demo corpus documents cannot be deleted by any user (403)."""
    public_doc_id = uuid.uuid4()
    public_doc = Document(
        id=public_doc_id,
        owner_id=uuid.uuid4(),  # System/admin owner
        filename="public_guide.pdf",
        storage_path="public/public_guide.pdf",
        content_type="application/pdf",
        file_size_bytes=500,
        checksum_sha256="public_checksum_123",
        status="ready",
        chunk_count=1,
        is_public=True,
    )
    DocumentRepository.create(db_session, public_doc)

    # User A attempts to delete public document
    del_resp = client.delete(f"/api/v1/documents/{public_doc_id}", headers=auth_headers_user_a)
    assert del_resp.status_code == 403
    assert del_resp.json()["code"] == "forbidden"


def test_chat_endpoint(client, auth_headers_user_a):
    """Verify chat endpoint executes grounded RAG and returns citations."""
    chat_payload = {
        "question": "What is the retry policy documented for payment endpoints?",
        "top_k": 3,
    }
    resp = client.post("/api/v1/chat", json=chat_payload, headers=auth_headers_user_a)
    assert resp.status_code == 200
    data = resp.json()
    assert "request_id" in data
    assert "answer" in data
    assert "citations" in data
    assert "timings_ms" in data
    assert "retrieval" in data


def test_feedback_endpoint(client, auth_headers_user_a):
    """Verify submitting user feedback on chat answer."""
    req_id = str(uuid.uuid4())
    feedback_payload = {
        "request_id": req_id,
        "rating": 1,
        "comment": "Accurate and clear citation.",
    }
    resp = client.post("/api/v1/feedback", json=feedback_payload, headers=auth_headers_user_a)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "success"
    assert data["request_id"] == req_id


def test_upload_duplicate_document_returns_409(client, auth_headers_user_a):
    """Verify that uploading the exact same document twice by same tenant returns HTTP 409 Conflict."""
    content = b"Unique content for duplicate detection test 12345."
    file_tuple_1 = ("doc1.txt", io.BytesIO(content), "text/plain")

    # First upload succeeds with 202
    resp1 = client.post(
        "/api/v1/documents",
        files={"file": file_tuple_1},
        headers=auth_headers_user_a,
    )
    assert resp1.status_code == 202

    # Second upload with identical content returns 409 Conflict
    file_tuple_2 = ("doc1_copy.txt", io.BytesIO(content), "text/plain")
    resp2 = client.post(
        "/api/v1/documents",
        files={"file": file_tuple_2},
        headers=auth_headers_user_a,
    )
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "conflict"


def test_upload_unsupported_format_returns_415(client, auth_headers_user_a):
    """Verify that unsupported file formats or invalid magic bytes return HTTP 415."""
    # 1. Unsupported extension
    exe_content = b"binary exe content"
    resp_exe = client.post(
        "/api/v1/documents",
        files={"file": ("malicious.exe", io.BytesIO(exe_content), "application/octet-stream")},
        headers=auth_headers_user_a,
    )
    assert resp_exe.status_code == 415
    assert resp_exe.json()["code"] == "unsupported_media_type"

    # 2. Corrupted PDF header (missing %PDF- magic bytes)
    fake_pdf = b"not a real pdf header at all"
    resp_pdf = client.post(
        "/api/v1/documents",
        files={"file": ("corrupt.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        headers=auth_headers_user_a,
    )
    assert resp_pdf.status_code == 415
    assert resp_pdf.json()["code"] == "unsupported_media_type"


def test_chat_empty_or_whitespace_question_returns_400(client, auth_headers_user_a):
    """Verify sending whitespace or blank question returns HTTP 400."""
    resp = client.post(
        "/api/v1/chat",
        json={"question": "   "},
        headers=auth_headers_user_a,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "bad_request"


def test_preview_document_pagination(client, db_session, auth_headers_user_a):
    """Verify preview document returns chunks and honors pagination limit/offset."""
    from tests.conftest import TEST_USER_A

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        owner_id=TEST_USER_A,
        filename="paginated.txt",
        storage_path="p/paginated.txt",
        content_type="text/plain",
        file_size_bytes=500,
        checksum_sha256="chk_pagination_test",
        status="ready",
        chunk_count=3,
        is_public=False,
    )
    DocumentRepository.create(db_session, doc)

    # Insert 3 chunks
    from sqlalchemy import text

    for i in range(3):
        db_session.execute(
            text("""
                INSERT INTO document_chunks (id, document_id, owner_id, chunk_index, content, embedding)
                VALUES (gen_random_uuid(), :doc_id, :owner, :idx, :content, (:vec)::vector)
            """),
            {
                "doc_id": str(doc_id),
                "owner": str(TEST_USER_A),
                "idx": i,
                "content": f"Chunk content paragraph {i}",
                "vec": "[" + ",".join(["0.01"] * 384) + "]",
            },
        )
    db_session.commit()

    # Preview with limit=2, offset=0
    resp = client.get(
        f"/api/v1/documents/{doc_id}/preview?limit=2&offset=0",
        headers=auth_headers_user_a,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_chunks"] == 3
    assert len(data["chunks"]) == 2
    assert data["chunks"][0]["chunk_index"] == 0
    assert data["chunks"][1]["chunk_index"] == 1


def test_delete_document_removes_from_database_and_storage(client, db_session, auth_headers_user_a):
    """Verify deleting a document removes the database record, cascading chunks, and storage object."""
    from sqlalchemy import text

    content = b"Content for deletion test document."
    upload_resp = client.post(
        "/api/v1/documents",
        files={"file": ("to_delete.txt", io.BytesIO(content), "text/plain")},
        headers=auth_headers_user_a,
    )
    assert upload_resp.status_code == 202
    doc_id = upload_resp.json()["document_id"]

    # Verify doc and chunks exist in DB
    doc_row = db_session.execute(
        text("SELECT storage_path FROM documents WHERE id = :id"), {"id": doc_id}
    ).fetchone()
    assert doc_row is not None
    chunks_before = db_session.execute(
        text("SELECT count(*) FROM document_chunks WHERE document_id = :id"), {"id": doc_id}
    ).scalar()
    assert chunks_before > 0

    # Delete
    del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers_user_a)
    assert del_resp.status_code == 204

    # Verify 404 on subsequent get
    get_resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_user_a)
    assert get_resp.status_code == 404

    # Verify chunks are cascaded
    chunks_after = db_session.execute(
        text("SELECT count(*) FROM document_chunks WHERE document_id = :id"), {"id": doc_id}
    ).scalar()
    assert chunks_after == 0


def test_user_b_cannot_chat_over_user_a_documents(client, auth_headers_user_a, auth_headers_user_b):
    """Verify User B cannot scope chat queries to User A's private documents (returns 404)."""
    # User A uploads a document
    content = b"Private secret information owned by user A only."
    upload_resp = client.post(
        "/api/v1/documents",
        files={"file": ("confidential_a.txt", io.BytesIO(content), "text/plain")},
        headers=auth_headers_user_a,
    )
    assert upload_resp.status_code == 202
    doc_a_id = upload_resp.json()["document_id"]

    # User B attempts to chat scoping to User A's document ID
    chat_payload = {
        "question": "What is the secret information?",
        "document_ids": [doc_a_id],
    }
    resp = client.post("/api/v1/chat", json=chat_payload, headers=auth_headers_user_b)
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


def test_upload_file_size_limit_enforced_413(client, auth_headers_user_a):
    """Verify uploading a file exceeding MAX_UPLOAD_MB returns HTTP 413 Payload Too Large."""
    # Settings default is MAX_UPLOAD_MB = 5 (5 * 1024 * 1024 bytes)
    # Generate 5.5MB file in memory
    oversized_content = b"X" * (6 * 1024 * 1024)
    file_tuple = ("large_file.txt", io.BytesIO(oversized_content), "text/plain")

    resp = client.post(
        "/api/v1/documents",
        files={"file": file_tuple},
        headers=auth_headers_user_a,
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "payload_too_large"


def test_client_polling_document_status_flow(client, auth_headers_user_a):
    """Verify client can poll GET /documents/{id} to observe ingestion status."""
    content = b"Polling test document content for knowledge assistant."
    upload_resp = client.post(
        "/api/v1/documents",
        files={"file": ("poll_doc.txt", io.BytesIO(content), "text/plain")},
        headers=auth_headers_user_a,
    )
    assert upload_resp.status_code == 202
    doc_id = upload_resp.json()["document_id"]

    # Immediate poll returns document with metadata
    poll_resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_user_a)
    assert poll_resp.status_code == 200
    doc_data = poll_resp.json()
    assert doc_data["id"] == doc_id
    assert doc_data["filename"] == "poll_doc.txt"
    assert doc_data["status"] in ("processing", "ready")


def test_chat_endpoint_greeting_returns_conversational_welcome(client, auth_headers_user_a):
    """Verify chat endpoint returns conversational welcome for greetings without querying documents."""
    resp = client.post(
        "/api/v1/chat",
        json={"question": "Hey there!"},
        headers=auth_headers_user_a,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["abstained"] is False
    assert data["citations"] == []
    assert data["retrieval"]["mode"] == "conversational"
    assert data["retrieval"]["attempts"] == 0
    assert "Enterprise Knowledge Assistant" in data["answer"]


@pytest.mark.asyncio
async def test_lifespan_recovers_stale_processing_documents(db_session):
    """Verify lifespan startup resets stale processing documents to failed and cleans orphan chunks."""
    from app.main import app, lifespan

    stale_id = uuid.uuid4()
    fresh_id = uuid.uuid4()
    owner_id = TEST_USER_A

    # Insert a stale document (updated 30 minutes ago)
    db_session.execute(
        text("""
            INSERT INTO documents (id, owner_id, filename, storage_path, content_type, file_size_bytes, checksum_sha256, status, created_at, updated_at)
            VALUES (:id, :owner, 'stale.txt', 'p/stale.txt', 'text/plain', 100, 'stale_sha_123', 'processing',
                    NOW() - INTERVAL '30 minutes', NOW() - INTERVAL '30 minutes')
        """),
        {"id": str(stale_id), "owner": str(owner_id)},
    )
    # Insert an orphan chunk for the stale document
    db_session.execute(
        text("""
            INSERT INTO document_chunks (id, document_id, owner_id, chunk_index, page_number, start_index, content, embedding)
            VALUES (:chunk_id, :doc_id, :owner, 0, 1, 0, 'stale content', (:vec)::vector)
        """),
        {
            "chunk_id": str(uuid.uuid4()),
            "doc_id": str(stale_id),
            "owner": str(owner_id),
            "vec": "[" + ",".join(["0.1"] * 384) + "]",
        },
    )

    # Insert a fresh document (updated just now)
    db_session.execute(
        text("""
            INSERT INTO documents (id, owner_id, filename, storage_path, content_type, file_size_bytes, checksum_sha256, status, created_at, updated_at)
            VALUES (:id, :owner, 'fresh.txt', 'p/fresh.txt', 'text/plain', 100, 'fresh_sha_456', 'processing',
                    NOW(), NOW())
        """),
        {"id": str(fresh_id), "owner": str(owner_id)},
    )
    db_session.commit()

    # Run lifespan startup
    async with lifespan(app):
        pass

    # Verify stale document is marked failed with error_code
    stale_doc = db_session.execute(
        text("SELECT status, error_code FROM documents WHERE id = :id"),
        {"id": str(stale_id)},
    ).fetchone()
    assert stale_doc is not None
    assert stale_doc[0] == "failed"
    assert stale_doc[1] == "ingestion_interrupted"

    # Verify orphan chunks for stale doc are deleted
    orphan_chunks = db_session.execute(
        text("SELECT count(*) FROM document_chunks WHERE document_id = :id"),
        {"id": str(stale_id)},
    ).scalar()
    assert orphan_chunks == 0

    # Verify fresh document remains untouched in processing status
    fresh_doc = db_session.execute(
        text("SELECT status, error_code FROM documents WHERE id = :id"),
        {"id": str(fresh_id)},
    ).fetchone()
    assert fresh_doc is not None
    assert fresh_doc[0] == "processing"
    assert fresh_doc[1] is None
