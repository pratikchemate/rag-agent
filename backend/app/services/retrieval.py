"""Hybrid retrieval combining pgvector cosine similarity and PostgreSQL full-text search with RRF."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services.embeddings import get_embedding_service

logger = get_logger(__name__)


@dataclass
class RetrievalCandidate:
    """Retrieved candidate chunk with scoring metadata."""

    chunk_id: UUID
    document_id: UUID
    filename: str
    page_number: Optional[int]
    chunk_index: int
    content: str
    vector_rank: Optional[int] = None
    vector_similarity: Optional[float] = None
    keyword_rank: Optional[int] = None
    keyword_score: Optional[float] = None
    rrf_score: float = 0.0


@dataclass
class RetrievalResult:
    """Aggregated retrieval output with diagnostics."""

    candidates: List[RetrievalCandidate]
    vector_count: int
    keyword_count: int
    top_similarity: float
    evidence_sufficient: bool
    mode: str = "hybrid_rrf"


def is_evidence_sufficient(
    vector_sims: Sequence[Optional[float]],
    keyword_scores: Sequence[Optional[float]],
    settings: Optional[Settings] = None,
    mode: str = "hybrid_rrf",
) -> bool:
    """Determine whether retrieved evidence is sufficient based on multi-signal grounding."""
    if settings is None:
        settings = get_settings()

    valid_sims = [s for s in vector_sims if s is not None]
    valid_kw = [k for k in keyword_scores if k is not None]

    if not valid_sims and not valid_kw:
        return False

    top_sim = max(valid_sims, default=0.0)
    bottom_sim = min(valid_sims, default=0.0)
    gap = top_sim - bottom_sim

    max_kw = max(valid_kw, default=0.0)

    if mode == "vector":
        return top_sim >= settings.EVIDENCE_VECTOR_ONLY_MIN_SIMILARITY
    elif mode == "keyword":
        return max_kw >= settings.EVIDENCE_KEYWORD_ONLY_MIN_SCORE

    # Multi-signal composite check for hybrid search:
    # 1. Absolute semantic floor: weak semantic correspondence
    if top_sim < settings.MIN_RETRIEVAL_SIMILARITY:
        return False

    # 2. Low lexical grounding (single keyword hit) requires high semantic certainty
    if (
        max_kw <= settings.EVIDENCE_LOW_KW_THRESHOLD
        and top_sim < settings.EVIDENCE_LOW_KW_MIN_SIMILARITY
    ):
        return False

    # 3. Sub-critical semantic match requires strong lexical corroboration
    if (
        top_sim < settings.EVIDENCE_SUBCRITICAL_SIMILARITY
        and max_kw < settings.EVIDENCE_SUBCRITICAL_MIN_KW
    ):
        return False

    # 4. Score gap check: flat semantic distribution across candidates indicates background noise
    if top_sim < settings.EVIDENCE_SCORE_GAP_CEILING and gap < settings.EVIDENCE_SCORE_GAP_MIN:
        return False

    return True


class HybridRetrievalService:
    """Executes hybrid vector + full-text search with Reciprocal Rank Fusion."""

    def __init__(self):
        self.settings = get_settings()
        self.embedder = get_embedding_service()
        self.rrf_k = self.settings.RRF_K
        self.min_similarity = self.settings.MIN_RETRIEVAL_SIMILARITY

    def search(
        self,
        db: Session,
        owner_id: UUID,
        query_text: str,
        selected_document_ids: Optional[List[UUID]] = None,
        top_k: Optional[int] = None,
        candidate_k: Optional[int] = None,
        mode: str = "hybrid_rrf",
    ) -> RetrievalResult:
        """Run search and return top ranked chunks according to mode (hybrid_rrf, vector, or keyword)."""
        effective_top_k = top_k or self.settings.RETRIEVAL_TOP_K
        effective_candidate_k = candidate_k or self.settings.RETRIEVAL_CANDIDATE_K

        # Format document ID filter parameters safely
        doc_filter_sql = ""
        doc_filter_params: Dict[str, object] = {
            "owner_id": str(owner_id),
            "candidate_k": effective_candidate_k,
        }

        if selected_document_ids:
            doc_filter_sql = "AND c.document_id = ANY(CAST(:selected_doc_ids AS uuid[]))"
            doc_filter_params["selected_doc_ids"] = [
                str(UUID(str(did))) for did in selected_document_ids
            ]

        vector_rows = []
        if mode in ("hybrid_rrf", "vector"):
            # 1. Embed query
            query_vector = self.embedder.embed_query(query_text)
            vector_str = "[" + ",".join(str(f) for f in query_vector) + "]"

            # 2. Vector Search (Cosine Similarity)
            vector_sql = f"""
                SELECT
                    c.id AS chunk_id,
                    c.document_id,
                    d.filename,
                    c.page_number,
                    c.chunk_index,
                    c.content,
                    (1.0 - (c.embedding <=> (:query_vector)::vector)) AS similarity
                FROM document_chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE (c.owner_id = :owner_id OR d.is_public = true)
                  AND d.status = 'ready'
                  {doc_filter_sql}
                ORDER BY c.embedding <=> (:query_vector)::vector ASC
                LIMIT :candidate_k
            """
            vector_params = {**doc_filter_params, "query_vector": vector_str}
            vector_rows = db.execute(text(vector_sql), vector_params).mappings().all()

        keyword_rows = []
        if mode in ("hybrid_rrf", "keyword"):
            # 3. Keyword Search (OR-joined tsquery with ts_rank_cd)
            keyword_sql = f"""
                WITH query_lexemes AS (
                    SELECT string_agg(lex, ' | ') AS or_tsquery
                    FROM unnest(tsvector_to_array(to_tsvector('english', :query_text))) AS lex
                )
                SELECT
                    c.id AS chunk_id,
                    c.document_id,
                    d.filename,
                    c.page_number,
                    c.chunk_index,
                    c.content,
                    ts_rank_cd(c.search_vector, to_tsquery('english', ql.or_tsquery)) AS rank_score
                FROM document_chunks c
                JOIN documents d ON c.document_id = d.id
                CROSS JOIN query_lexemes ql
                WHERE ql.or_tsquery IS NOT NULL AND ql.or_tsquery <> ''
                  AND (c.owner_id = :owner_id OR d.is_public = true)
                  AND d.status = 'ready'
                  AND c.search_vector @@ to_tsquery('english', ql.or_tsquery)
                  {doc_filter_sql}
                ORDER BY rank_score DESC
                LIMIT :candidate_k
            """
            keyword_params = {**doc_filter_params, "query_text": query_text}
            keyword_rows = db.execute(text(keyword_sql), keyword_params).mappings().all()

        if mode == "vector":
            sorted_candidates = [
                RetrievalCandidate(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    filename=row["filename"],
                    page_number=row["page_number"],
                    chunk_index=row["chunk_index"],
                    content=row["content"],
                    vector_rank=rank,
                    vector_similarity=float(row["similarity"]),
                    rrf_score=float(row["similarity"]),
                )
                for rank, row in enumerate(vector_rows, start=1)
            ]
        elif mode == "keyword":
            sorted_candidates = [
                RetrievalCandidate(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    filename=row["filename"],
                    page_number=row["page_number"],
                    chunk_index=row["chunk_index"],
                    content=row["content"],
                    keyword_rank=rank,
                    keyword_score=float(row["rank_score"]),
                    rrf_score=float(row["rank_score"]),
                )
                for rank, row in enumerate(keyword_rows, start=1)
            ]
        else:
            # 4. Reciprocal Rank Fusion (RRF)
            # rrf_score = sum(1 / (k + rank_i))
            candidates_by_id: Dict[UUID, RetrievalCandidate] = {}

            # Process vector rankings
            for rank, row in enumerate(vector_rows, start=1):
                cid = row["chunk_id"]
                sim = float(row["similarity"])
                cand = RetrievalCandidate(
                    chunk_id=cid,
                    document_id=row["document_id"],
                    filename=row["filename"],
                    page_number=row["page_number"],
                    chunk_index=row["chunk_index"],
                    content=row["content"],
                    vector_rank=rank,
                    vector_similarity=sim,
                    rrf_score=1.0 / (self.rrf_k + rank),
                )
                candidates_by_id[cid] = cand

            # Process keyword rankings
            for rank, row in enumerate(keyword_rows, start=1):
                cid = row["chunk_id"]
                k_score = float(row["rank_score"])
                rrf_contribution = 1.0 / (self.rrf_k + rank)
                if cid in candidates_by_id:
                    cand = candidates_by_id[cid]
                    cand.keyword_rank = rank
                    cand.keyword_score = k_score
                    cand.rrf_score += rrf_contribution
                else:
                    candidates_by_id[cid] = RetrievalCandidate(
                        chunk_id=cid,
                        document_id=row["document_id"],
                        filename=row["filename"],
                        page_number=row["page_number"],
                        chunk_index=row["chunk_index"],
                        content=row["content"],
                        keyword_rank=rank,
                        keyword_score=k_score,
                        rrf_score=rrf_contribution,
                    )

            # Sort candidates by combined RRF score descending
            sorted_candidates = sorted(
                candidates_by_id.values(),
                key=lambda c: c.rrf_score,
                reverse=True,
            )

        top_candidates = sorted_candidates[:effective_top_k]
        top_similarity = max(
            (c.vector_similarity for c in top_candidates if c.vector_similarity is not None),
            default=0.0,
        )

        evidence_sufficient = self.evaluate_evidence_sufficiency(top_candidates, mode=mode)

        logger.info(
            f"Retrieval finished: {len(vector_rows)} vector, {len(keyword_rows)} keyword. "
            f"Top similarity: {top_similarity:.3f}, sufficient: {evidence_sufficient}"
        )

        return RetrievalResult(
            candidates=top_candidates,
            vector_count=len(vector_rows),
            keyword_count=len(keyword_rows),
            top_similarity=top_similarity,
            evidence_sufficient=evidence_sufficient,
            mode=mode,
        )

    def evaluate_evidence_sufficiency(
        self,
        candidates: List[RetrievalCandidate],
        mode: str = "hybrid_rrf",
    ) -> bool:
        """Determine whether retrieved evidence is sufficient based on multi-signal grounding."""
        if not candidates:
            return False

        return is_evidence_sufficient(
            vector_sims=[c.vector_similarity for c in candidates],
            keyword_scores=[c.keyword_score for c in candidates],
            settings=self.settings,
            mode=mode,
        )


_default_retrieval: Optional[HybridRetrievalService] = None


def get_retrieval_service() -> HybridRetrievalService:
    """Return default retrieval service."""
    global _default_retrieval
    if _default_retrieval is None:
        _default_retrieval = HybridRetrievalService()
    return _default_retrieval
