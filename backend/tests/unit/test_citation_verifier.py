"""Unit tests for deterministic sentence-level citation verification."""

import uuid

from app.services.citation_verifier import CitationVerifier
from app.services.retrieval import RetrievalCandidate


def make_candidate(idx: int, filename: str = "api.pdf", page: int = 1) -> RetrievalCandidate:
    """Helper to create candidate for verification tests."""
    return RetrievalCandidate(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename=filename,
        page_number=page,
        chunk_index=idx - 1,
        content=f"Content for candidate {idx}",
        rrf_score=1.0 / (60 + idx),
    )


def test_valid_citations_pass():
    """Verify answer with valid citations passes and returns grounded Citation objects."""
    c1 = make_candidate(1, filename="policy.pdf", page=3)
    c2 = make_candidate(2, filename="terms.pdf", page=5)

    answer = "The retry maximum is 3 attempts [S1]. The timeout period is 45 seconds [S2]."
    res = CitationVerifier.verify(answer, [c1, c2])

    assert res.is_valid is True
    assert res.abstained is False
    assert len(res.citations) == 2
    assert res.citations[0].label == "S1"
    assert res.citations[0].filename == "policy.pdf"
    assert res.citations[0].page_number == 3
    assert res.citations[1].label == "S2"
    assert res.citations[1].filename == "terms.pdf"


def test_unknown_label_fails_closed():
    """Verify that hallucinated/unprovided citation labels fail closed."""
    c1 = make_candidate(1)
    answer = "The policy allows up to 5 users [S99]."

    res = CitationVerifier.verify(answer, [c1])
    assert res.is_valid is False
    assert res.abstained is True
    assert "hallucinated_label" in (res.failure_reason or "")
    assert len(res.citations) == 0


def test_uncited_factual_claim_fails_closed():
    """Verify that uncited factual sentences fail closed per sentence-level rule."""
    c1 = make_candidate(1)
    answer = "The maximum retry limit is three [S1]. In addition, server timeouts trigger alerts."

    res = CitationVerifier.verify(answer, [c1])
    assert res.is_valid is False
    assert res.abstained is True
    assert res.failure_reason == "uncited_factual_sentences"


def test_abstention_hedges_exempt_from_citation():
    """Verify that hedge and abstention sentences do not require citations."""
    c1 = make_candidate(1)
    answer = "The maximum retry limit is three [S1]. The available documents do not contain information regarding caching."

    res = CitationVerifier.verify(answer, [c1])
    assert res.is_valid is True
    assert res.abstained is False
    assert len(res.citations) == 1
    assert res.citations[0].label == "S1"


def test_pure_abstention_response_passes():
    """Verify that a full abstention answer passes as abstained."""
    c1 = make_candidate(1)
    answer = "The provided documents do not contain sufficient information to answer this question."

    res = CitationVerifier.verify(answer, [c1])
    assert res.is_valid is True
    assert res.abstained is True
    assert len(res.citations) == 0


def test_meta_commentary_stripped_and_exempt():
    """Verify that trailing meta-commentary like word counts or citation affirmations are stripped."""
    c1 = make_candidate(1, filename="lstm.pdf")
    answer = (
        "LSTM is an advanced recurrent neural network [S1].\n"
        "Word count: ~220 words.\n"
        "All sentences include citations as required."
    )

    res = CitationVerifier.verify(answer, [c1])
    assert res.is_valid is True
    assert res.abstained is False
    assert len(res.citations) == 1
    assert "Word count" not in res.answer
    assert "All sentences include" not in res.answer

