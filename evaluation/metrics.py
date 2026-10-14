"""Deterministic evaluation metrics for retrieval and evidence verification.

No external API calls or LLM dependencies are used in this module.
"""

import re
from collections.abc import Sequence


def recall_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Calculate Recall@K: fraction of ground-truth relevant items found in top-k retrieved items.

    Args:
        retrieved: Ordered list of retrieved identifiers (e.g. filenames or chunk IDs).
        relevant: Set/list of ground truth relevant identifiers.
        k: Cutoff depth.
    """
    if not relevant:
        return 1.0

    top_k_set: set[str] = set(retrieved[:k])
    relevant_set: set[str] = set(relevant)

    hits = len(top_k_set.intersection(relevant_set))
    return float(hits) / float(len(relevant_set))


def precision_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Calculate Precision@K: fraction of top-k retrieved items that are relevant."""
    if k <= 0:
        return 0.0

    top_k = retrieved[:k]
    if not top_k:
        return 0.0

    relevant_set: set[str] = set(relevant)
    hits = sum(1 for item in top_k if item in relevant_set)
    return float(hits) / float(len(top_k))


def reciprocal_rank(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
    """Calculate Reciprocal Rank (RR): 1 / rank of first relevant item in retrieved list (1-based)."""
    relevant_set: set[str] = set(relevant)
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant_set:
            return 1.0 / float(rank)
    return 0.0


def mean_reciprocal_rank(
    retrieved_lists: Sequence[Sequence[str]], relevant_lists: Sequence[Sequence[str]]
) -> float:
    """Calculate Mean Reciprocal Rank (MRR) across multiple queries."""
    if not retrieved_lists or len(retrieved_lists) != len(relevant_lists):
        return 0.0

    total_rr = sum(
        reciprocal_rank(ret, rel)
        for ret, rel in zip(retrieved_lists, relevant_lists)
        if rel  # Only queries with relevant targets
    )
    count = sum(1 for rel in relevant_lists if rel)
    return total_rr / count if count > 0 else 0.0


def citation_validity_rate(
    cited_labels: Sequence[str], available_labels: Sequence[str]
) -> float:
    """Calculate citation validity rate: fraction of generated labels that map to actual retrieved sources."""
    if not cited_labels:
        return 1.0  # No citations claimed, trivially valid

    available_set: set[str] = set(available_labels)
    valid_count = sum(1 for label in cited_labels if label in available_set)
    return float(valid_count) / float(len(cited_labels))


def abstention_accuracy(
    predicted_abstentions: Sequence[bool], ground_truth_abstentions: Sequence[bool]
) -> float:
    """Calculate abstention classification accuracy across all test questions."""
    if not predicted_abstentions or len(predicted_abstentions) != len(
        ground_truth_abstentions
    ):
        return 0.0

    correct = sum(
        1
        for pred, gt in zip(predicted_abstentions, ground_truth_abstentions)
        if pred == gt
    )
    return float(correct) / float(len(predicted_abstentions))


def false_abstention_rate(
    predicted_abstentions: Sequence[bool], ground_truth_abstentions: Sequence[bool]
) -> float:
    """Calculate false abstention rate: fraction of answerable queries where system incorrectly abstained.

    Mandated by AGENTS.md §11 & §15 as a diagnostic metric for strict citation verification.
    """
    answerable_count = sum(1 for gt in ground_truth_abstentions if not gt)
    if answerable_count == 0:
        return 0.0

    false_abstentions = sum(
        1
        for pred, gt in zip(predicted_abstentions, ground_truth_abstentions)
        if pred is True and gt is False
    )
    return float(false_abstentions) / float(answerable_count)


def tokenize_text(text: str) -> set[str]:
    """Simple alphanumeric word tokenization for lexical overlap."""
    words = re.findall(r"\b\w+\b", text.lower())
    return {w for w in words if len(w) > 2}


def lexical_overlap_faithfulness(sentence: str, chunk_content: str) -> float:
    """Calculate unigram lexical overlap between a cited sentence and its referenced chunk.

    Used as an offline, non-LLM proxy for citation faithfulness per AGENTS.md §11 & §15.
    Returns: fraction of sentence content words present in the referenced chunk.
    """
    sent_tokens = tokenize_text(sentence)
    if not sent_tokens:
        return 0.0

    chunk_tokens = tokenize_text(chunk_content)
    overlap = sent_tokens.intersection(chunk_tokens)
    return float(len(overlap)) / float(len(sent_tokens))
