"""Conditional routing logic for the LangGraph RAG workflow."""

from typing import Literal

from app.core.config import get_settings
from app.graph.state import RAGState


def route_after_validation(state: RAGState) -> Literal["end", "retrieve_hybrid"]:
    """Route from validate_question to either early exit or retrieval."""
    if state.get("error_code") == "invalid_question":
        return "end"
    return "retrieve_hybrid"


def route_after_evidence_assessment(
    state: RAGState,
) -> Literal["generate_answer", "rewrite_query", "abstain"]:
    """Route based on evidence sufficiency and attempt count."""
    settings = get_settings()

    if state.get("evidence_sufficient", False):
        return "generate_answer"

    current_attempt = state.get("retrieval_attempt", 1)
    if current_attempt < settings.MAX_RETRIEVAL_ATTEMPTS and settings.ENABLE_QUERY_REWRITE:
        return "rewrite_query"

    return "abstain"


def route_after_citation_verification(state: RAGState) -> Literal["end", "safe_abstention"]:
    """Route from verify_citations to end or fail-closed safe abstention."""
    if state.get("error_code") is not None:
        return "safe_abstention"
    return "end"
