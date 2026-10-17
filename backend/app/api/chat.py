"""Chat question-answering endpoint with LangGraph orchestration."""

import time
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser, get_current_user_optional
from app.core.errors import AppException, NotFoundError, ServiceUnavailableError
from app.core.logging import get_logger, request_id_ctx
from app.core.rate_limit import get_chat_limiter
from app.db.engine import get_db
from app.db.repositories import DocumentRepository
from app.graph.workflow import rag_graph
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    RetrievalMetadata,
    TimingsMetadata,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
def ask_question(
    request: ChatRequest,
    req: Request,
    user: AuthenticatedUser = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Execute evidence-grounded RAG workflow via LangGraph."""
    start_total_time = time.perf_counter()
    req_id = request_id_ctx.get() or str(uuid.uuid4())

    # 1. Rate limiting (per-user/IP)
    client_ip = req.client.host if req.client else "anonymous"
    rate_key = str(user.user_id) if user.role != "anonymous" else f"anon_{client_ip}"
    chat_limiter = get_chat_limiter()
    chat_limiter.check(rate_key)

    # 2. Validate selected document IDs (verify ownership or public status)
    if request.document_ids:
        for doc_id in request.document_ids:
            doc = DocumentRepository.get_by_id(db, doc_id, user.user_id, allow_public=True)
            if not doc:
                raise NotFoundError(f"Document {doc_id} not found or inaccessible.")

    # 3. Clamped top_k
    effective_top_k = min(max(request.top_k, 1), 8)

    # 4. Execute LangGraph workflow (budget quota is charged dynamically at model invocation)
    initial_state = {
        "request_id": str(req_id),
        "owner_id": str(user.user_id),
        "question": request.question,
        "selected_document_ids": request.document_ids,
        "top_k": effective_top_k,
        "retrieval_attempt": 1,
        "timings_ms": {},
    }

    try:
        final_state = rag_graph.invoke(initial_state)
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in RAG graph execution: {str(e)}", exc_info=True)
        raise ServiceUnavailableError(f"An error occurred while generating your response: {str(e)}")

    total_elapsed_ms = (time.perf_counter() - start_total_time) * 1000.0
    graph_timings = final_state.get("timings_ms", {})
    retrieval_ms = graph_timings.get("retrieval", 0.0)
    generation_ms = graph_timings.get("generation", 0.0)

    # Format citations
    citations_data = final_state.get("citations", [])
    citations = [Citation(**c) if isinstance(c, dict) else c for c in citations_data]

    retrieval_debug = final_state.get("retrieval_debug", {})
    is_greeting = final_state.get("is_greeting", False)
    retrieval_metadata = RetrievalMetadata(
        mode=retrieval_debug.get("mode", "conversational" if is_greeting else "hybrid_rrf"),
        attempts=0 if is_greeting else final_state.get("retrieval_attempt", 1),
        returned_chunks=retrieval_debug.get("returned_chunks", len(citations)),
    )

    timings = TimingsMetadata(
        retrieval=round(retrieval_ms, 2),
        generation=round(generation_ms, 2),
        total=round(total_elapsed_ms, 2),
    )

    logger.info(
        f"Chat completed for req {req_id}: abstained={final_state.get('abstained', False)}, "
        f"citations={len(citations)}, total_ms={timings.total}"
    )

    return ChatResponse(
        request_id=req_id,
        answer=final_state.get("answer", "No answer could be generated."),
        abstained=final_state.get("abstained", False),
        citations=citations,
        retrieval=retrieval_metadata,
        timings_ms=timings,
    )
