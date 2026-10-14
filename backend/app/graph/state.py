"""Typed state definition for the LangGraph RAG workflow."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from typing_extensions import TypedDict


class RAGState(TypedDict, total=False):
    """Execution state passed through the LangGraph RAG nodes."""

    request_id: str
    owner_id: str
    question: str
    search_query: str
    selected_document_ids: Optional[List[UUID]]
    top_k: Optional[int]
    retrieval_attempt: int
    retrieved_chunks: List[Dict[str, Any]]
    retrieval_debug: Dict[str, Any]
    evidence_sufficient: bool
    answer: str
    citation_labels: List[str]
    citations: List[Dict[str, Any]]
    abstained: bool
    error_code: Optional[str]
    timings_ms: Dict[str, float]
