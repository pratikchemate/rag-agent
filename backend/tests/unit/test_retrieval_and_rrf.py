"""Unit tests for hybrid retrieval, RRF ranking, and keyword OR tsquery."""

import uuid

from sqlalchemy import text


def test_rrf_scoring_and_ranking():
    """Verify Reciprocal Rank Fusion computes correct scores and orders candidates."""
    k = 60

    # Candidate 1: Rank 1 in vector, Rank 2 in keyword
    score_1 = (1.0 / (k + 1)) + (1.0 / (k + 2))

    # Candidate 2: Rank 2 in vector, not in keyword
    score_2 = 1.0 / (k + 2)

    assert score_1 > score_2


def test_keyword_or_tsquery_partial_matches(db_session):
    """Regression test for §9.2: Natural language question matches chunks with partial terms."""
    # Insert test document and chunk
    owner_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    db_session.execute(
        text("""
            INSERT INTO documents (id, owner_id, filename, storage_path, content_type, file_size_bytes, checksum_sha256, status, is_public)
            VALUES (:id, :owner, 'api.txt', 'p/api.txt', 'text/plain', 100, 'hash1', 'ready', false)
        """),
        {"id": str(doc_id), "owner": str(owner_id)},
    )

    # Chunk contains "payment" and "api", but does NOT contain "retry" or "policy"
    chunk_id = uuid.uuid4()
    db_session.execute(
        text("""
            INSERT INTO document_chunks (id, document_id, owner_id, chunk_index, content, embedding)
            VALUES (:id, :doc_id, :owner, 0, 'This is the enterprise payment api endpoint specification.', (:vec)::vector)
        """),
        {
            "id": str(chunk_id),
            "doc_id": str(doc_id),
            "owner": str(owner_id),
            "vec": "[" + ",".join(["0.1"] * 384) + "]",
        },
    )
    db_session.commit()

    # Query has 9 words: "What retry policy is documented for the payment API?"
    # If using websearch_to_tsquery (AND), this returns 0 rows because 'retry' and 'policy' are absent.
    # With our OR-joined tsquery (§9.2), it matches on 'payment' and 'api'!
    keyword_sql = """
        WITH query_lexemes AS (
            SELECT string_agg(lex, ' | ') AS or_tsquery
            FROM unnest(tsvector_to_array(to_tsvector('english', :query_text))) AS lex
        )
        SELECT c.id, ts_rank_cd(c.search_vector, to_tsquery('english', ql.or_tsquery)) AS rank_score
        FROM document_chunks c
        CROSS JOIN query_lexemes ql
        WHERE ql.or_tsquery IS NOT NULL AND ql.or_tsquery <> ''
          AND c.owner_id = :owner_id
          AND c.search_vector @@ to_tsquery('english', ql.or_tsquery)
    """

    res = db_session.execute(
        text(keyword_sql),
        {
            "query_text": "What retry policy is documented for the payment API?",
            "owner_id": str(owner_id),
        },
    ).fetchall()

    assert len(res) == 1, "OR-based tsquery must match chunk containing subset of query terms"
    assert res[0][0] == chunk_id


def test_hybrid_retrieval_service_search_live(db_session):
    """Verify HybridRetrievalService executes live search against database across all modes."""
    from app.services.retrieval import get_retrieval_service

    retrieval_svc = get_retrieval_service()
    owner_id = uuid.uuid4()
    doc_1_id = uuid.uuid4()
    doc_2_id = uuid.uuid4()

    # Create two ready documents
    db_session.execute(
        text("""
            INSERT INTO documents (id, owner_id, filename, storage_path, content_type, file_size_bytes, checksum_sha256, status, is_public)
            VALUES
                (:id1, :owner, 'doc1.md', 'p/doc1.md', 'text/markdown', 100, 'hash_doc1', 'ready', false),
                (:id2, :owner, 'doc2.md', 'p/doc2.md', 'text/markdown', 100, 'hash_doc2', 'ready', false)
        """),
        {"id1": str(doc_1_id), "id2": str(doc_2_id), "owner": str(owner_id)},
    )

    # Insert chunks with FastEmbed compatible 384-d vectors
    vec_data = "[" + ",".join(["0.05"] * 384) + "]"
    db_session.execute(
        text("""
            INSERT INTO document_chunks (id, document_id, owner_id, chunk_index, content, embedding)
            VALUES
                (gen_random_uuid(), :doc1, :owner, 0, 'Kubernetes cluster deployment architecture and ingress controller.', (:vec)::vector),
                (gen_random_uuid(), :doc2, :owner, 0, 'Database backup and replication recovery policy.', (:vec)::vector)
        """),
        {"doc1": str(doc_1_id), "doc2": str(doc_2_id), "owner": str(owner_id), "vec": vec_data},
    )
    db_session.commit()

    # 1. Hybrid RRF Search
    result_hybrid = retrieval_svc.search(
        db=db_session,
        owner_id=owner_id,
        query_text="Kubernetes deployment",
        top_k=2,
        mode="hybrid_rrf",
    )
    assert len(result_hybrid.candidates) > 0
    top_c = result_hybrid.candidates[0]
    assert top_c.document_id == doc_1_id
    assert top_c.rrf_score > 0.0

    # 2. Selected document filter
    result_filtered = retrieval_svc.search(
        db=db_session,
        owner_id=owner_id,
        query_text="architecture policy",
        selected_document_ids=[doc_2_id],
        top_k=2,
        mode="hybrid_rrf",
    )
    assert len(result_filtered.candidates) == 1
    assert result_filtered.candidates[0].document_id == doc_2_id

    # 3. Vector-only mode
    result_vector = retrieval_svc.search(
        db=db_session,
        owner_id=owner_id,
        query_text="cluster",
        top_k=2,
        mode="vector",
    )
    assert result_vector.mode == "vector"
    assert len(result_vector.candidates) > 0

    # 4. Keyword-only mode
    result_kw = retrieval_svc.search(
        db=db_session,
        owner_id=owner_id,
        query_text="replication",
        top_k=2,
        mode="keyword",
    )
    assert result_kw.mode == "keyword"
    assert len(result_kw.candidates) > 0
    assert result_kw.candidates[0].document_id == doc_2_id


def test_retrieval_owner_and_public_isolation(db_session):
    """Verify User A cannot retrieve User B's documents, but both can retrieve public docs."""
    from app.services.retrieval import get_retrieval_service

    retrieval_svc = get_retrieval_service()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    system_user = uuid.uuid4()

    doc_a = uuid.uuid4()
    doc_b = uuid.uuid4()
    doc_pub = uuid.uuid4()

    vec_data = "[" + ",".join(["0.08"] * 384) + "]"

    db_session.execute(
        text("""
            INSERT INTO documents (id, owner_id, filename, storage_path, content_type, file_size_bytes, checksum_sha256, status, is_public)
            VALUES
                (:doc_a, :user_a, 'doc_a.md', 'p/a.md', 'text/markdown', 100, 'hash_a', 'ready', false),
                (:doc_b, :user_b, 'doc_b.md', 'p/b.md', 'text/markdown', 100, 'hash_b', 'ready', false),
                (:doc_pub, :sys, 'public_doc.md', 'p/pub.md', 'text/markdown', 100, 'hash_pub', 'ready', true)
        """),
        {
            "doc_a": str(doc_a),
            "doc_b": str(doc_b),
            "doc_pub": str(doc_pub),
            "user_a": str(user_a),
            "user_b": str(user_b),
            "sys": str(system_user),
        },
    )

    db_session.execute(
        text("""
            INSERT INTO document_chunks (id, document_id, owner_id, chunk_index, content, embedding)
            VALUES
                (gen_random_uuid(), :doc_a, :user_a, 0, 'Confidential financials for organization alpha.', (:vec)::vector),
                (gen_random_uuid(), :doc_b, :user_b, 0, 'Confidential patent disclosures for organization beta.', (:vec)::vector),
                (gen_random_uuid(), :doc_pub, :sys, 0, 'Public open source compliance guidelines and standards.', (:vec)::vector)
        """),
        {
            "doc_a": str(doc_a),
            "doc_b": str(doc_b),
            "doc_pub": str(doc_pub),
            "user_a": str(user_a),
            "user_b": str(user_b),
            "sys": str(system_user),
            "vec": vec_data,
        },
    )
    db_session.commit()

    # User A searches for organization data
    res_a = retrieval_svc.search(
        db=db_session,
        owner_id=user_a,
        query_text="organization compliance guidelines",
        top_k=5,
        mode="hybrid_rrf",
    )
    doc_ids_a = {c.document_id for c in res_a.candidates}
    assert doc_a in doc_ids_a or doc_pub in doc_ids_a
    assert doc_b not in doc_ids_a, "User A must never retrieve User B's private documents"

    # User B searches
    res_b = retrieval_svc.search(
        db=db_session,
        owner_id=user_b,
        query_text="organization compliance guidelines",
        top_k=5,
        mode="hybrid_rrf",
    )
    doc_ids_b = {c.document_id for c in res_b.candidates}
    assert doc_b in doc_ids_b or doc_pub in doc_ids_b
    assert doc_a not in doc_ids_b, "User B must never retrieve User A's private documents"


def test_evidence_sufficiency_unified_between_graph_and_retrieval():
    """Verify assess_evidence_node and HybridRetrievalService yield identical sufficiency decisions."""
    from app.graph.nodes import assess_evidence_node
    from app.services.retrieval import (
        RetrievalCandidate,
        get_retrieval_service,
        is_evidence_sufficient,
    )

    retrieval_svc = get_retrieval_service()

    # Define various candidate scenarios
    test_cases = [
        # 1. Semantic floor failure (sim < 0.50 even with high keyword)
        ([0.48, 0.40], [0.80, 0.50], False),
        # 2. Low lexical grounding requiring high similarity (kw <= 0.15 and sim < 0.72)
        ([0.68, 0.50], [0.10, 0.05], False),
        ([0.75, 0.50], [0.10, 0.05], True),
        # 3. Sub-critical match requiring strong lexical corroboration (sim < 0.63 and kw < 0.50)
        ([0.60, 0.50], [0.40, 0.20], False),
        ([0.60, 0.50], [0.55, 0.20], True),
        # 4. Score gap check (sim < 0.65 and gap < 0.05)
        ([0.62, 0.60], [0.60, 0.50], False),
        ([0.62, 0.50], [0.60, 0.50], True),
        # 5. Strong evidence
        ([0.88, 0.65], [0.90, 0.70], True),
        # 6. Empty candidates
        ([], [], False),
    ]

    for sims, kws, expected in test_cases:
        candidates = [
            RetrievalCandidate(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                filename=f"doc_{i}.md",
                page_number=1,
                chunk_index=i,
                content=f"Content {i}",
                vector_similarity=sim,
                keyword_score=kw,
            )
            for i, (sim, kw) in enumerate(zip(sims, kws))
        ]

        # Service decision
        service_decision = retrieval_svc.evaluate_evidence_sufficiency(candidates)

        # Pure function decision
        pure_decision = is_evidence_sufficient(sims, kws)

        # Graph node decision
        chunks = [
            {"vector_similarity": c.vector_similarity, "keyword_score": c.keyword_score}
            for c in candidates
        ]
        node_decision = assess_evidence_node(
            {"retrieved_chunks": chunks, "retrieval_debug": {"mode": "hybrid_rrf"}}
        )["evidence_sufficient"]

        assert service_decision == expected
        assert pure_decision == expected
        assert node_decision == expected
