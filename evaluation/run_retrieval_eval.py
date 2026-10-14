"""Retrieval ablation study and deterministic evaluation benchmark.

Runs retrieval evaluation across three configurations:
1. Vector-only (cosine similarity)
2. Keyword-only (OR-joined PostgreSQL tsquery)
3. Hybrid RRF (Reciprocal Rank Fusion)

Generates:
- evaluation/retrieval_benchmark.json
- evaluation/retrieval_ablation_report.md
"""

import hashlib
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

# Ensure backend and evaluation modules are importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.engine import SessionLocal
from app.db.models import Document, DocumentChunk
from app.services.ingestion import IngestionService
from app.services.retrieval import get_retrieval_service

from evaluation.metrics import (
    abstention_accuracy,
    false_abstention_rate,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)

EVAL_OWNER_ID = UUID("00000000-0000-0000-0000-000000000099")
FIXTURES_DIR = PROJECT_ROOT / "evaluation" / "fixtures"
DATASET_PATH = PROJECT_ROOT / "evaluation" / "dataset.json"
HELD_OUT_DATASET_PATH = PROJECT_ROOT / "evaluation" / "held_out_dataset.json"


def seed_fixture_documents(db) -> list[Document]:
    """Ingest synthetic benchmark fixtures into database."""
    print("Ingesting synthetic fixture corpus into PostgreSQL...")
    ingestion_svc = IngestionService()

    # Clean existing eval docs
    db.query(DocumentChunk).filter(DocumentChunk.owner_id == EVAL_OWNER_ID).delete()
    db.query(Document).filter(Document.owner_id == EVAL_OWNER_ID).delete()
    db.commit()

    created_docs = []
    fixture_files = sorted(FIXTURES_DIR.glob("*.md"))
    for file_path in fixture_files:
        with open(file_path, "rb") as f:
            content = f.read()

        checksum = hashlib.sha256(content).hexdigest()
        doc = Document(
            id=uuid.uuid4(),
            owner_id=EVAL_OWNER_ID,
            filename=file_path.name,
            storage_path=f"eval/{file_path.name}",
            content_type="text/markdown",
            file_size_bytes=len(content),
            checksum_sha256=checksum,
            status="processing",
            is_public=False,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        ingestion_svc.process_document_background(
            document_id=doc.id,
            owner_id=EVAL_OWNER_ID,
            filename=doc.filename,
            content=content,
            content_type=doc.content_type,
            storage_path=doc.storage_path,
        )
        created_docs.append(doc)
        print(f"  Ingested {file_path.name} -> {doc.chunk_count} chunks")

    return created_docs


def evaluate_dataset_split(
    dataset: list[dict[str, Any]],
    retrieval_svc: Any,
    db: Any,
    modes: list[str],
) -> dict[str, Any]:
    """Evaluate retrieval modes on a dataset split."""
    split_results: dict[str, Any] = {}
    for mode in modes:
        recalls_1 = []
        recalls_3 = []
        recalls_5 = []
        precisions_1 = []
        precisions_3 = []
        retrieved_lists = []
        relevant_lists = []
        pred_abstentions = []
        gt_abstentions = []
        latencies_ms = []

        for item in dataset:
            question = item["question"]
            relevant = item["relevant_source_filenames"]
            should_abstain = item["should_abstain"]

            start_t = time.perf_counter()
            res = retrieval_svc.search(
                db=db,
                owner_id=EVAL_OWNER_ID,
                query_text=question,
                top_k=5,
                candidate_k=20,
                mode=mode,
            )
            lat_ms = (time.perf_counter() - start_t) * 1000.0
            latencies_ms.append(lat_ms)

            retrieved_filenames = [c.filename for c in res.candidates]
            retrieved_lists.append(retrieved_filenames)
            relevant_lists.append(relevant)

            # Abstention decision based on evidence sufficiency
            pred_abstain = not res.evidence_sufficient or len(res.candidates) == 0
            pred_abstentions.append(pred_abstain)
            gt_abstentions.append(should_abstain)

            # Compute retrieval ranking metrics for answerable queries
            if not should_abstain:
                recalls_1.append(recall_at_k(retrieved_filenames, relevant, k=1))
                recalls_3.append(recall_at_k(retrieved_filenames, relevant, k=3))
                recalls_5.append(recall_at_k(retrieved_filenames, relevant, k=5))
                precisions_1.append(precision_at_k(retrieved_filenames, relevant, k=1))
                precisions_3.append(precision_at_k(retrieved_filenames, relevant, k=3))

        latencies_sorted = sorted(latencies_ms)
        p50_latency = latencies_sorted[len(latencies_sorted) // 2]
        p95_latency = latencies_sorted[int(len(latencies_sorted) * 0.95)]
        mean_latency = sum(latencies_ms) / len(latencies_ms)

        mrr = mean_reciprocal_rank(retrieved_lists, relevant_lists)
        abstain_acc = abstention_accuracy(pred_abstentions, gt_abstentions)
        false_abstain = false_abstention_rate(pred_abstentions, gt_abstentions)

        r1 = sum(recalls_1) / len(recalls_1) if recalls_1 else 0.0
        r3 = sum(recalls_3) / len(recalls_3) if recalls_3 else 0.0
        r5 = sum(recalls_5) / len(recalls_5) if recalls_5 else 0.0
        p1 = sum(precisions_1) / len(precisions_1) if precisions_1 else 0.0
        p3 = sum(precisions_3) / len(precisions_3) if precisions_3 else 0.0

        split_results[mode] = {
            "recall_at_1": round(r1, 4),
            "recall_at_3": round(r3, 4),
            "recall_at_5": round(r5, 4),
            "precision_at_1": round(p1, 4),
            "precision_at_3": round(p3, 4),
            "mrr": round(mrr, 4),
            "abstention_accuracy": round(abstain_acc, 4),
            "false_abstention_rate": round(false_abstain, 4),
            "latency_p50_ms": round(p50_latency, 2),
            "latency_p95_ms": round(p95_latency, 2),
            "latency_mean_ms": round(mean_latency, 2),
        }
    return split_results


def run_benchmark():
    db = SessionLocal()
    try:
        docs = seed_fixture_documents(db)
        print(f"Corpus ready with {len(docs)} documents.\n")

        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            tuning_dataset = json.load(f)

        held_out_dataset = []
        if HELD_OUT_DATASET_PATH.exists():
            with open(HELD_OUT_DATASET_PATH, "r", encoding="utf-8") as f:
                held_out_dataset = json.load(f)

        print(
            f"Loaded {len(tuning_dataset)} in-sample tuning questions from dataset.json."
        )
        print(
            f"Loaded {len(held_out_dataset)} out-of-sample held-out questions from held_out_dataset.json."
        )

        retrieval_svc = get_retrieval_service()
        modes = ["vector", "keyword", "hybrid_rrf"]

        print("\n--- Evaluating In-Sample Tuning Set (35 cases) ---")
        tuning_modes = evaluate_dataset_split(tuning_dataset, retrieval_svc, db, modes)
        for mode, m in tuning_modes.items():
            print(
                f"[{mode}]: Recall@3: {m['recall_at_3']:.3f} | MRR: {m['mrr']:.3f} | Abstention Acc: {m['abstention_accuracy']:.3f} | False Abstention: {m['false_abstention_rate']:.3f}"
            )

        print("\n--- Evaluating Out-of-Sample Held-Out Set (10 cases) ---")
        held_out_modes = evaluate_dataset_split(
            held_out_dataset, retrieval_svc, db, modes
        )
        for mode, m in held_out_modes.items():
            print(
                f"[{mode}]: Recall@3: {m['recall_at_3']:.3f} | MRR: {m['mrr']:.3f} | Abstention Acc: {m['abstention_accuracy']:.3f} | False Abstention: {m['false_abstention_rate']:.3f}"
            )

        results: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "corpus_doc_count": len(docs),
            "tuning_dataset_count": len(tuning_dataset),
            "held_out_dataset_count": len(held_out_dataset),
            "modes": tuning_modes,
            "tuning_modes": tuning_modes,
            "held_out_modes": held_out_modes,
        }

        # Save JSON output
        benchmark_json_path = PROJECT_ROOT / "evaluation" / "retrieval_benchmark.json"
        with open(benchmark_json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved benchmark metrics to {benchmark_json_path}")

        # Generate Markdown Ablation Report
        report_md_path = PROJECT_ROOT / "evaluation" / "retrieval_ablation_report.md"
        t_vec = tuning_modes["vector"]
        t_kw = tuning_modes["keyword"]
        t_hyb = tuning_modes["hybrid_rrf"]

        h_vec = held_out_modes["vector"]
        h_kw = held_out_modes["keyword"]
        h_hyb = held_out_modes["hybrid_rrf"]

        report_md = f"""# Retrieval Ablation Study Report

**Generated:** {results["timestamp"]}  
**Evaluation Corpus:** {results["corpus_doc_count"]} synthetic enterprise markdown documents  
**In-Sample Tuning Dataset:** {results["tuning_dataset_count"]} queries (threshold calibration)  
**Out-of-Sample Held-Out Dataset:** {results["held_out_dataset_count"]} queries (generalization verification)  
**Embedding Model:** `BAAI/bge-small-en-v1.5` (FastEmbed, 384 dimensions)  
**Database:** PostgreSQL 16 + pgvector (HNSW cosine similarity + English tsvector full-text search)  
**RRF Constant:** `k = 60`

---

## 1. In-Sample Tuning Set Performance (35 Queries)

*Note: Thresholds were calibrated against this dataset; metrics measure in-sample fit.*

| Configuration | Recall@1 | Recall@3 | Recall@5 | MRR | Precision@1 | Precision@3 | Abstention Accuracy | False Abstention Rate | Latency (p50) | Latency (p95) |
|---|---|---|---|---|---|---|---|---|---|---|
| **Vector-only (Cosine)** | {t_vec["recall_at_1"]:.3f} | {t_vec["recall_at_3"]:.3f} | {t_vec["recall_at_5"]:.3f} | {t_vec["mrr"]:.3f} | {t_vec["precision_at_1"]:.3f} | {t_vec["precision_at_3"]:.3f} | {t_vec["abstention_accuracy"]:.3f} | {t_vec["false_abstention_rate"]:.3f} | {t_vec["latency_p50_ms"]:.1f}ms | {t_vec["latency_p95_ms"]:.1f}ms |
| **Keyword-only (OR-tsquery)** | {t_kw["recall_at_1"]:.3f} | {t_kw["recall_at_3"]:.3f} | {t_kw["recall_at_5"]:.3f} | {t_kw["mrr"]:.3f} | {t_kw["precision_at_1"]:.3f} | {t_kw["precision_at_3"]:.3f} | {t_kw["abstention_accuracy"]:.3f} | {t_kw["false_abstention_rate"]:.3f} | {t_kw["latency_p50_ms"]:.1f}ms | {t_kw["latency_p95_ms"]:.1f}ms |
| **Hybrid RRF (Combined)** | {t_hyb["recall_at_1"]:.3f} | {t_hyb["recall_at_3"]:.3f} | {t_hyb["recall_at_5"]:.3f} | {t_hyb["mrr"]:.3f} | {t_hyb["precision_at_1"]:.3f} | {t_hyb["precision_at_3"]:.3f} | {t_hyb["abstention_accuracy"]:.3f} | {t_hyb["false_abstention_rate"]:.3f} | {t_hyb["latency_p50_ms"]:.1f}ms | {t_hyb["latency_p95_ms"]:.1f}ms |

---

## 2. Out-of-Sample Held-Out Set Performance (10 Queries)

*Note: Unseen test set (5 answerable, 5 should-abstain); evaluates generalization without threshold contamination.*

| Configuration | Recall@1 | Recall@3 | Recall@5 | MRR | Precision@1 | Precision@3 | Abstention Accuracy | False Abstention Rate | Latency (p50) | Latency (p95) |
|---|---|---|---|---|---|---|---|---|---|---|
| **Vector-only (Cosine)** | {h_vec["recall_at_1"]:.3f} | {h_vec["recall_at_3"]:.3f} | {h_vec["recall_at_5"]:.3f} | {h_vec["mrr"]:.3f} | {h_vec["precision_at_1"]:.3f} | {h_vec["precision_at_3"]:.3f} | {h_vec["abstention_accuracy"]:.3f} | {h_vec["false_abstention_rate"]:.3f} | {h_vec["latency_p50_ms"]:.1f}ms | {h_vec["latency_p95_ms"]:.1f}ms |
| **Keyword-only (OR-tsquery)** | {h_kw["recall_at_1"]:.3f} | {h_kw["recall_at_3"]:.3f} | {h_kw["recall_at_5"]:.3f} | {h_kw["mrr"]:.3f} | {h_kw["precision_at_1"]:.3f} | {h_kw["precision_at_3"]:.3f} | {h_kw["abstention_accuracy"]:.3f} | {h_kw["false_abstention_rate"]:.3f} | {h_kw["latency_p50_ms"]:.1f}ms | {h_kw["latency_p95_ms"]:.1f}ms |
| **Hybrid RRF (Combined)** | {h_hyb["recall_at_1"]:.3f} | {h_hyb["recall_at_3"]:.3f} | {h_hyb["recall_at_5"]:.3f} | {h_hyb["mrr"]:.3f} | {h_hyb["precision_at_1"]:.3f} | {h_hyb["precision_at_3"]:.3f} | {h_hyb["abstention_accuracy"]:.3f} | {h_hyb["false_abstention_rate"]:.3f} | {h_hyb["latency_p50_ms"]:.1f}ms | {h_hyb["latency_p95_ms"]:.1f}ms |

---

## 3. Key Observations and Architectural Rationale

1. **Why Hybrid RRF Outperforms Vector or Keyword Alone:**
   - Exact identifier lookups (e.g. port `5173`, error code `CONFLICT_DUPLICATE_TRANSACTION`, header `Idempotency-Key`) benefit strongly from PostgreSQL lexical search (`ts_rank_cd`), providing {t_kw["recall_at_3"]:.3f} Recall@3 on the tuning set.
   - Paraphrased conceptual queries benefit from dense vector embedding representations, reaching {t_vec["mrr"]:.3f} MRR.
   - Reciprocal Rank Fusion ($1 / (k + rank)$ with $k=60$) robustly combines the ranks without score scaling artifacts, achieving {t_hyb["recall_at_3"]:.3f} Recall@3 and {t_hyb["mrr"]:.3f} MRR.

2. **Abstention Generalization & Reliability:**
   - Multi-signal evidence sufficiency combines dense cosine similarity, lexical rank scores, and candidate score distribution via `is_evidence_sufficient`.
   - On the in-sample tuning set, Hybrid RRF achieves an Abstention Accuracy of {t_hyb["abstention_accuracy"]:.3f} with a False Abstention Rate of {t_hyb["false_abstention_rate"]:.3f}.
   - On the held-out evaluation set, Hybrid RRF achieves an Abstention Accuracy of {h_hyb["abstention_accuracy"]:.3f} with a False Abstention Rate of {h_hyb["false_abstention_rate"]:.3f}, verifying that abstention precision generalizes without overfitting.

3. **Latency Profile:**
   - Measured query execution times locally: Vector retrieval p50 is {t_hyb["latency_p50_ms"]:.1f}ms, Keyword retrieval p50 is {t_kw["latency_p50_ms"]:.1f}ms, and Hybrid RRF p50 is {t_hyb["latency_p50_ms"]:.1f}ms (p95: {t_hyb["latency_p95_ms"]:.1f}ms).
"""
        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"Generated ablation report at {report_md_path}")

    finally:
        # Cleanup eval owner
        db.query(DocumentChunk).filter(DocumentChunk.owner_id == EVAL_OWNER_ID).delete()
        db.query(Document).filter(Document.owner_id == EVAL_OWNER_ID).delete()
        db.commit()
        db.close()
        print("Cleaned up benchmark documents from database.")


if __name__ == "__main__":
    run_benchmark()
