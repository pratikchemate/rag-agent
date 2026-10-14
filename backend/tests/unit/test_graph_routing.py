"""Unit tests for LangGraph routing logic and state transitions."""

from app.graph.routing import (
    route_after_citation_verification,
    route_after_evidence_assessment,
    route_after_validation,
)
from app.graph.state import RAGState


def test_routing_after_validation():
    """Verify route_after_validation exits early on invalid question."""
    invalid_state: RAGState = {"error_code": "invalid_question"}
    assert route_after_validation(invalid_state) == "end"

    valid_state: RAGState = {"error_code": None, "question": "Valid query?"}
    assert route_after_validation(valid_state) == "retrieve_hybrid"


def test_routing_after_evidence_assessment():
    """Verify route_after_evidence_assessment handles sufficient, retry, and exhaustion."""
    # 1. Sufficient evidence -> generate_answer
    state_strong: RAGState = {"evidence_sufficient": True, "retrieval_attempt": 1}
    assert route_after_evidence_assessment(state_strong) == "generate_answer"

    # 2. Weak evidence on attempt 1 -> rewrite_query
    state_weak_attempt_1: RAGState = {
        "evidence_sufficient": False,
        "retrieval_attempt": 1,
    }
    assert route_after_evidence_assessment(state_weak_attempt_1) == "rewrite_query"

    # 3. Weak evidence on attempt 2 (max attempts reached) -> abstain
    state_weak_attempt_2: RAGState = {
        "evidence_sufficient": False,
        "retrieval_attempt": 2,
    }
    assert route_after_evidence_assessment(state_weak_attempt_2) == "abstain"


def test_routing_after_citation_verification():
    """Verify verify_citations terminates or routes to safe abstention without loops."""
    # 1. Valid citations -> end
    state_verified: RAGState = {"error_code": None, "abstained": False}
    assert route_after_citation_verification(state_verified) == "end"

    # 2. Failed verification -> safe_abstention
    state_failed: RAGState = {"error_code": "hallucinated_label_S99", "abstained": True}
    assert route_after_citation_verification(state_failed) == "safe_abstention"


def test_compiled_graph_abstain_path_never_reaches_verification(monkeypatch):
    """Verify compiled LangGraph executes abstain path without invoking generate_answer or verify_citations."""
    from uuid import uuid4

    from app.graph import nodes
    from app.graph.workflow import create_rag_graph

    # Track invocations
    generate_called = False
    verify_called = False

    def mock_generate(state):
        nonlocal generate_called
        generate_called = True
        return {"answer": "Should not be called"}

    def mock_verify(state):
        nonlocal verify_called
        verify_called = True
        return {"citations": []}

    # Simulate retrieval returning zero chunks (insufficient evidence)
    def mock_retrieve(state):
        return {
            "retrieved_chunks": [],
            "retrieval_debug": {"candidates": 0},
            "evidence_sufficient": False,
        }

    monkeypatch.setattr(nodes, "generate_answer_node", mock_generate)
    monkeypatch.setattr(nodes, "verify_citations_node", mock_verify)
    monkeypatch.setattr(nodes, "retrieve_hybrid_node", mock_retrieve)

    # Compile fresh graph with patched nodes
    test_graph = create_rag_graph()

    initial_state = {
        "request_id": str(uuid4()),
        "owner_id": str(uuid4()),
        "question": "What is the out-of-corpus secret code?",
        "selected_document_ids": None,
        "top_k": 3,
        "retrieval_attempt": 1,
        "evidence_sufficient": False,
        "abstained": False,
        "citations": [],
    }

    final_state = test_graph.invoke(initial_state)

    assert final_state.get("abstained") is True
    assert "The available documents do not contain" in final_state.get("answer", "")
    assert not generate_called, "generate_answer_node must never be invoked on abstain path"
    assert not verify_called, "verify_citations_node must never be invoked on abstain path"
