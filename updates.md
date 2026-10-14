# Code Review Findings and Implementation Status

**Date:** 2026-10-14  
**Scope:** Full repository review against AGENTS.md specification  
**Method:** Graphify knowledge graph analysis (866 nodes, built 2026-10-14 06:29) + direct source review by three Opus reviewers (data/security, retrieval/LLM, tests/eval/frontend/docs) + local validation checks

**Local Validation Results:**
- **Backend lint:** `ruff check .` — All checks passed
- **Backend format:** `ruff format --check .` — 41 files already formatted
- **Backend tests:** `pytest -q` — 39 passed in 2.75s (against a locally reachable Postgres; several of these tests need a database and the real embedding model, see P2)
- **Frontend lint:** `npm run lint` — Passed with no errors
- **Frontend build:** `npm run build` — Built successfully in 4.61s (429.49 kB bundle)

**Verdict:**

The implementation contains most of the required structure: RLS migrations, the partial unique index for deduplication, JWKS-based JWT verification, the `:free` model guard, 202 async ingestion, OR-based tsquery for hybrid search, reciprocal rank fusion, the corrected LangGraph workflow with proper abstain routing, sentence-level citation verification, frontend quota/disclaimer/single-turn UX, and pgvector CI container. However, there is **one critical security vulnerability** (auth bypass with default development environment), the core "abstain on weak evidence" behavior is effectively unreachable due to a flat OR-threshold bug, part of the evaluation framework fabricates results instead of measuring them, and several spec requirements are missing or incorrectly implemented. The codebase is functional for demonstration but requires P0 fixes before any deployment and P1 fixes to match the specification fully.

---

## P0: Critical (fix before any deploy)

### 1. Auth bypass via test-token acceptance in default configuration

**Problem:** The backend accepts unsigned `test-token-<uuid>` tokens with no signature verification when `ENVIRONMENT` is `development` or `test` (`backend/app/core/auth.py:46-62`), and `ENVIRONMENT` defaults to `"development"` (`backend/app/core/config.py:20`). A production deployment that forgets to set the `ENVIRONMENT` variable allows anyone to impersonate any user by submitting a trivial bearer token.

**Evidence:**
- `backend/app/core/auth.py:46-62` — test-token bypass gate
- `backend/app/core/config.py:20` — `ENVIRONMENT: str = "development"`

**Fix:**
1. Change the default environment to `production` in `config.py:20`
2. Only allow test tokens when `ENVIRONMENT == "test"` AND an explicit opt-in flag `ALLOW_TEST_TOKENS=true` is set
3. Add startup validation that refuses to start if `ALLOW_TEST_TOKENS=true` when `ENVIRONMENT != "test"`

**Verify:**
- Attempt to authenticate with `Authorization: Bearer test-token-<uuid>` in a default configuration (no `.env` overrides); confirm it returns 401
- Set `ENVIRONMENT=test` and `ALLOW_TEST_TOKENS=true`; confirm test tokens are accepted
- Set `ENVIRONMENT=production` and `ALLOW_TEST_TOKENS=true`; confirm the app refuses to start with a clear error message

---

### 2. JWT hardening: missing issuer check and incorrect HS256 fallback secret

**Problem:** The JWT verification does not check the `iss` (issuer) claim (`auth.py:69-75`), allowing tokens issued by other Supabase projects or unrelated providers to be accepted as long as the signature validates. The HS256 fallback path (`auth.py:79-88`) uses `SUPABASE_SECRET_KEY` (the service-role key) as the JWT secret, which is the wrong key — Supabase's legacy JWT secret is a separate value.

**Evidence:**
- `backend/app/core/auth.py:69-75` — JWKS verification with no issuer check
- `backend/app/core/auth.py:79-88` — HS256 fallback using service-role key

**Fix:**
1. Add `issuer=f"{settings.SUPABASE_URL}/auth/v1"` to the `jwt.decode` call in the JWKS path
2. Require `exp`, `sub`, and `aud` claims explicitly
3. Make HS256 an explicit opt-in that uses a separate `SUPABASE_JWT_SECRET` environment variable (not the service-role key), and only enable it if the variable is set and `ENVIRONMENT != "production"`

**Verify:**
- Create a JWT signed by a different Supabase project's key with a valid signature; confirm it is rejected
- Create an expired JWT; confirm it is rejected
- Create a JWT with wrong audience; confirm it is rejected
- Set `SUPABASE_JWT_SECRET` to a test value and confirm HS256 tokens signed with that secret are accepted only in non-production environments

---

### 3. Fabricated Ragas evaluation report

**Problem:** `evaluation/run_ragas_eval.py:54-78` writes hardcoded Ragas metric scores (faithfulness: 0.95, answer relevance: 0.92, context precision: 0.94, context recall: 0.96) marked as "PASS" and claims the evaluation was "executed sequentially" with throttling, but the script never imports Ragas, never calls any Ragas metric function, and never runs the LLM-based evaluation. The report is entirely fictional.

**Evidence:**
- `evaluation/run_ragas_eval.py:54-78` — frozen hardcoded report content
- `evaluation/run_ragas_eval.py:1-50` — no Ragas imports, no metric computation

**Fix:**
Either:
1. Actually call Ragas on a subset of ≤10 cases as specified in AGENTS.md §15, or
2. Delete `run_ragas_eval.py` and the generated report, and document in the README that Ragas evaluation has not been run and is left as future work

**Verify:**
- If Ragas is implemented: run the script and confirm it makes real LLM calls and writes measured (not hardcoded) scores
- If deleted: confirm the file no longer exists and the README does not claim Ragas results

---

### 4. Abstention is effectively unreachable due to flat OR-threshold

**Problem:** Evidence is marked as sufficient if `top_similarity >= 0.25 OR any keyword hit` (`retrieval.py:228-232`, with threshold at `config.py:62`). The `assess_evidence_node` in the LangGraph workflow adds no additional logic (`backend/app/graph/nodes.py:117-121`). The project's own benchmark (`evaluation/retrieval_benchmark.json`) shows abstention accuracy of 0.7429 (26/35) across all modes, meaning **0 of the 9 should-abstain cases actually abstained**. The OR condition makes abstention practically impossible: any keyword match bypasses the similarity check entirely.

**Evidence:**
- `backend/app/services/retrieval.py:228-232` — `if top_similarity >= self.min_similarity or any(c.keyword_rank is not None for c in top_candidates): evidence_sufficient = True`
- `backend/app/core/config.py:62` — `MIN_RETRIEVAL_SIMILARITY: float = 0.25`
- `backend/app/graph/nodes.py:117-121` — `assess_evidence_node` does nothing beyond reading the pre-computed flag
- `evaluation/retrieval_benchmark.json` — measured abstention accuracy 0.7429 in every mode (0 true abstentions)

**Fix:**
1. Move the evidence sufficiency decision into the `assess_evidence_node` in the LangGraph workflow
2. Combine at least three signals with AND/weighted logic (not OR): top similarity, presence of keyword hits, and the score gap between the top chunk and the 20th candidate chunk
3. Run an evaluation sweep over the dataset (including the should-abstain cases) to derive an empirically justified threshold
4. Document the chosen threshold and the evaluation run that produced it in `docs/architecture.md`

**Verify:**
- Run the evaluation suite against the updated evidence logic
- Confirm that at least 7 of the 9 should-abstain cases now abstain (target: abstention recall ≥ 0.75)
- Confirm that answerable cases still produce answers (target: false-abstention rate ≤ 0.15)
- Verify the threshold value and derivation are documented in `docs/architecture.md`

---

### 5. Misleading and contradictory evaluation narrative

**Problem:** The retrieval evaluation report text is hardcoded and contradicts the measured numbers:
- The narrative says the system "cleanly identified" out-of-corpus queries, but abstention accuracy is 0.7429 (meaning 0 of 9 should-abstain cases abstained)
- The narrative claims "sub-10ms p50 latency" but the measured p50 is 17.27 ms (`evaluation/run_retrieval_eval.py:234-241`)
- The README.md table at lines 109-114 shows different numbers than `evaluation/retrieval_benchmark.json`

**Evidence:**
- `evaluation/run_retrieval_eval.py:234-241` — hardcoded narrative contradicting measurements
- `README.md:109-114` — table doesn't match `retrieval_benchmark.json`
- `evaluation/retrieval_benchmark.json` — actual measured values

**Fix:**
1. Generate the evaluation narrative programmatically from the measured JSON data
2. Regenerate the README table from `retrieval_benchmark.json` to ensure consistency
3. Remove any claim not supported by the actual measurements

**Verify:**
- Run the evaluation script and confirm the generated narrative accurately reflects the JSON numbers
- Confirm the README table matches the current `retrieval_benchmark.json` output
- Grep for hardcoded metric claims and verify they are now data-driven

---

## P1: Spec items wrong or missing

### LLM layer issues

**Problem:**
1. The fallback catches every `Exception` (`model_factory.py:81`), so a programming error (AttributeError, KeyError) is treated the same as a provider rate limit — it should only fall through on 404/429/503 and should map provider-specific errors (rate limit, timeout, auth failure, model unavailable) to distinct error codes
2. `finish_reason == "length"` is logged as a warning but still returns the truncated response as success (`:74-80`), so the truncated answer with unverifiable trailing citations is delivered to the user
3. `OPENROUTER_REASONING_EFFORT` is defined in config but is never passed to the model
4. There is a hardcoded default model slug at line 36

**Evidence:**
- `backend/app/services/model_factory.py:81` — broad `except Exception`
- `backend/app/services/model_factory.py:74-80` — logs warning but returns response
- `backend/app/services/model_factory.py:36` — hardcoded default
- `backend/app/core/config.py` — `OPENROUTER_REASONING_EFFORT` defined but unused

**Fix:**
1. Replace the broad `except Exception` with specific provider exception types; only fall through on retriable conditions
2. When `finish_reason == "length"`, raise a distinct error (e.g. `ResponseTruncatedError`) instead of returning the incomplete response
3. Pass `reasoning_effort=settings.OPENROUTER_REASONING_EFFORT` to the `ChatOpenRouter` constructor
4. Remove or make the hardcoded default conditional on explicit fallback configuration

**Verify:**
- Trigger a model 429 response (mock or real); confirm it falls through to the next model
- Trigger a programming error (e.g. bad config); confirm it does not fall through but raises immediately
- Mock a truncated response; confirm the API returns an error, not a partial answer
- Confirm `OPENROUTER_REASONING_EFFORT` appears in the ChatOpenRouter constructor call

---

### Daily budget and quota issues

**Problem:**
1. The daily LLM budget counter uses a read-then-increment pattern (`rate_limit.py:64-77`) which is racy under concurrent requests — two requests can both read the same count and both increment, undercounting usage
2. The budget reserves 1 call instead of up to 2 (query rewrite + generate)
3. The budget is charged before document-ID validation and on abstention paths that never call the LLM (`chat.py:44-53`)

**Evidence:**
- `backend/app/core/rate_limit.py:64-77` — read, check, then update in separate statements
- `backend/app/api/chat.py:44-53` — single `reserve_llm_budget(1)` call before document validation

**Fix:**
1. Replace the read-increment logic with a single atomic `UPDATE ... SET used = used + :cost WHERE used + :cost <= :budget RETURNING used` and check if any row was returned
2. Charge the budget per actual LLM call: reserve nothing up front, increment by 1 after query rewrite (if run) and again after generate
3. Move budget charging to the LangGraph nodes that actually invoke the model

**Verify:**
- Run 10 concurrent chat requests and confirm the final counter accurately reflects 10-20 calls (depending on rewrite)
- Submit a request with an invalid document ID; confirm the budget is not charged
- Trigger an abstention (weak evidence, no rewrite); confirm the budget is not charged
- Exhaust the budget during a rewrite call; confirm the 429 response is returned and generate is not called

---

### Upload and document ingestion issues

**Problem:** (`backend/app/api/documents.py:51-114`, `document_parser.py:38-75`)
1. File size is checked only after a full `read()`, so a 50MB file is fully loaded into memory before rejection
2. Extension and MIME type are validated only inside the background task, so clients never receive a 415 (Unsupported Media Type) — they get 202 and then have to poll to discover the failure
3. `SUPPORTED_MIME_TYPES` is defined in config but never used, and there is no magic-byte check (file signature validation)
4. The file is uploaded to storage before the database row is inserted — if two users upload the same file concurrently, both succeed at storage, then both try to insert, one gets an IntegrityError (500), and an orphaned file is left in storage
5. The ingestion functions are `async def` but make blocking calls to the database and `httpx` without await

**Evidence:**
- `backend/app/api/documents.py:51-114` — upload endpoint
- `backend/app/services/document_parser.py:38-75` — parsing logic

**Fix:**
1. Stream the upload and enforce size limits during streaming, or at minimum check `Content-Length` header before reading the body
2. Move extension and MIME type validation to the synchronous request handler before returning 202, and return 415 immediately for unsupported types
3. Add magic-byte validation using `python-magic` or equivalent, and actually check against `SUPPORTED_MIME_TYPES`
4. Insert the database row first, then upload to storage, so the unique constraint prevents duplicates before storage side effects
5. Either make the blocking calls properly async (use async DB driver methods, async httpx calls) or change the function to `def` (not `async def`) so the blocking behavior is explicit

**Verify:**
- Upload a 10MB file (over the 5MB limit); confirm it is rejected before full read (check logs for memory usage or stream position)
- Upload a .exe file; confirm it returns 415 immediately, not 202 followed by failed status
- Upload two identical files concurrently; confirm one succeeds, one returns 409, and only one storage object exists
- Review DB calls in the background task; confirm they use async methods (or the function is marked `def`)

---

### Storage fallback issues

**Problem:** (`backend/app/services/storage.py:51-96`)
1. The service silently falls back to local disk on any Supabase Storage error, even in production
2. The fallback writes `.storage_cache` inside the repository root (both `/home/pratik/personal/rag-agent/.storage_cache` and `backend/.storage_cache` exist in the working tree)
3. `delete_file` always returns `True` even when the delete fails

**Evidence:**
- `backend/app/services/storage.py:51-96` — storage service with fallback
- Git working tree shows `.storage_cache` directories present despite being gitignored

**Fix:**
1. Disable the local-disk fallback when `ENVIRONMENT == "production"`
2. Move the fallback path outside the repository (e.g. `/tmp/.storage_cache`)
3. Make `delete_file` return `False` or raise an exception on failure, and propagate delete errors to the caller so orphaned files are visible

**Verify:**
- Set `ENVIRONMENT=production` and trigger a Supabase Storage error; confirm the request fails instead of falling back
- Trigger a delete failure (mock or disconnect storage); confirm the API returns an error and logs the orphaned file path
- Confirm `.storage_cache` no longer appears inside the repository

---

### Database engine and connection pooling

**Problem:** (`backend/app/db/engine.py:13-19`)
1. `pool_size=3` + `max_overflow=2` allows 5 connections, which may be too many for Supabase Free or may be too few for concurrent requests — the choice is not documented
2. There is no `prepare_threshold=None` setting (required for Supabase transaction pooler if it's used, though the config correctly uses the session pooler)
3. There is no comment explaining that the **session pooler** (not transaction pooler, not direct host) must be used per AGENTS.md §19
4. Chunks and document status are written in two separate commits (`ingestion.py:71-77`), so a crash can leave status=processing with chunks already persisted

**Evidence:**
- `backend/app/db/engine.py:13-19` — engine configuration
- `backend/app/services/ingestion.py:71-77` — separate commits for chunks and status

**Fix:**
1. Document the connection pool sizing rationale in a comment
2. Add `prepare_threshold=None` as a safeguard (it's harmless with the session pooler, but essential if the connection string is accidentally changed to the transaction pooler)
3. Add a comment near the `DATABASE_URL` config and in `engine.py` noting the requirement to use Supabase's **session pooler** connection string
4. Wrap chunk insertion and status update in a single transaction, or use a try/finally to ensure status is updated even on partial failure

**Verify:**
- Review the connection pool settings and confirm the rationale is documented
- Confirm `prepare_threshold=None` is present
- Grep for "session pooler" or equivalent note
- Trigger a failure during chunk insertion; confirm the document status is updated to `failed`

---

### Retrieval and query construction issues

**Problem:**
1. `document_id = ANY(:selected_doc_ids)` receives `list[str]` and may fail with a type error (uuid[] vs text[]) depending on the driver's parameter handling (`retrieval.py:77-78`)
2. The tsquery uses `'english'` stemming and doesn't quote lexemes (`:122,129`), so searches for "APIs" might not match "API" and multi-word terms aren't quoted
3. The query construction does not cast the list or ensure the parameter type is explicitly uuid[]

**Evidence:**
- `backend/app/services/retrieval.py:77-78` — `ANY(:selected_doc_ids)`
- `backend/app/services/retrieval.py:122,129` — tsquery construction

**Fix:**
1. Cast `selected_doc_ids` to `list[UUID]` before passing to the query, or cast the SQL parameter: `document_id = ANY(:selected_doc_ids::uuid[])`
2. Use `'simple'` configuration instead of `'english'` for tsquery to avoid unexpected stemming, and quote lexemes to preserve exact terms
3. Add a test with a multi-word query and document IDs as strings to catch the regression

**Verify:**
- Submit a query with `document_ids=["<uuid-string>"]` and confirm it does not raise a type error
- Search for "APIs" and confirm it matches a chunk containing "API" (or vice versa, depending on desired behavior)
- Confirm the test suite includes a case with selected document IDs

---

### Configuration validation and secrets

**Problem:** (`backend/app/core/config.py`)
1. There is no numeric range validation (e.g. `CHUNK_SIZE > 0`, `RETRIEVAL_TOP_K >= 1`)
2. There is no enum validation (e.g. `ENVIRONMENT in {"development", "test", "production"}`)
3. Secrets are not marked as `SecretStr`, so they may appear in error messages or logs

**Evidence:**
- `backend/app/core/config.py` — settings class with no validators

**Fix:**
1. Add Pydantic `@field_validator` or `@model_validator` decorators to enforce numeric ranges and enum membership
2. Mark `OPENROUTER_API_KEY`, `SUPABASE_SECRET_KEY`, and any other secrets as `SecretStr`
3. Add startup tests that attempt to load invalid configs and confirm they are rejected with clear error messages

**Verify:**
- Set `CHUNK_SIZE=-100` and confirm the app refuses to start
- Set `ENVIRONMENT=staging` and confirm it is rejected
- Trigger a config error and confirm no secret values appear in the error message

---

### Request ID handling

**Problem:**
1. The chat endpoint overwrites `request_id_ctx` with a new UUID, so the header-provided request ID and the body-echoed request ID differ (`chat.py:37-38`)
2. The client-supplied `X-Request-ID` header is trusted without validation — a malicious client could inject a newline or very long string (`main.py:52`)
3. The 422 validation error response echoes the submitted input, which could leak sensitive data in logs or error tracking

**Evidence:**
- `backend/app/api/chat.py:37-38` — `request_id_ctx.set(str(uuid4()))`
- `backend/app/main.py:52` — reads header without validation
- `backend/app/main.py:87` — 422 handler echoes request body

**Fix:**
1. Only generate a new request ID if the client did not provide one; otherwise use the validated client ID
2. Validate the client request ID: must be a valid UUID or a short alphanumeric string, reject if invalid
3. Do not echo the full request body in 422 responses; return only the validation error structure

**Verify:**
- Send a request with `X-Request-ID: test-123`; confirm the response `request_id` matches `test-123`
- Send a request with `X-Request-ID: <1000-character string>`; confirm it is rejected or truncated
- Trigger a 422 error with a request containing a password field; confirm the password does not appear in the response

---

### LangChain usage is minimal

**Problem:** The Definition of Done (AGENTS.md §21) requires that "LangChain is used substantively for document handling, splitting, embeddings, prompts, and the chat model integration." The implementation uses `ChatOpenRouter` and `RecursiveCharacterTextSplitter`, but there is no usage of `Document`, `FastEmbedEmbeddings`, or `ChatPromptTemplate` in `backend/app/`.

**Evidence:**
- `grep -r "from langchain" backend/app/` shows only `ChatOpenRouter` and `RecursiveCharacterTextSplitter`
- No `from langchain.schema import Document` or `from langchain.embeddings import FastEmbedEmbeddings`

**Fix:**
1. Use `langchain.schema.Document` (or `langchain_core.documents.Document`) as the internal representation for chunks, rather than plain dictionaries
2. Wrap the FastEmbed model in `FastEmbedEmbeddings` from `langchain_community.embeddings`
3. Use `ChatPromptTemplate` to construct the generation prompt instead of string formatting

**Verify:**
- Grep for `from langchain` imports and confirm `Document`, `FastEmbedEmbeddings`, and `ChatPromptTemplate` are present
- Confirm the chunking service returns `Document` objects with `.page_content` and `.metadata`
- Confirm the generation service uses `ChatPromptTemplate.from_messages(...)`

---

### Smaller spec gaps

**Problem:**
1. `CREATE EXTENSION vector` is not schema-qualified (should be `CREATE EXTENSION IF NOT EXISTS vector SCHEMA extensions` or the appropriate schema)
2. There is no `updated_at` trigger on the `documents` table
3. `get_by_id` in repositories defaults to `allow_public=True`, so the caller must remember to pass `False` for ownership-only checks (insecure default)
4. The `EXEMPT_REGEX` pattern for citation-exemption sentences is very broad and matches real factual claims like "X feature is not available in the free tier"
5. An invalid/empty question returns 200 + abstained instead of 400
6. There is no LLM-rewrite fallback when the LLM call fails
7. The generation prompt lacks the "distinguish fact vs inference" instruction from AGENTS.md §11

**Evidence:**
- `supabase/migrations/` — extension creation SQL
- `supabase/migrations/` — no updated_at trigger
- `backend/app/db/repositories.py` — `get_by_id` method signature
- `backend/app/services/citation_verifier.py` — `EXEMPT_REGEX`
- `backend/app/graph/nodes.py` — validate_question node
- `backend/app/graph/nodes.py` — no rewrite fallback on error
- `backend/app/services/generation.py` — system prompt

**Fix:**
1. Schema-qualify the vector extension creation
2. Add an `updated_at` trigger that updates the timestamp on every UPDATE
3. Change `get_by_id` default to `allow_public=False` (secure by default)
4. Tighten the `EXEMPT_REGEX` to only match explicit abstention phrases like "I could not find", "The documents do not contain", etc.
5. Return 400 from the validate_question node when the question is empty or invalid
6. Add a deterministic fallback (e.g. return the original query) when LLM-based query rewrite fails
7. Add "Distinguish direct facts from inferences" to the system prompt

**Verify:**
- Confirm `CREATE EXTENSION` uses schema qualification
- Confirm `updated_at` column is auto-updated on document modification
- Call `get_by_id` without `allow_public` on another user's document; confirm it returns None
- Search for "not available" in a chunk and confirm it is not exempted from citation requirements
- Submit an empty question; confirm the response is 400, not 200 + abstained
- Mock an LLM rewrite failure; confirm the graph falls back gracefully
- Grep the system prompt for "fact" or "inference" instruction

---

## P2: Tests, CI, frontend, docs

### Hollow tests

**Problem:**
1. The RRF test is pure arithmetic and does not test the actual `HybridRetrievalService.search` method
2. The OR-tsquery test tests pasted SQL in a docstring, not the real `HybridRetrievalService.search` method
3. The chat-citation test only checks that the response has `"citations"` and `"answer"` keys, not that the citations are valid or correctly mapped

**Evidence:**
- `backend/tests/unit/test_retrieval.py` — RRF test on mock data
- `backend/tests/unit/test_retrieval.py` — tsquery test with inline SQL
- `backend/tests/integration/test_chat.py` — citation test checks keys only

**Fix:**
1. Add a test that calls `HybridRetrievalService.search` with real database rows and verifies the RRF-fused ranking order
2. Add a test that calls `HybridRetrievalService.search` with a multi-word natural-language query and confirms keyword candidates are returned even when not all terms match
3. Extend the citation test to verify that every citation label in the answer maps to a chunk ID that was actually retrieved and owned by the user

**Verify:**
- Run the updated retrieval tests and confirm they call the real service method
- Confirm the tsquery test uses the live query path, not inline SQL
- Confirm the citation test validates label mapping, not just key presence

---

### Missing tests

**Problem:** The following behaviors are not covered by any test:
1. JWT invalid/expired/wrong-aud rejection
2. RLS allowlist fallback (Supabase Data API with anon key returns zero rows)
3. `finish_reason == "length"` detection and error
4. Document deletion removes storage object and all chunks
5. Upload size enforcement before full read
6. No secrets appear in logs
7. Mocked embeddings return 384-dimensional vectors
8. Owner/`is_public` retrieval scope (user A can't search user B's docs, but both can search public docs)
9. A compiled LangGraph test that confirms abstain paths never reach `verify_citations`
10. User B cannot chat over user A's documents
11. Client polls `GET /documents/{id}` until status is `ready`
12. True duplicate upload is blocked by the partial unique index

**Evidence:**
- `backend/tests/` directory — missing coverage

**Fix:**
Add tests for each of the above cases.

**Verify:**
Run the full test suite and confirm all 12 cases are explicitly tested and pass.

---

### CI issues

**Problem:**
1. The GitHub Actions workflow downloads the FastEmbed model from Hugging Face during the test run (an external network call, violating AGENTS.md §4 rule 10)
2. There is no separate frontend type-check step (only `tsc -b` inside `npm run build`)
3. There is no scheduled keep-alive workflow to ping `/api/v1/health/ready` and prevent Supabase inactivity pause
4. CI has never run because the repository has no commits

**Evidence:**
- `.github/workflows/ci.yml` — workflow definition
- Git status shows no commits

**Fix:**
1. Download and cache the FastEmbed model in the CI job's setup step (before tests), or mock the embedding service to avoid the download
2. Add a separate `tsc --noEmit` step in the frontend job
3. Add a `.github/workflows/keep-alive.yml` scheduled workflow (e.g. every 3 days) that curls the health endpoint
4. Create an initial commit so CI can run

**Verify:**
- Run CI and confirm no external network calls occur during tests (check logs for Hugging Face downloads)
- Confirm the frontend job includes a distinct type-check step
- Confirm the keep-alive workflow is present and scheduled
- Confirm CI runs successfully on push

---

### Dataset gaps

**Problem:** The evaluation dataset has 35 cases but is missing:
1. Conflicting-sources cases (where two documents give different answers)
2. Empty-question and invalid-question cases (should return 400, not abstain)

The relevance scoring is based on filename matching over only 4 documents, so recall is near-automatic and does not test retrieval quality.

**Evidence:**
- `evaluation/dataset.json` — 35 cases, no conflicting sources or invalid questions

**Fix:**
1. Add at least 2 conflicting-sources cases
2. Add at least 2 empty/invalid-question cases
3. Expand the fixture corpus to at least 10 documents with more granular ground-truth chunk IDs

**Verify:**
- Confirm the dataset includes conflicting-sources and invalid-question cases
- Run the evaluation and confirm recall is not trivially 1.0

---

### Frontend issues

**Problem:**
1. No `AbortController` to cancel in-flight requests when the component unmounts or a new query is submitted
2. All error kinds (auth, cold start, rate limit, DB unavailable) go to one generic error box
3. Preview contract mismatch: the backend returns `{document: {...}, chunks: [...], total_chunks: N}` but `types/index.ts:21-26` expects top-level `chunks` and `total_chunks`
4. Feedback response uses `feedback_id` but the type expects `id` (`api.ts:132`)
5. `tsconfig.app.json` contains unsupported Vite options
6. Vite template leftovers remain: `App.css`, `hero.png`, `react.svg`, `vite.svg`, `frontend/README.md`
7. No Vitest configuration or tests

**Evidence:**
- `frontend/src/` — no AbortController usage
- `frontend/src/components/` — generic error component
- `frontend/src/types/index.ts:21-26` — preview type
- `frontend/src/lib/api.ts:132` — feedback response mapping
- `frontend/tsconfig.app.json` — config file
- `frontend/public/` and `frontend/src/` — template files
- `frontend/` — no vitest config

**Fix:**
1. Add `AbortController` to chat and document fetch calls
2. Create distinct error states for auth (401), quota exhausted (429 with reset time), cold start/timeout (503), and generic errors
3. Fix the preview type to match the backend contract
4. Unify the feedback ID field (`id` everywhere or `feedback_id` everywhere)
5. Remove unsupported options from `tsconfig.app.json` or delete the file if it's unused
6. Delete Vite template files
7. Add Vitest and at least one smoke test (e.g. component renders without crashing)

**Verify:**
- Submit two queries in quick succession; confirm the first is aborted
- Trigger each error type; confirm distinct UI states
- Call the preview endpoint and confirm the response is correctly typed
- Submit feedback and confirm no type errors
- Confirm `tsconfig.app.json` has no errors or is deleted
- Confirm template files are deleted
- Run `npm test` and confirm Vitest runs

---

### Documentation drift

**Problem:** The README and docs contradict the implementation:
1. Refers to `MODEL_ALLOWLIST` instead of `OPENROUTER_MODELS`
2. Bucket name is `documents` in docs but `source-documents` in code
3. Similarity threshold is documented as 0.35 but code uses 0.25
4. Daily budget is documented as 100 but code uses 40
5. A Dockerfile snippet is shown but there is no Dockerfile or `render.yaml`
6. Missing sections: Supabase setup (project creation, migration application), invite-only configuration, redirect URLs, CORS setup, storage bucket creation, test/lint commands, keep-alive workflow, cost statement, credit top-up explanation, full §20 known limitations

**Evidence:**
- `README.md` — contradictions and missing sections
- `docs/` — incomplete or missing documentation

**Fix:**
1. Global search-replace to reconcile variable/bucket/threshold/budget names
2. Add missing sections per AGENTS.md §20
3. Remove or complete the Dockerfile snippet

**Verify:**
- Grep for `MODEL_ALLOWLIST`, `documents` (bucket), `0.35`, `100` and confirm they are corrected or removed
- Confirm README includes all §20 required sections
- Confirm Dockerfile snippet is removed or a working Dockerfile is present

---

### Hygiene

**Problem:**
1. `*.tsbuildinfo` is not in `.gitignore`
2. Stray `.storage_cache/` directories at root and in `backend/`
3. `GEMINI.md` and `.gemini/` are present — needs decision on whether to keep

**Evidence:**
- `.gitignore` — missing tsbuildinfo
- File system — `.storage_cache` exists
- Root directory — `GEMINI.md` and `.gemini/`

**Fix:**
1. Add `*.tsbuildinfo` to `.gitignore`
2. Delete `.storage_cache` directories (they are already gitignored but shouldn't exist after the storage fallback fix)
3. Decide whether to keep or delete `GEMINI.md` and `.gemini/`

**Verify:**
- Confirm `*.tsbuildinfo` is gitignored
- Confirm no `.storage_cache` directories exist
- Confirm GEMINI.md decision is made

---

## Definition of Done Scorecard

| Requirement | Status | Reason |
|-------------|--------|--------|
| Frontend and backend run locally using documented commands | **Unverified** | Lint, tests and the production build pass, but neither `npm run dev` nor `uvicorn` was started during this review |
| Authenticated users can upload, list, preview, and delete supported documents | **Met** | Endpoints exist and tests pass; 202 async upload implemented per spec |
| PDF page metadata is preserved in chunks and citations | **Met** | `page_number` field populated from PyMuPDF parsing and returned in citations |
| Embeddings are generated locally through FastEmbed (384 dimensions) | **Met** | `BAAI/bge-small-en-v1.5` via FastEmbed with `VECTOR(384)` in the schema; note there is no dedicated 384-dim embeddings test (P2) |
| PostgreSQL stores document chunks and vectors; retrieval uses pgvector and full-text search (OR-joined tsquery) combined by RRF | **Met** | Hybrid retrieval with OR-tsquery (§9.2 fix applied), RRF fusion, pgvector cosine distance all implemented |
| LangChain is used substantively for document handling, splitting, embeddings, prompts, and chat model integration | **Partial** | Uses `RecursiveCharacterTextSplitter` and `ChatOpenRouter`, but does not use `Document` objects, `FastEmbedEmbeddings` wrapper, or `ChatPromptTemplate` (P1 finding) |
| LangGraph is used substantively for typed multi-step workflow orchestration and bounded conditional routing, with corrected flow from §10 | **Met** | `StateGraph` with typed `RAGState`, conditional routing, max 2 retrieval attempts, both abstain paths terminate at END |
| LLM uses configured `OPENROUTER_MODELS` free-model allowlist by default and there is no automatic paid fallback | **Met** | Allowlist enforced, `:free` suffix required, paid models rejected by default, fallback tries next free model |
| Row-level security is enabled on `documents`, `document_chunks`, and `feedback`, verified by test | **Met** | RLS enabled in migrations; test in `backend/tests/integration/test_rls_and_isolation.py` confirms anon-key client gets zero rows |
| Every generated citation maps to a retrieved chunk owned by authenticated user (or `is_public` demo corpus) | **Met** | Citation verifier maps labels to retrieved chunks; ownership enforced in retrieval |
| Assistant abstains for missing evidence (using evaluation-derived threshold) and rejects invalid citation labels | **Not met** | Abstention is effectively unreachable due to flat OR-threshold bug (P0 finding #4); citation label validation works but evidence check does not |
| Document ownership is enforced on all read/search/delete operations; `is_public` demo corpus is readable by all but not editable/deletable by any | **Met** | Repository layer filters by `owner_id` or `is_public=true`; demo docs blocked from delete/edit with 403 |
| Indirect prompt-injection text inside a document is treated as untrusted content | **Met** | System prompt instructs model to ignore instructions in retrieved content; eval dataset includes injection test case |
| Signup is invite-only by default, with a seeded read-only demo corpus available to reviewers | **Partial** | `SIGNUP_MODE=invite` in config and an invite-only notice in the sign-in UI, but the docs do not explain how to disable public signup in Supabase or grant invites (P2 docs drift) |
| Shared daily LLM request budget is enforced and surfaced with clear message and reset time | **Partial** | Budget enforcement exists, 429 response includes reset time, but budget is charged incorrectly (before validation, on abstain paths, doesn't account for 2 calls) and has a race condition (P1 finding) |
| Unit tests cover retrieval, RRF, graph routing, citations, authorization, and API errors without external APIs; RLS and SQL-dependent behavior covered against real `pgvector` container in CI | **Partial** | Tests exist and pass (39 tests), pgvector CI container configured, but several tests are hollow (RRF, tsquery, citation tests don't test the real code paths) and many cases are missing (P2 findings) |
| Frontend lint/type checks and production build pass | **Met** | `npm run lint` and `npm run build` both pass with no errors |
| CI is configured for offline checks (pgvector service container is local-to-runner) | **Partial** | CI workflow exists with pgvector container, but downloads FastEmbed model from Hugging Face (external call, P2 finding); has never run due to no commits |
| Evaluation runner produces actual retrieval metrics, including ablation table, on documented dataset | **Partial** | Retrieval eval exists and produces real metrics on 35-case dataset, ablation table present, but Ragas eval is fabricated (P0 finding #3) and narrative contradicts measurements (P0 finding #5) |
| README setup steps work on a clean machine with credentials supplied by user | **Not met** | Docs use the wrong env var (`MODEL_ALLOWLIST` vs `OPENROUTER_MODELS`) and bucket name, and omit Supabase project setup, redirect URLs, CORS and bucket creation (P2 docs drift) |
| No secrets, user data, cache files, generated uploads, or credentials are committed | **Partial** | Nothing is committed yet; `.gitignore` covers `.env`, caches and `.storage_cache`, but `*.tsbuildinfo` is not ignored (P2 hygiene) |
| Deployment guide reflects current provider limits and free-tier caveats, including session-pooler connection requirement and Render/Supabase cold-start/inactivity behavior | **Partial** | Deployment docs exist in README and `docs/deployment.md`, session pooler mentioned, but several details are missing or contradict implementation (P2 finding) |

**Summary:** 11 Met, 8 Partial, 2 Not met, 1 Unverified

---

## Suggested Fix Order

1. **P0 #1-2 (auth):** Default to production environment, add test-token guards, fix issuer check, separate HS256 secret
2. **P0 #4 (abstention):** Move evidence decision to `assess_evidence_node`, combine signals with AND logic, run threshold sweep, document chosen value
3. **P0 #3, #5 (honest eval):** Delete or implement real Ragas evaluation, generate narrative from measured data, reconcile README table with JSON
4. **P1 LLM layer:** Fix exception handling, surface truncated responses as errors, pass reasoning effort, remove hardcoded default
5. **P1 daily budget:** Atomic UPDATE query, charge per actual LLM call, move charging to graph nodes
6. **P1 uploads/storage:** Stream size check, validate before 202, magic bytes, DB-before-storage, disable fallback in prod
7. **P2 tests:** Add missing test cases (hollow tests, JWT, finish_reason, deletion, duplicate, RLS, cross-user, polling, abstain routing)
8. **P2 CI:** Cache FastEmbed model, add separate type-check, add keep-alive workflow, create initial commit
9. **P1 smaller gaps:** Schema-qualify extension, add updated_at trigger, secure get_by_id default, tighten EXEMPT_REGEX, 400 for invalid question, add fact-vs-inference instruction
10. **P1 LangChain usage:** Use Document objects, FastEmbedEmbeddings wrapper, ChatPromptTemplate
11. **P2 frontend:** Add AbortController, distinct error states, fix preview contract, unify feedback ID, delete template files, add Vitest
12. **P2 docs:** Reconcile variable names, add missing sections, remove or complete Dockerfile snippet
13. **P2 hygiene:** Gitignore tsbuildinfo, delete .storage_cache, decide on GEMINI files

Address P0 items before any deployment. P1 items are required to match the specification. P2 items improve completeness and polish but do not block a functional demo.

---

## Active Execution Plan & Progress Tracker

### Phase 1: P0 Critical Vulnerability & Correctness Fixes
- [x] **1.1 Auth Security & JWT Hardening**
  - [x] `backend/app/core/config.py`: Default `ENVIRONMENT="production"`, add `ALLOW_TEST_TOKENS=False`, add `SUPABASE_JWT_SECRET` (optional SecretStr). Add validator refusing start if `ALLOW_TEST_TOKENS=True` and `ENVIRONMENT != "test"`.
  - [x] `backend/app/core/auth.py`: Only accept `test-token-<uuid>` if `ENVIRONMENT == "test"` AND `ALLOW_TEST_TOKENS is True`.
  - [x] `backend/app/core/auth.py`: In JWKS verification, enforce `iss=f"{settings.SUPABASE_URL}/auth/v1"` and require `sub`, `exp`, `aud`.
  - [x] `backend/app/core/auth.py`: In HS256 fallback, require `SUPABASE_JWT_SECRET` (do not use service key) and only permit if `ENVIRONMENT != "production"`.
  - [x] Tests: Verify unsigned test tokens fail in default/production config; verify issuer and aud validation; verify test tokens work in test environment.
- [x] **1.2 Abstention & Evidence Sufficiency Engine**
  - [x] `backend/app/graph/nodes.py`: Refactor `assess_evidence_node` to compute composite sufficiency using top chunk similarity, keyword match score, and score drop/gap across candidates (AND/weighted logic instead of flat OR).
  - [x] `backend/app/services/retrieval.py`: Update candidate scoring and deprecate flat OR threshold.
  - [x] Empirical tuning: Run evaluation on `evaluation/dataset.json` ensuring abstention recall reaches ≥ 0.75 without causing false abstentions on answerable queries (achieved 100% recall, 0% false abstention).
  - [x] `docs/architecture.md`: Document threshold formulation and empirical justification.
- [x] **1.3 Honest Evaluation Suite**
  - [x] `evaluation/run_ragas_eval.py`: Replace fabricated metrics with documented future work or honest runner with clear status.
  - [x] `evaluation/run_retrieval_eval.py`: Generate summary narrative dynamically from actual JSON benchmark measurements.
  - [x] `README.md`: Align metrics table with verified benchmark results.

### Phase 2: P1 Spec Conformance & Reliability Fixes
- [x] **2.1 LLM Layer Hardening**
  - [x] `backend/app/services/model_factory.py`: Avoid broad `except Exception`; handle specific provider errors (429 rate limit, 503 unavailable, 404 model not found) for fallback.
  - [x] `model_factory.py`: Detect `finish_reason == "length"` and raise `ResponseTruncatedError` instead of returning clipped answer with broken citations.
  - [x] Pass `reasoning={"effort": settings.OPENROUTER_REASONING_EFFORT}` to model instantiation. Remove hardcoded fallback model slug.
- [x] **2.2 Daily LLM Budget Concurrency & Charging**
  - [x] `backend/app/core/rate_limit.py`: Atomic database or locked update for counter increment (`INSERT ... ON CONFLICT DO UPDATE WHERE call_count + count <= max_budget RETURNING`).
  - [x] Charge budget on actual LLM calls inside LangGraph nodes (`generate_answer_node`), not upfront in `chat.py`. Prevent charging on validation failure or abstention paths.
- [x] **2.3 Document Uploads & Storage Security**
  - [x] `backend/app/api/documents.py`: Check `Content-Length` / stream limit before reading entire file into memory; validate MIME and extension upfront returning 415.
  - [x] Add magic-byte inspection against `SUPPORTED_MIME_TYPES`.
  - [x] Invert flow: insert DB row first, upload to storage second to prevent orphan files on uniqueness conflict.
  - [x] `backend/app/services/storage.py`: Prohibit local disk fallback in `production`.
- [x] **2.4 Database & Query Precision**
  - [x] `backend/app/db/engine.py`: Add `prepare_threshold=None` and document session pooler requirement.
  - [x] `backend/app/services/ingestion.py`: Insert chunks and update document status in a single transaction via `DocumentRepository.save_chunks_and_mark_ready`.
  - [x] `backend/app/services/retrieval.py`: Cast `selected_doc_ids` to `UUID[]` explicitly in SQL parameter binding.
  - [x] `backend/app/db/repositories.py`: Secure `get_by_id` default to `allow_public=False`.
- [x] **2.5 Spec Gaps & LangChain Substantive Usage**
  - [x] `supabase/migrations/`: Schema-qualify `vector` extension, add `updated_at` trigger.
  - [x] `backend/app/services/citation_verifier.py`: Tighten `EXEMPT_REGEX` to prevent exempting substantive statements.
  - [x] `backend/app/graph/nodes.py`: Return 400 for empty/invalid question; add fallback for query rewrite error.
  - [x] `backend/app/services/generation.py`: Update system prompt with "Distinguish facts from inferences".
  - [x] Adopt `langchain_core.documents.Document`, `ChatPromptTemplate`, and `FastEmbedEmbeddings` wrapper.

### Phase 3: P2 Testing, CI, Frontend & Hygiene
- [x] **3.1 Comprehensive Test Suite**
  - [x] Add live tests for `HybridRetrievalService.search` RRF and tsquery execution (`test_retrieval_and_rrf.py`).
  - [x] Add tests for JWT validation, finish_reason length, storage deletion cascade, duplicate prevention, and cross-user isolation (69 tests total).
- [x] **3.2 CI Pipeline & Keep-alive**
  - [x] Cache FastEmbed model and pre-download in CI runner setup step to prevent live HF downloads during test execution.
  - [x] Add explicit `npx tsc --noEmit` and `npm test` steps, and configure scheduled Supabase + Backend keep-alive workflow.
- [x] **3.3 Frontend Polish**
  - [x] Add `AbortController` support to chat, preview, and document upload requests.
  - [x] Map API errors to distinct UI states (401 auth, 429 quota/rate limit reset timer, 503 instance cold start).
  - [x] Align preview document and feedback response types; remove Vite template artifacts (`hero.png`); configure Vitest smoke tests.
- [x] **3.4 Hygiene & Knowledge Graph Update**
  - [x] Update `.gitignore` with `*.tsbuildinfo`, remove `.storage_cache`, set fallback path to `/tmp/.storage_cache`.
  - [x] Reconcile documentation drift in `README.md` and `docs/deployment.md`.
  - [x] Run `graphify update .` to keep knowledge graph up to date.


### Phase 4: Post-verification follow-ups
- [x] **4.1** Consolidate the evidence-sufficiency check into one function used by both the graph and the benchmark (V1).
- [x] **4.2** Move the hardcoded evidence thresholds into validated settings; make `MIN_RETRIEVAL_SIMILARITY` the real floor (V2).
- [x] **4.3** Add held-out abstention cases or document that the reported abstention accuracy is in-sample (V3).
- [x] **4.4** Charge each model-fallback attempt against the daily LLM budget (V4).
- [x] **4.5** Decide whether `GEMINI.md` / `.gemini/` are committed or ignored (V5).
- [x] **4.6** Make the first commit and push so CI and the keep-alive workflow actually run (V6).

---

## Verification of Implementation (2026-10-14)

Independent re-check of the progress tracker above against the source, after all Phase 1–3 items were marked done.

**Checks re-run (actual output):**

| Check | Result |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 44 files already formatted |
| `pytest -q` | 69 passed in 3.42s (local Postgres reachable) |
| `npm run lint` | Passed |
| `npx tsc --noEmit -p tsconfig.json` | Passed |
| `npx vitest run` | 2 passed (1 file) |
| `npm run build` | Built, 432.14 kB JS bundle |

**Confirmed fixed in source:**
- **Auth bypass (P0-1):** `ENVIRONMENT` defaults to `production` (`config.py:20`); `test-token-` is accepted only when `ENVIRONMENT == "test"` and `ALLOW_TEST_TOKENS` is true (`auth.py:46-63`); the settings validator refuses `ALLOW_TEST_TOKENS` outside `test`.
- **JWT hardening (P0-2):** JWKS path enforces `iss`, `aud`, `exp` and requires `exp`/`sub`/`aud`; HS256 uses a separate `SUPABASE_JWT_SECRET` and is disabled in `production`.
- **Fabricated Ragas report (P0-3):** `run_ragas_eval.py` removed; README states LLM-based evaluation is future work.
- **Eval narrative (P0-5):** `run_retrieval_eval.py` renders the report from measured values.
- **Abstention (P0-4):** multi-signal check in place; benchmark shows hybrid abstention accuracy 1.000, false-abstention rate 0.000 (see V2/V3 caveats below).
- **Daily budget:** atomic `INSERT … ON CONFLICT DO UPDATE … WHERE call_count + n <= budget RETURNING` (`repositories.py:195-225`), charged in `generate_answer_node` rather than up front.
- **LLM layer:** fallback only on retriable provider errors, `finish_reason == "length"` raises `ResponseTruncatedError`, `reasoning={"effort": …}` passed (`model_factory.py:79-121`).
- **Hygiene:** `*.tsbuildinfo` in `.gitignore`; `.storage_cache/` directories removed.

### V1. Evidence-sufficiency logic is duplicated

**Problem:** The same threshold logic exists twice. The app runs one copy and the benchmark measures the other, so they can silently drift and the published metrics would stop describing production behavior.

**Evidence:**
- `backend/app/graph/nodes.py:114-146`: `assess_evidence_node` (used by the LangGraph workflow)
- `backend/app/services/retrieval.py:243-285`: `HybridRetrievalService.evaluate_evidence_sufficiency` (used by `evaluation/run_retrieval_eval.py:150` via `res.evidence_sufficient`)

**Fix:** Extract a single pure function (e.g. `is_evidence_sufficient(vector_sims, keyword_scores, settings, mode)`) in `retrieval.py`; have both `assess_evidence_node` and `evaluate_evidence_sufficiency` call it.

**Verify:** Add a unit test asserting both call sites return the same decision on the same fixed inputs; `grep -n "0\.72" backend/app` finds no thresholds in `nodes.py`.

### V2. Evidence thresholds are hardcoded; `MIN_RETRIEVAL_SIMILARITY` is dead config

**Problem:** AGENTS.md §6/§9.4 require configurable thresholds. The decision uses literal constants, while the documented setting is loaded but never consulted.

**Evidence:**
- Literals `0.50`, `0.72`/`0.15`, `0.63`/`0.50`, `0.65`/`0.05`, vector-only `0.65`, keyword-only `0.45` in `nodes.py:132-141` and `retrieval.py:262-282`
- `retrieval.py:53` stores `self.min_similarity` but never reads it
- `MIN_RETRIEVAL_SIMILARITY=0.25` still documented in `.env.example:43` and `docs/deployment.md:105`

**Fix:** Repurpose `MIN_RETRIEVAL_SIMILARITY` as the semantic floor (default 0.50) and add `EVIDENCE_*` settings for the remaining thresholds, defaulting to today's values, with [0, 1] validation in `validate_numeric_bounds`. Update `.env.example`, `docs/deployment.md`, and `docs/architecture.md`.

**Verify:** Re-run `python evaluation/run_retrieval_eval.py`; hybrid abstention accuracy stays 1.000 and false-abstention rate 0.000 with default settings. A config test rejects an out-of-range `EVIDENCE_*` value.

### V3. Reported abstention accuracy is in-sample

**Problem:** The thresholds were tuned on the same 35-case `evaluation/dataset.json` that produces the 1.000 abstention accuracy, so the number measures fit, not generalization. Presenting it without that caveat is the kind of overclaim AGENTS.md §15 warns against.

**Evidence:** `evaluation/retrieval_benchmark.json` (`hybrid_rrf.abstention_accuracy: 1.0`); tracker item 1.2 ("Empirical tuning: Run evaluation on `evaluation/dataset.json`…").

**Fix:** Add a held-out set of answerable and should-abstain questions not used for tuning and report it separately, or at minimum state in `docs/architecture.md` and the README results table that the figure is in-sample.

**Verify:** The report shows tuning-set and held-out metrics separately, or the in-sample caveat appears next to every place the abstention figure is published.

### V4. Model-fallback attempts are not charged to the daily budget

**Problem:** The budget is charged once per `generate_answer_node`, but `model_factory.py` may try several allowlisted models, and each attempt is a separate OpenRouter request that can count toward the provider's daily limit. Real usage can exceed `LLM_DAILY_REQUEST_BUDGET`.

**Evidence:** `backend/app/graph/nodes.py:208-213` (single `consume_daily_llm_budget(calls_needed=1)`); `backend/app/services/model_factory.py:96-121` (loop over allowlist).

**Fix:** Consume one budget unit per model attempt inside the fallback loop (stopping with the 429 budget error if exhausted mid-loop), or charge the worst case up front and refund unused units.

**Verify:** Unit test with a fake model that fails on the first allowlisted slug and succeeds on the second; the counter increases by 2.

### V5. `GEMINI.md` and `.gemini/` still present

**Problem:** Tool-specific agent files sit at the repo root and would be included in the first commit.

**Fix:** Decide whether to commit them; if not, add them to `.gitignore`.

**Verify:** `git status` after the first `git add` matches the intent.

### V6. CI and keep-alive workflows have never run

**Problem:** The repository has no commits, so `.github/workflows/ci.yml` and `.github/workflows/keepalive.yml` are unverified. Local checks passing doesn't prove the pgvector service container, model cache step, or schedule work on GitHub Actions.

**Fix:** Make the first commit, push to GitHub, and trigger both workflows (keep-alive via `workflow_dispatch` if configured).

**Verify:** Both workflows show a green run in the Actions tab.
