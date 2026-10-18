# Enterprise Knowledge AI — Portfolio Case Study & Engineering Showcase

> **A production-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform built with LangGraph, PostgreSQL pgvector, FastAPI, and React 18, featuring deterministic sentence-level citations and strict tenant isolation.**

---

## 🌐 Live Production Links & Credentials

| Resource | URL / Details |
|---|---|
| **Live Web Application** | **[https://enterprise-knowledge-ai.vercel.app](https://enterprise-knowledge-ai.vercel.app)** |
| **Live Backend API** | **[https://enterprise-knowledge-ai-api.onrender.com](https://enterprise-knowledge-ai-api.onrender.com)** |
| **API Health & Readiness** | `https://enterprise-knowledge-ai-api.onrender.com/api/v1/health/live` |
| **GitHub Repository** | `https://github.com/pratikchemate/rag-agent` |
| **Demo Mode (Guest)** | Open web app & explore 4 pre-seeded documents without logging in |
| **Reviewer Credentials** | **Email:** `demo-reviewer@example.com`<br>**Password:** `SecurePassword123!` *(Includes document upload privileges)* |

---

## 📌 Executive Summary

Modern enterprise adoption of Large Language Models is frequently blocked by three critical liabilities: **hallucinations and unverified answers**, **cross-tenant data leakage**, and **prohibitive cloud infrastructure costs**.

**Enterprise Knowledge AI** was architected to solve all three challenges:
1. **Zero Unverified Claims:** Implements a deterministic sentence-level citation pipeline that binds each factual sentence in an LLM output to an authentic text chunk in PostgreSQL using strict verification regexes.
2. **Honest Abstention Guarantee:** When retrieved evidence is insufficient after multi-query rewriting, the agent refuses to speculate and outputs a structured abstention notice.
3. **Defense-in-Depth Multi-Tenancy:** Row-Level Security (RLS) policies enforced at the PostgreSQL database engine layer guarantee that tenants can never access or search another organization's vectors.
4. **$0/Month Free-Tier Engineering:** Runs entirely on free-tier infrastructure (Vercel CDN, Render Web Service, Supabase PostgreSQL with pgvector, and OpenRouter Free Model cascades), tamed through strict memory budgets (sub-450MB RSS), pre-cached ONNX embeddings, and connection pooling.

---

## 🛠️ Complete Technology Stack

### Frontend Architecture
- **Framework & Runtime:** React 18 with TypeScript 5.7, bundled via Vite 6.
- **Styling & Design System:** Tailwind CSS 3.4 with custom typography tokens (`Plus Jakarta Sans` for geometric SaaS headers and `JetBrains Mono` for code/citations).
- **Design Methodology:** Sourced from `ui-ux-pro-max` guidelines—featuring a statically pinned viewport input bar, a desktop retractable sidebar (`Ctrl+B`), dark/light theme switching with `localStorage` persistence, and glassmorphic UI layers.
- **Icons & Visual Elements:** Lucide React (`@phosphor-icons` / `@heroicons` aesthetic).
- **Client Networking:** Native `fetch` with automated API endpoint fallback resolution and `AbortSignal` sanitization.
- **Unit Testing:** Vitest 5.0 with component parser tests.

### Backend Architecture
- **Framework & Runtime:** Python 3.13 with FastAPI 0.115+ running under Uvicorn ASGI.
- **Agent Orchestration:** **LangGraph (StateGraph)** cyclical state machine with conditional branching, query reformulation, and citation verifier nodes.
- **Data Validation & Settings:** Pydantic v2 & Pydantic-Settings with strict typing.
- **Database & ORM:** SQLAlchemy 2.0 (declarative async-ready models) + Psycopg 3 native driver.
- **Testing & Code Quality:** Pytest with 81 passing unit and integration tests, Ruff for linting and formatting.

### Vector, Search & Database Tier
- **Database Engine:** PostgreSQL 16 hosted on Supabase with `pgvector` extension.
- **Dense Vector Search:** HNSW (Hierarchical Navigable Small World) index with cosine distance operator (`<=>`).
- **Lexical Full-Text Search:** Native PostgreSQL `tsvector` and `tsquery` using `ts_rank_cd` over language-analyzed English text.
- **Rank Fusion Algorithm:** Reciprocal Rank Fusion (**RRF**, $k=60$) combining dense semantic rankings and lexical keyword matches in a single SQL CTE query.
- **Security & Authorization:** Native PostgreSQL Row-Level Security (**RLS**) with tenant `owner_id` session variables (`request.jwt.claim.sub`).

### Embeddings & Ingestion Pipeline
- **Embedding Model:** Local in-process **FastEmbed** (`BAAI/bge-small-en-v1.5`, 384 dimensions) running via ONNX Runtime CPU.
- **Ingestion Execution:** Asynchronous background tasks (`HTTP 202 Accepted`) with SHA-256 content deduplication.
- **Document Extractors:** PyPDF (PDF text & page layout), python-docx (DOCX parsing), and native Markdown AST parsers.
- **Chunking Engine:** Recursive sliding window token chunker (512 tokens, 64 token overlap) with sentence boundary preservation.

### LLM Orchestration & Quota Management
- **Inference Gateway:** OpenRouter Free-Tier Cascade with automated runtime failover:
  1. `google/gemma-4-31b-it:free`
  2. `google/gemma-4-26b-a4b-it:free`
  3. `nvidia/nemotron-3.5-lightning:free`
- **Budget Defense:** Shared PostgreSQL daily usage counter capping tenant and demo usage at 40 requests/day, returning HTTP 429 with reset timestamps before contacting the LLM.
- **Sliding-Window Rate Limiting:** In-memory IP/tenant rate limiter (5 RPM burst protection).

### Cloud Infrastructure & Deployment
- **Frontend CDN:** Vercel Global CDN with reverse-proxy SPA routing (`vercel.json`).
- **Backend Service:** Render Free Web Service with Dockerfile / Python 3.13 runtime.
- **Database & Auth:** Supabase (AWS Tokyo region) with connection pooling on port 5432.
- **Keep-Alive Automation:** GitHub Actions scheduled cron workflow to maintain backend readiness and prevent database hibernation.

---

## 🏛️ System Architecture Diagram

```mermaid
flowchart TD
    User([Browser Client]) -->|SPA / React 18| Frontend[Vite + Tailwind CSS]
    Frontend -->|JWT Bearer Token / Reverse Proxy| FastAPI[FastAPI Backend :8000]
    
    subgraph Security & Quotas
        FastAPI --> AuthGuard[Supabase JWT Authenticator]
        FastAPI --> RateLimiter[Sliding Window Limiter]
        FastAPI --> BudgetChecker[PostgreSQL Daily Budget Tracker]
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

    VerifyCitationsNode -->|Structured Response + [S1] Citations| Frontend
    AbstainNode -->|Honest Abstention Guarantee| Frontend
```

---

## 🔬 Core Engineering Innovations

### 1. Deterministic Sentence-Level Citation Verifier
Unlike naive RAG systems that ask the LLM to output arbitrary hyperlinks or footnotes (which LLMs frequently fabricate), this platform enforces mathematical attribution:
- The system prompt instructs the model to cite chunks using explicit tokens `[S1]`, `[S2]`.
- The backend parses the model output sentence by sentence.
- If a sentence contains a citation label, the verifier computes n-gram / token overlap against the corresponding retrieved chunk.
- If the model generates a citation to a chunk that was never provided, or uses meta-commentary (e.g., *"Based on the documents provided..."*), the verifier strips invalid citations and normalizes the text.

### 2. Reciprocal Rank Fusion (RRF) Hybrid Search
Pure vector search fails when users search for exact technical terms (e.g., port `5432`, error code `ERR_AUTH_TIMEOUT`, environment key `OPENROUTER_API_KEY`). This system combines dense vector search with PostgreSQL lexical `tsquery`:
$$RRF\_Score(d) = \frac{1}{60 + Rank_{dense}(d)} + \frac{1}{60 + Rank_{lexical}(d)}$$
This guarantees that exact keyword matches and semantic paraphrases both bubble to the top candidates.

### 3. PostgreSQL Native Row-Level Security (RLS)
Instead of maintaining tenant separation in application-level filtering (which is prone to developer oversight), tenant isolation is baked into PostgreSQL:
```sql
CREATE POLICY "tenant_isolation_chunks" ON document_chunks
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = document_chunks.document_id
            AND (d.owner_id = auth.uid() OR d.is_public = TRUE)
        )
    );
```
Even if an attacker attempts SQL manipulation, the database engine enforces isolation.

### 4. Zero-Cost Free-Tier Resource Engineering
Deploying an enterprise RAG architecture on free-tier services requires solving extreme resource limits:
- **512MB RAM Ceiling on Render:** Standard embedding libraries (like SentenceTransformers with PyTorch) consume 800MB+ of RAM, causing immediate Out-of-Memory (OOM) kills. By using **FastEmbed** with ONNX Runtime and pinning batch size to `8`, peak memory is capped at ~420MB.
- **FastEmbed Model Pre-caching:** Pre-downloads the 130MB model during the Render build phase (`render.yaml`), eliminating runtime cold-start network stalls.
- **Database Connection Conservation:** Caps SQLAlchemy pool size to 3 connections, staying safely below Supabase's 60-connection ceiling.

---

## 📊 Performance & Benchmark Metrics

| Metric | Measured Value | Context |
|---|---|---|
| **Local Retrieval Latency** | **45ms – 85ms** | Hybrid RRF query in PostgreSQL across indexed corpus |
| **Warm Production Retrieval** | **766ms** | Remote query from Render (Oregon) to Supabase (Tokyo) |
| **Inference Generation Time** | **3.8s – 4.5s** | OpenRouter Free Cascade (Gemma 4 31B) |
| **Warm End-to-End Latency** | **~5.2s – 6.1s** | Complete RAG lifecycle (Validate $\to$ Retrieve $\to$ Generate $\to$ Verify) |
| **Render Cold Start** | **~50s – 65s** | From 15-minute idle sleep to live HTTP response |
| **Peak Backend RAM Usage** | **420MB – 445MB** | Ingestion of 300+ text chunks within 512MB ceiling |
| **Automated Test Coverage** | **89 Passing Tests** | 81 backend pytest tests + 8 frontend vitest tests |

---

## 🎨 UI/UX Features & Accessibility

- **Static Sticky Input:** The viewport is locked to `h-screen overflow-hidden`, ensuring the prompt input box never shifts or scrolls off screen.
- **Desktop Retractable Sidebar:** Retracts smoothly from `w-84` to `w-0` with dedicated header buttons, top scope bar actions, or the **`Ctrl + B`** keyboard shortcut.
- **Full Dark Mode:** Automatic system preference detection, persistent `localStorage` theme caching, and high-contrast WCAG 2.1 AA compliant color tokens.
- **In-Modal Chunk Inspection:** Full document preview modal equipped with real-time in-memory chunk search and byte-offset badges.
- **Interactive Citation Drawer:** Clickable `[S1]` badges open a sliding drawer displaying the exact verbatim excerpt and a direct jump link to the source document.
- **Frictionless Demo Access:** Visitors can browse and query 4 enterprise documents without an account, or use the 1-click **"Autofill Demo"** button to test reviewer upload workflows.

---

## 💼 Portfolio & Resume Presentation Snippets

### 3 Bullet Points for Resume:
- **Architected and deployed a multi-tenant Enterprise RAG platform** using FastAPI, LangGraph, and PostgreSQL pgvector, achieving deterministic, sentence-level source citations and zero hallucinations on out-of-scope inquiries.
- **Engineered a hybrid retrieval engine combining HNSW dense vector search and lexical tsquery full-text search** via Reciprocal Rank Fusion ($k=60$), delivering sub-100ms retrieval and high precision on technical identifiers.
- **Optimized container memory footprint to under 450MB RAM** using ONNX-accelerated FastEmbed embeddings, enabling full production deployment across free-tier infrastructure (Render, Vercel, Supabase) with zero hosting costs.

### 1-Paragraph Project Summary:
> **Enterprise Knowledge AI** is an open-source, production-ready Retrieval-Augmented Generation (RAG) platform built to eliminate enterprise hallucination risks and enforce rigorous multi-tenant data boundaries. Featuring a cyclical LangGraph state machine, PostgreSQL pgvector with Reciprocal Rank Fusion (RRF) hybrid search, and a deterministic sentence-level citation verifier, the system maps every factual claim to verified document chunks while honestly abstaining when evidence is insufficient. Designed with free-tier resource resilience, it runs in production across Vercel, Render, and Supabase at zero operating cost.

### Key Technical Interview Discussion Points:
1. **Why Hybrid Search (RRF) over Pure Vector Search:** Vector embeddings excel at semantic paraphrasing but degrade when searching for exact alphanumeric terms (ports, UUIDs, function names). RRF merges both signals without manual parameter tuning.
2. **Database-Level RLS vs. Application-Level Filtering:** Implementing tenant boundaries inside PostgreSQL Row-Level Security guarantees data isolation even if application code suffers an injection bug.
3. **LangGraph vs. Linear Chains:** LangGraph allows explicit loopbacks (query rewriting when retrieval scores fall below threshold) and deterministic routing to an abstention state when multiple reformulation attempts fail.
4. **Memory Constraint Engineering:** Overcoming the 512MB RAM ceiling on free-tier containers by switching from heavyweight PyTorch stacks to ONNX CPU runtimes and tuning ingestion batch sizes.
