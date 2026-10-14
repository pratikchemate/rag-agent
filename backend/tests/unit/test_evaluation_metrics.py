"""Unit tests for deterministic evaluation metrics."""

import sys
from pathlib import Path

import pytest

# Ensure repo root is on sys.path so evaluation.metrics is importable
REPO_ROOT = Path(__file__).resolve().parents[2].parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.metrics import (  # noqa: E402
    abstention_accuracy,
    citation_validity_rate,
    false_abstention_rate,
    lexical_overlap_faithfulness,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k():
    retrieved = ["doc1.pdf", "doc2.pdf", "doc3.pdf", "doc4.pdf"]
    relevant = ["doc2.pdf", "doc4.pdf"]

    # K=1: only doc1 -> 0 hits
    assert recall_at_k(retrieved, relevant, k=1) == 0.0

    # K=2: doc1, doc2 -> 1 hit out of 2
    assert recall_at_k(retrieved, relevant, k=2) == 0.5

    # K=4: doc1, doc2, doc3, doc4 -> 2 hits out of 2
    assert recall_at_k(retrieved, relevant, k=4) == 1.0

    # Empty relevant -> 1.0
    assert recall_at_k(retrieved, [], k=3) == 1.0


def test_precision_at_k():
    retrieved = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    relevant = ["doc2.pdf"]

    assert precision_at_k(retrieved, relevant, k=1) == 0.0
    assert precision_at_k(retrieved, relevant, k=2) == 0.5
    assert precision_at_k([], relevant, k=5) == 0.0


def test_reciprocal_rank_and_mrr():
    # Query 1: hit at rank 1
    assert reciprocal_rank(["a", "b", "c"], ["a"]) == 1.0

    # Query 2: hit at rank 2
    assert reciprocal_rank(["x", "y", "z"], ["y"]) == 0.5

    # Query 3: no hit
    assert reciprocal_rank(["m", "n"], ["z"]) == 0.0

    retrieved_lists = [["a", "b"], ["x", "y"], ["m", "n"]]
    relevant_lists = [["a"], ["y"], ["z"]]

    # (1.0 + 0.5 + 0.0) / 3 = 0.5
    assert mean_reciprocal_rank(retrieved_lists, relevant_lists) == pytest.approx(0.5)


def test_citation_validity_rate():
    available = ["S1", "S2", "S3"]

    # All valid
    assert citation_validity_rate(["S1", "S2"], available) == 1.0

    # One hallucinated
    assert citation_validity_rate(["S1", "S99"], available) == 0.5

    # No citations claimed
    assert citation_validity_rate([], available) == 1.0


def test_abstention_metrics():
    # 4 queries: 2 should answer (False), 2 should abstain (True)
    gt = [False, False, True, True]
    # Prediction: answered Q1, falsely abstained on Q2, correctly abstained on Q3, falsely answered Q4
    pred = [False, True, True, False]

    # Accuracy: 2 out of 4 correct = 0.5
    assert abstention_accuracy(pred, gt) == 0.5

    # False abstention: out of 2 answerable queries (Q1, Q2), system abstained on Q2 -> 1 / 2 = 0.5
    assert false_abstention_rate(pred, gt) == 0.5


def test_lexical_overlap_faithfulness():
    sentence = "Clients must implement a maximum of three retries with backoff."
    chunk_full = "The payment specification states that clients must implement a maximum of three retries with exponential backoff delay."
    chunk_disjoint = "The audit logging policy requires retaining records for 365 days."

    overlap_high = lexical_overlap_faithfulness(sentence, chunk_full)
    overlap_zero = lexical_overlap_faithfulness(sentence, chunk_disjoint)

    assert overlap_high >= 0.7
    assert overlap_zero <= 0.1
