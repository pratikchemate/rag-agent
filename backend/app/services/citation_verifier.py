"""Deterministic sentence-level citation verification."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from app.core.logging import get_logger
from app.schemas.chat import Citation
from app.services.retrieval import RetrievalCandidate

logger = get_logger(__name__)

# Hedge / abstention phrases exempt from strict citation requirements (anchored to prevent exempting substantive claims)
EXEMPT_PATTERNS = [
    r"^(?:however,\s*)?(?:based\s+on\s+the\s+(?:provided|available)\s+documents?,\s*)?(?:there\s+is\s+)?no\s+(?:information|mention|record|evidence|data)\b",
    r"^(?:this\s+information\s+)?(?:cannot\s+be\s+(?:determined|found|verified)|could\s+not\s+be\s+found)\b",
    r"^(?:the\s+(?:provided|available)\s+documents?\s+)?do(?:es)?\s+not\s+(?:contain|mention|state|provide|specify)\b",
    r"^i\s+(?:apologize|could\s+not\s+find|do\s+not\s+have)\b",
    r"^(?:there\s+is\s+)?insufficient\s+information\b",
    r"^(?:this\s+is\s+)?not\s+(?:mentioned|specified|provided|available)\s+in\s+the\s+(?:provided|available)\s+documents?\b",
]

# Patterns for non-substantive LLM meta-commentary (e.g. self-reported word counts, instruction compliance affirmations)
META_PATTERNS = [
    r"^(?:\(?total\s+)?word\s+count\s*:\s*~?\d+\s*words?\)?\.?$",
    r"^(?:note:\s*)?all\s+sentences\s+(?:include|have|are)\s+cit(?:ed|ations)\b.*",
    r"^(?:note:\s*)?every\s+sentence\s+(?:is|includes)\s+cit(?:ed|ations)\b.*",
    r"^(?:note:\s*)?all\s+(?:statements|claims)\s+are\s+(?:directly\s+)?cited\b.*",
]

EXEMPT_REGEX = re.compile("|".join(EXEMPT_PATTERNS), re.IGNORECASE)
META_REGEX = re.compile("|".join(META_PATTERNS), re.IGNORECASE)
CITATION_LABEL_REGEX = re.compile(r"\[(S\d+)\]")


@dataclass
class VerificationResult:
    """Result of citation verification."""

    is_valid: bool
    abstained: bool
    answer: str
    citations: List[Citation]
    failure_reason: Optional[str] = None


class CitationVerifier:
    """Verifies citation labels and grounds them in actual retrieved chunks."""

    @classmethod
    def verify(
        cls,
        answer: str,
        retrieved_candidates: List[RetrievalCandidate],
    ) -> VerificationResult:
        """Verify that every factual claim is cited with a valid, provided chunk label."""
        clean_answer = answer.strip()
        if not clean_answer:
            return VerificationResult(
                is_valid=True,
                abstained=True,
                answer="No answer was generated from the provided documents.",
                citations=[],
                failure_reason="empty_answer",
            )

        # Strip trailing or standalone meta-commentary lines (e.g. word counts, prompt instruction echoes)
        cleaned_lines = [
            line for line in clean_answer.split("\n")
            if not (line.strip() and META_REGEX.match(line.strip()))
        ]
        if cleaned_lines:
            clean_answer = "\n".join(cleaned_lines).strip()

        # Build map of valid labels: S1 -> RetrievalCandidate
        valid_map: Dict[str, RetrievalCandidate] = {}
        for idx, candidate in enumerate(retrieved_candidates, start=1):
            label = f"S{idx}"
            valid_map[label] = candidate

        # Split into sentences (preserving punctuation)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_answer) if s.strip()]
        if not sentences:
            sentences = [clean_answer]

        # Check if entire answer is an explicit abstention
        all_exempt = True
        cited_labels_found: Set[str] = set()
        uncited_factual_sentences: List[str] = []

        for sent in sentences:
            labels_in_sentence = CITATION_LABEL_REGEX.findall(sent)
            is_exempt = bool(EXEMPT_REGEX.search(sent) or META_REGEX.match(sent))

            if labels_in_sentence:
                for lbl in labels_in_sentence:
                    # Check for unknown / hallucinated labels
                    if lbl not in valid_map:
                        logger.warning(f"Citation verification failed: unknown label [{lbl}] found")
                        return VerificationResult(
                            is_valid=False,
                            abstained=True,
                            answer="The available documents did not provide verifiable evidence for this response.",
                            citations=[],
                            failure_reason=f"hallucinated_label_{lbl}",
                        )
                    cited_labels_found.add(lbl)
                all_exempt = False
            elif not is_exempt:
                all_exempt = False
                uncited_factual_sentences.append(sent)

        # If answer is entirely abstention/hedge sentences
        if all_exempt:
            return VerificationResult(
                is_valid=True,
                abstained=True,
                answer=clean_answer,
                citations=[],
            )

        # Fail-closed if there are uncited factual sentences
        if uncited_factual_sentences:
            logger.warning(
                f"Citation verification failed: {len(uncited_factual_sentences)} uncited factual sentence(s): {uncited_factual_sentences}"
            )
            return VerificationResult(
                is_valid=False,
                abstained=True,
                answer="The available documents did not provide verifiable evidence for this response.",
                citations=[],
                failure_reason="uncited_factual_sentences",
            )

        # If no citations were found at all and not exempt
        if not cited_labels_found:
            return VerificationResult(
                is_valid=False,
                abstained=True,
                answer="The available documents did not provide verifiable evidence for this response.",
                citations=[],
                failure_reason="no_citations_present",
            )

        # Convert valid labels to grounded Citation objects
        # Sort citations by label index (S1, S2, ...)
        sorted_labels = sorted(
            cited_labels_found,
            key=lambda lbl: int(lbl[1:]) if lbl[1:].isdigit() else 999,
        )

        grounded_citations: List[Citation] = []
        for lbl in sorted_labels:
            cand = valid_map[lbl]
            grounded_citations.append(
                Citation(
                    label=lbl,
                    document_id=cand.document_id,
                    chunk_id=cand.chunk_id,
                    filename=cand.filename,
                    page_number=cand.page_number,
                    excerpt=cand.content[:500] + ("..." if len(cand.content) > 500 else ""),
                )
            )

        return VerificationResult(
            is_valid=True,
            abstained=False,
            answer=clean_answer,
            citations=grounded_citations,
        )
