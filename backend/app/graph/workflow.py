"""LangGraph StateGraph compilation for evidence-grounded RAG."""

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    abstain_node,
    assess_evidence_node,
    generate_answer_node,
    retrieve_hybrid_node,
    rewrite_query_node,
    safe_abstention_node,
    validate_question_node,
    verify_citations_node,
)
from app.graph.routing import (
    route_after_citation_verification,
    route_after_evidence_assessment,
    route_after_validation,
)
from app.graph.state import RAGState


def create_rag_graph():
    """Build and compile the typed LangGraph RAG workflow."""
    workflow = StateGraph(RAGState)

    # 1. Add all functional nodes
    workflow.add_node("validate_question", validate_question_node)
    workflow.add_node("retrieve_hybrid", retrieve_hybrid_node)
    workflow.add_node("assess_evidence", assess_evidence_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("verify_citations", verify_citations_node)
    workflow.add_node("abstain", abstain_node)
    workflow.add_node("safe_abstention", safe_abstention_node)

    # 2. Add edges and conditional routing
    workflow.add_edge(START, "validate_question")

    workflow.add_conditional_edges(
        "validate_question",
        route_after_validation,
        {
            "end": END,
            "retrieve_hybrid": "retrieve_hybrid",
        },
    )

    workflow.add_edge("retrieve_hybrid", "assess_evidence")

    workflow.add_conditional_edges(
        "assess_evidence",
        route_after_evidence_assessment,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
            "abstain": "abstain",
        },
    )

    # Loop back from rewrite to retrieve (bounded by attempt count in assess_evidence)
    workflow.add_edge("rewrite_query", "retrieve_hybrid")

    # Abstain terminates directly without verifying citations
    workflow.add_edge("abstain", END)

    # Answer generation moves to citation verification
    workflow.add_edge("generate_answer", "verify_citations")

    workflow.add_conditional_edges(
        "verify_citations",
        route_after_citation_verification,
        {
            "end": END,
            "safe_abstention": "safe_abstention",
        },
    )

    # Safe abstention terminates at END
    workflow.add_edge("safe_abstention", END)

    return workflow.compile()


# Compiled singleton graph
rag_graph = create_rag_graph()
