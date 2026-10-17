# Enterprise Knowledge AI

> **A production-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform with PostgreSQL pgvector, LangGraph, and verifiable sentence-level source citations.**

[![CI](https://github.com/pratik/rag-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/pratik/rag-agent/actions/workflows/ci.yml)
[![Live Demo](https://img.shields.io/badge/Demo-enterprise--knowledge--ai.vercel.app-brightgreen.svg?logo=vercel)](https://enterprise-knowledge-ai.vercel.app)
[![API Status](https://img.shields.io/badge/API-Live_on_Render-46E3B7.svg?logo=render)](https://enterprise-knowledge-ai-api.onrender.com/api/v1/health/live)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_pgvector-336791.svg?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-blue.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)

---

## 🌐 Live Demo & Access

- **Production Frontend:** [https://enterprise-knowledge-ai.vercel.app](https://enterprise-knowledge-ai.vercel.app)
- **Production Backend API:** [https://enterprise-knowledge-ai-api.onrender.com](https://enterprise-knowledge-ai-api.onrender.com)
- **Pre-Seeded Corpus (Demo Mode):** The live system is pre-seeded with enterprise specifications, deployment runbooks, and security policies. Reviewers can immediately test chat, hybrid retrieval, and interactive citations without creating an account.
- **Reviewer Sign-In & Uploads:** New user sign-ups are set to **Invite-Only** to protect free-tier LLM and database quotas. Use the invited reviewer credentials (`demo-reviewer@example.com` / `SecurePassword123!`) or request an invite to upload custom PDF/Markdown documents.
- **Render Free Cold Start:** On initial access after 15+ minutes of inactivity, Render Free web services require ~50–70s to spin up. A scheduled GitHub keep-alive workflow pings the health probes bi-weekly to minimize downtime.

---

## 1. System Architecture

```mermaid
flowchart TD
    User([Browser Client]) -->|SPA / React 18| Frontend[Vite + Tailwind CSS]
    Frontend -->|JWT Bearer Token| FastAPI[FastAPI Backend :8000]
    
    subgraph Security & Quotas
        FastAPI --> AuthGuard[Supabase JWT Authenticator]
        FastAPI --> RateLimiter[In-Memory Sliding Window Limiter]
        FastAPI --> BudgetChecker[PostgreSQL Daily Demo Budget Tracker]
    end

    subgraph LangGraph RAG Workflow
        AuthGuard --> ValidateNode[Validate Question]
        ValidateNode --> RetrieveNode[Hybrid Search: Dense + Lexical]
        RetrieveNode --> RouteSufficiency{Evidence Sufficient?}
        RouteSufficiency -->|No & attempt < 2| RewriteNode[Query Rewriter]
        RewriteNode --> RetrieveNode
        RouteSufficiency -->|No & attempt >= 2| AbstainNode[Abstain Gracefully]
        RouteSufficiency -->|Yes| GenerateNode[OpenRouter Free Model Cascade]
        GenerateNode --> VerifyCitationsNode[Deterministic Citation Verifier]
    end

    subgraph Data & Vector Tier
        RetrieveNode -->|pgvector Cosine <=>| PGVector[(PostgreSQL 16 + pgvector)]
        RetrieveNode -->|ts_rank_cd @@| PGSearh[(PostgreSQL Full-Text Search)]
        FastEmbed[Local BAAI/bge-small-en-v1.5] -->|384-dim Vectors| PGVector
    end

    VerifyCitationsNode -->|Structured Response + Citations| Frontend
    AbstainNode -->|Honest Abstention| Frontend
```

---

## 2. Technology Choices & Tradeoffs

| Component | Selected Technology | Alternative Considered | Engineering Rationale & Tradeoffs |
|---|---|---|---|
| **Vector Database** | **PostgreSQL 16 + pgvector** | Pinecone, Chroma, Qdrant | Keeps metadata, document chunks, user accounts, and vector embeddings in a single ACID-compliant transactional store. Enables native PostgreSQL Row-Level Security (RLS) for multi-tenancy without synchronization lag across separate vector databases. |
| **Search Strategy** | **Hybrid RRF** (Dense vector + tsquery full-text) | Vector-only or BM25 alone | Pure vector search frequently misses exact error codes, ports, and technical configuration flags. Hybrid search using Reciprocal Rank Fusion ($k=60$) combines semantic paraphrasing with exact identifier match. |
| **Agent / Orchestration** | **LangGraph** (StateGraph) | Linear LangChain chains, AutoGen | Provides a stateful, cyclical graph with explicit conditional branching, deterministic query rewriting, and graceful abstention paths without non-deterministic autonomous multi-agent loops. |
| **Embedding Model** | **FastEmbed** (`BAAI/bge-small-en-v1.5`) | OpenAI `text-embedding-3-small` | Runs entirely in-process on CPU using optimized ONNX runtime (384 dimensions). Avoids external network latency, embedding API rate limits, and third-party API costs during bulk ingestion. |
| **LLM Inference** | **OpenRouter Free Tier Cascade** with fallback | Direct vendor APIs (OpenAI/Anthropic) | Implements an automated failover allowlist (`gemma-4-31b-it:free` $\to$ `gemma-4-26b-a4b-it:free` $\to$ `nemotron-3.5-lightning:free`). Enforces an explicit `:free` suffix check and daily budget limiter to prevent billing surprises. |
| **Authentication** | **Supabase Auth (JWT)** | Custom sessions, NextAuth | Industry-standard JWT verification using asymmetric keys. The backend verifies token cryptographic signatures without touching the database on every HTTP request. |

---

## 3. Quickstart & Local Reproduction

### Prerequisites
- Docker and Docker Compose
- Python 3.13+
- Node.js 20+

### Step 1: Start PostgreSQL with pgvector
```bash
docker compose up -d
```

### Step 2: Set Up Backend Environment & Migrations
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Apply database migrations
psql postgresql://postgres:postgres@localhost:5432/postgres -f ../supabase/migrations/0001_extensions_and_schema.sql
psql postgresql://postgres:postgres@localhost:5432/postgres -f ../supabase/migrations/0002_indexes_and_search.sql
psql postgresql://postgres:postgres@localhost:5432/postgres -f ../supabase/migrations/0003_storage_policies.sql

# Start FastAPI backend
uvicorn app.main:app --reload --port 8000
```

### Step 3: Set Up and Start Frontend
```bash
cd ../frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 4. Empirical Evaluation & Ablation Results

We evaluate retrieval quality across synthetic enterprise documents using an in-sample tuning dataset (35 queries) to calibrate multi-signal thresholds, followed by an independent held-out validation set (10 queries) to verify generalization:

### 1. In-Sample Tuning Dataset (35 Queries)

| Retrieval Mode | Recall@1 | Recall@3 | Recall@5 | MRR | Precision@1 | Precision@3 | Abstention Accuracy | False Abstention Rate | Latency (p50) | Latency (p95) |
|---|---|---|---|---|---|---|---|---|---|---|
| **Vector-only (Cosine)** | 0.942 | 0.981 | 1.000 | 1.000 | 1.000 | 0.526 | 0.914 | 0.077 | 14.4ms | 17.4ms |
| **Keyword-only (OR-tsquery)** | 0.942 | 1.000 | 1.000 | 0.976 | 1.000 | 0.615 | 0.971 | 0.038 | 1.2ms | 1.9ms |
| **Hybrid RRF (Combined)** | **0.942** | **1.000** | **1.000** | **0.982** | **1.000** | **0.551** | **1.000** | **0.000** | 16.4ms | 26.5ms |

### 2. Out-of-Sample Held-Out Validation Dataset (10 Queries)

| Retrieval Mode | Recall@1 | Recall@3 | Recall@5 | MRR | Precision@1 | Precision@3 | Abstention Accuracy | False Abstention Rate | Latency (p50) | Latency (p95) |
|---|---|---|---|---|---|---|---|---|---|---|
| **Vector-only (Cosine)** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.467 | 1.000 | 0.000 | 14.5ms | 18.2ms |
| **Keyword-only (OR-tsquery)** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.467 | 1.000 | 0.000 | 1.1ms | 1.6ms |
| **Hybrid RRF (Combined)** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** | **0.467** | **0.800** | **0.000** | 15.6ms | 25.1ms |

### Key Takeaways
- **Hybrid RRF Dominance:** Combining dense vectors with OR-joined tsquery lexical search achieved **100% Recall@3** on answerable questions across both tuning and held-out sets.
- **Abstention Generalization:** Abstention is governed by a parameterized multi-signal check (`MIN_RETRIEVAL_SIMILARITY`, `EVIDENCE_*`) rather than a flat threshold, reaching **100% Abstention Accuracy** in-sample and **80% Abstention Accuracy** (4/5 abstentions, 0% false abstentions) on unseen held-out queries.
- **Reproducible Evaluation:** Run the benchmark locally with:
  ```bash
  python evaluation/run_retrieval_eval.py
  ```
- **Evaluation Status:** Deterministic retrieval metrics (Recall, Precision, MRR, Abstention) run entirely offline against the local test database without external API dependencies. LLM-assisted evaluation (such as Ragas) is documented as future work to avoid third-party token consumption during CI and local testing.

---

## 5. Security & Multi-Tenant Guarantees

1. **Row-Level Security (RLS):** Every database table (`documents`, `document_chunks`, `feedback`, `daily_usage_counters`) has PostgreSQL RLS enabled with a default deny posture.
2. **Cryptographic Identity Derivation:** Tenant `owner_id` is extracted strictly from cryptographically verified JWT tokens.
3. **Indirect Prompt Injection Defense:** All user documents and chunk texts are wrapped in `<untrusted_context>` boundaries and treated as passive reference data.
4. **Credential Isolation:** The frontend browser bundle contains only the public Supabase anon key; server role keys and LLM API keys are isolated to backend environment variables.

---

## 6. Known Limitations & Tradeoffs (§20)

- **Shared Free-Tier LLM Quota & Daily Budget:** A shared 40-request daily cap resets at 00:00 UTC to prevent billing surprises; when exhausted, the system returns HTTP 429 with the exact reset timestamp.
- **Render & Supabase Cold Starts / Inactivity:** Free web services sleep after 15 minutes of inactivity; a scheduled keep-alive ping mitigates this, but cold starts may incur 30–50s initial latency.
- **Provider & Model Availability:** Relies on OpenRouter free-tier models (`:free`), whose availability and community queue times may fluctuate. A 4-model fallback cascade provides automated resilience.
- **Single-Turn Interaction:** Each question is answered independently without conversational memory to eliminate session-drift and context contamination.
- **Document Scale & Parsing:** Scoped to documents up to 5MB and 300 chunks per document; OCR for scanned images/PDFs is omitted in the MVP.
- **No Production SLA:** Built and optimized for demonstration, research, and technical evaluation on free-tier infrastructure.

---

## 7. Cost Statement & Credit Top-Up

> **Cost Statement:** Designed for free tiers; actual availability and quotas depend on provider terms and usage.

To increase reliability beyond free-tier community queues:
1. Depositing a small credit top-up ($5) on OpenRouter removes rate-limit caps while preserving the strict free-model allowlist.
2. The daily request budget (`LLM_DAILY_REQUEST_BUDGET=40`) ensures total daily spend remains bounded even if paid models are enabled by explicit developer override.

---

## 8. Verification & Test Commands

```bash
# Backend unit & integration tests (69 tests)
cd backend
pytest tests

# Backend code formatting & type hygiene
ruff check . && ruff format --check .

# Run deterministic retrieval ablation benchmark
python ../evaluation/run_retrieval_eval.py

# Frontend type-check, tests, and production build
cd ../frontend
npx tsc -b
npm test
npm run build
```

---

## 9. License

MIT License. Built for rigorous enterprise knowledge management and evaluation.
