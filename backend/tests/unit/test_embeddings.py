"""Unit tests for local FastEmbed embedding service."""

from app.services.embeddings import FastEmbedEmbeddings, get_embedding_service


def test_embedding_dimensions_and_compliance():
    """Verify that FastEmbed service returns 384-dimensional vector embeddings."""
    service = get_embedding_service()
    assert isinstance(service, FastEmbedEmbeddings)

    # 1. Single query embedding
    query_vec = service.embed_query("enterprise documentation query")
    assert isinstance(query_vec, list)
    assert len(query_vec) == 384
    assert all(isinstance(val, float) for val in query_vec)

    # 2. Batch document embeddings
    texts = [
        "First document chunk text for indexing.",
        "Second document chunk text with configuration parameters.",
    ]
    batch_vecs = service.embed_documents(texts)
    assert len(batch_vecs) == 2
    for vec in batch_vecs:
        assert len(vec) == 384
        assert all(isinstance(val, float) for val in vec)

    # 3. Empty input
    assert service.embed_documents([]) == []
