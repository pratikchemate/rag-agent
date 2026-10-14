"""Nodes executing individual steps of the LangGraph RAG workflow."""

import time
from typing import Any, Dict
from uuid import UUID

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.core.logging import get_logger
from app.db.engine import SessionLocal
from app.graph.state import RAGState
from app.services.citation_verifier import CitationVerifier
from app.services.generation import GenerationService
from app.services.retrieval import (
    RetrievalCandidate,
    get_retrieval_service,
    is_evidence_sufficient,
)

logger = get_logger(__name__)


def candidate_to_dict(c: RetrievalCandidate) -> Dict[str, Any]:
    """Serialize candidate to dictionary for graph state."""
    return {
        "chunk_id": str(c.chunk_id),
        "document_id": str(c.document_id),
        "filename": c.filename,
        "page_number": c.page_number,
        "chunk_index": c.chunk_index,
        "content": c.content,
        "vector_rank": c.vector_rank,
        "vector_similarity": c.vector_similarity,
        "keyword_rank": c.keyword_rank,
        "keyword_score": c.keyword_score,
        "rrf_score": c.rrf_score,
    }


def dict_to_candidate(d: Dict[str, Any]) -> RetrievalCandidate:
    """Deserialize candidate dictionary from graph state."""
    return RetrievalCandidate(
        chunk_id=UUID(d["chunk_id"]),
        document_id=UUID(d["document_id"]),
        filename=d["filename"],
        page_number=d.get("page_number"),
        chunk_index=d["chunk_index"],
        content=d["content"],
        vector_rank=d.get("vector_rank"),
        vector_similarity=d.get("vector_similarity"),
        keyword_rank=d.get("keyword_rank"),
        keyword_score=d.get("keyword_score"),
        rrf_score=d.get("rrf_score", 0.0),
    )


def validate_question_node(state: RAGState) -> RAGState:
    """Validate question format and length."""
    settings = get_settings()
    question = (state.get("question") or "").strip()

    if not question or len(question) > settings.MAX_QUESTION_LENGTH:
        raise BadRequestError("Question cannot be empty or exceed maximum character limits.")

    return {
        "question": question,
        "search_query": question,
        "retrieval_attempt": 1,
        "error_code": None,
        "timings_ms": state.get("timings_ms", {}),
    }


def retrieve_hybrid_node(state: RAGState) -> RAGState:
    """Execute hybrid retrieval using current search query."""
    start_time = time.perf_counter()
    retrieval_svc = get_retrieval_service()
    owner_id = UUID(state["owner_id"])
    query = state.get("search_query", state["question"])
    selected_docs = state.get("selected_document_ids")
    top_k = state.get("top_k")

    db = SessionLocal()
    try:
        result = retrieval_svc.search(
            db=db,
            owner_id=owner_id,
            query_text=query,
            selected_document_ids=selected_docs,
            top_k=top_k,
        )
    finally:
        db.close()

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    timings = dict(state.get("timings_ms", {}))
    # Accumulate or set retrieval time
    timings["retrieval"] = timings.get("retrieval", 0.0) + elapsed_ms

    serialized_chunks = [candidate_to_dict(c) for c in result.candidates]
    retrieval_debug = {
        "vector_count": result.vector_count,
        "keyword_count": result.keyword_count,
        "top_similarity": result.top_similarity,
        "returned_chunks": len(result.candidates),
        "mode": result.mode,
    }

    return {
        "retrieved_chunks": serialized_chunks,
        "retrieval_debug": retrieval_debug,
        "evidence_sufficient": result.evidence_sufficient,
        "timings_ms": timings,
    }


def assess_evidence_node(state: RAGState) -> RAGState:
    """Determine whether evidence is sufficient to answer based on multi-signal grounding."""
    chunks = state.get("retrieved_chunks", [])
    if not chunks:
        return {"evidence_sufficient": False}

    mode = state.get("retrieval_debug", {}).get("mode", "hybrid_rrf")
    sufficient = is_evidence_sufficient(
        vector_sims=[c.get("vector_similarity") for c in chunks],
        keyword_scores=[c.get("keyword_score") for c in chunks],
        mode=mode,
    )
    return {"evidence_sufficient": sufficient}


def rewrite_query_node(state: RAGState) -> RAGState:
    """Perform deterministic search query rewriting on weak evidence with fallback."""
    question = state.get("question", "")
    attempt = state.get("retrieval_attempt", 1) + 1

    try:
        stopwords = {
            "what",
            "where",
            "when",
            "which",
            "who",
            "whom",
            "how",
            "why",
            "is",
            "are",
            "was",
            "were",
            "do",
            "does",
            "did",
            "can",
            "could",
            "would",
            "should",
            "the",
            "a",
            "an",
            "of",
            "in",
            "for",
            "on",
            "with",
            "about",
            "please",
            "tell",
            "me",
        }
        words = [w.strip("?,.!;:\"'()") for w in question.split()]
        filtered_words = [w for w in words if w.lower() not in stopwords and len(w) > 1]
        rewritten_query = " ".join(filtered_words) if filtered_words else question
    except Exception as e:
        logger.warning(f"Query rewrite encountered error: {e}. Falling back to original question.")
        rewritten_query = question

    logger.info(f"Rewrote query for attempt {attempt}: '{rewritten_query}'")
    return {
        "search_query": rewritten_query,
        "retrieval_attempt": attempt,
    }


def generate_answer_node(state: RAGState) -> RAGState:
    """Generate cited answer using ChatOpenRouter."""
    start_time = time.perf_counter()
    chunks = [dict_to_candidate(d) for d in state.get("retrieved_chunks", [])]
    question = state.get("question", "")

    db = SessionLocal()
    try:
        answer = GenerationService.generate_answer(question=question, candidates=chunks, db=db)
    finally:
        db.close()

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    timings = dict(state.get("timings_ms", {}))
    timings["generation"] = elapsed_ms

    return {
        "answer": answer,
        "timings_ms": timings,
    }


def verify_citations_node(state: RAGState) -> RAGState:
    """Verify generated citations sentence by sentence."""
    answer = state.get("answer", "")
    chunks = [dict_to_candidate(d) for d in state.get("retrieved_chunks", [])]

    verification = CitationVerifier.verify(answer=answer, retrieved_candidates=chunks)

    if not verification.is_valid:
        return {
            "abstained": True,
            "answer": verification.answer,
            "citations": [],
            "error_code": verification.failure_reason,
        }

    return {
        "abstained": verification.abstained,
        "answer": verification.answer,
        "citations": [c.model_dump() for c in verification.citations],
        "error_code": None,
    }


def abstain_node(state: RAGState) -> RAGState:
    """Abstain due to missing evidence after search attempts."""
    return {
        "abstained": True,
        "answer": "The available documents do not contain sufficient information to answer this question.",
        "citations": [],
        "error_code": "insufficient_evidence",
    }


def safe_abstention_node(state: RAGState) -> RAGState:
    """Fail-closed abstention when citations are invalid or unverified."""
    return {
        "abstained": True,
        "answer": "The available documents did not provide verifiable evidence for this response.",
        "citations": [],
        "error_code": "unverified_citations",
    }
