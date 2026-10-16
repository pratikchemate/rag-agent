# Deployment Plan: Enterprise Knowledge AI

> **Goal:** Deploy the app for a public portfolio demo on free tiers: **Vercel Hobby** (frontend), **Render Free** (FastAPI backend) and **Supabase Free** (Postgres + pgvector, Storage, Auth).
>
> **Constraints (AGENTS.md §4, §19):**
> - No billing, no paid models, no paid add-ons.
> - Deployment is a **manual** step. No resources are created automatically.
> - Re-verify provider limits before relying on them.
>
> **Related docs:**
> - [`docs/deployment.md`](docs/deployment.md) is the operator runbook (env reference, SQL commands, architecture diagram).
> - This file is the **plan and tracker**: what has to happen, in what order, and how each step is verified.

---

## Phase 0: Pre-flight

### 0.1 Re-verify live free-tier limits
Every figure below can change. Check each one live and update the docs if it differs.

| Provider | What to check | Where | Value assumed today |
|---|---|---|---|
| OpenRouter | Current `:free` slugs; every entry in `OPENROUTER_MODELS` must still resolve | `GET https://openrouter.ai/api/v1/models` (filter on `:free`) | `gemma-4-31b-it`, `gemma-4-26b-a4b-it`, `nemotron-3.5-lightning`, `lfm-2.5-2.6b` |
| OpenRouter | Request limits | https://openrouter.ai/docs/api-reference/limits | 20/min; 50/day (1000/day after a one-time ≥$10 top-up) |
| Render | Free web service RAM, spin-down, build minutes | https://render.com/docs/free | 512 MB, spins down after ~15 min idle, ~1 min cold start |
| Supabase | DB/storage quota, inactivity pause | https://supabase.com/pricing | 500 MB DB, 1 GB storage, pauses after ~7 days idle |
| Vercel | Hobby terms (personal, non-commercial use) | https://vercel.com/docs/plans/hobby | OK for a personal portfolio |

**Verify:**
- Record any changed values in `docs/deployment.md` §2.
- Update the `OPENROUTER_MODELS` default in `backend/app/core/config.py` and `.env.example` if a slug is gone.

### 0.2 Clean working tree
- **Settle the Vite dev-port drift.** The uncommitted `frontend/vite.config.ts` uses port **5174** and proxies `/api` to **8001**. The CORS default, `OPENROUTER_APP_URL`, `.env.example` and README all say **5173** and backend **8000**. Pick one:
  - (a) revert to 5173 and drop the proxy;
  - (b) keep it, and update `CORS_ALLOWED_ORIGINS`, `OPENROUTER_APP_URL`, `.env.example`, the README and `docs/deployment.md` to match.

  Production is unaffected either way, because `frontend/src/lib/api.ts:9` uses `VITE_API_BASE_URL`.
- Commit the remaining uncommitted files: the greeting feature, the tests, `App.tsx`, and the regenerated benchmark outputs.
- Note the greeting shortcut in `docs/architecture.md`. It returns a canned answer with no citations, which is an intentional exception to the citation rule.

**Verify:** `git status` is clean, and CI is green on `main`.

---

## Phase 1: Pre-deploy code work

Each item is problem · evidence · fix · verify, the same format as `updates.md`.

### 1.1 Seed the read-only public demo corpus
- **Problem:** AGENTS.md §13 and Phase 4 require seeded `is_public = true` documents so reviewers can try the app without uploading anything. Nothing in the codebase ever sets `is_public=True`.
- **Evidence:**
  - `backend/app/api/documents.py:127` hardcodes `is_public=False`.
  - `evaluation/run_retrieval_eval.py:50` `seed_fixture_documents` also uses `False`, with the eval owner.
  - The read paths already support public docs: `repositories.py:28,38` and `retrieval.py:153,182`.
- **Fix:** add `backend/scripts/seed_demo_corpus.py`, modeled on `seed_fixture_documents`:
  - Ingest `evaluation/fixtures/*.md` with `is_public=True` under a fixed `DEMO_OWNER_ID` UUID that no real user can have.
  - Upload the originals to Storage under `demo/…`.
  - Make it **idempotent**: skip any file whose checksum already exists for the demo owner, so re-running creates no duplicates.
  - Reuse `IngestionService` rather than duplicating the chunk/embed logic.
- **Verify:**
  - Run it twice locally against the pgvector container; the second run inserts 0 rows.
  - `GET /api/v1/documents` as any test user lists the demo docs.
  - `DELETE` on a demo doc returns 403.

### 1.2 Recover documents stuck in `processing` on startup
- **Problem:** Spec §8 rule 11 says rows stuck in `processing` past a staleness window should be reset to `failed` on restart. Render Free spins the process down while idle, so a `BackgroundTask` killed mid-ingest leaves a row in `processing` forever. It can't be retried, and the partial unique index blocks re-uploading the same file.
- **Evidence:** `lifespan` in `backend/app/main.py:26` only logs.
- **Fix:**
  - Add a `STALE_PROCESSING_MINUTES: int = 15` setting, range-validated.
  - In `lifespan`, run one parameterized `UPDATE documents SET status='failed', error_code='ingestion_interrupted', updated_at=now() WHERE status='processing' AND updated_at < now() - make_interval(mins => :m)`.
  - Delete orphan chunks for those rows.
  - Wrap it so a DB outage at boot logs a warning rather than crashing the app; `/health/ready` already reports DB state.
- **Verify:**
  - An integration test inserts a stale `processing` row, runs the lifespan, and asserts `failed`.
  - A fresh `processing` row is left untouched.

### 1.3 Render blueprint + build-time embedding model download
- **Problem:** There is no `render.yaml` and no Dockerfile. `EMBEDDING_CACHE_DIR` defaults to a relative `.fastembed_cache`. Without a build-time download, every cold start fetches about 130 MB from Hugging Face on Render's 0.1 CPU (spec §19).
- **Fix:** add a root-level `render.yaml`:
  ```yaml
  services:
    - type: web
      name: enterprise-knowledge-ai-api
      runtime: python
      plan: free
      rootDir: backend
      buildCommand: >
        pip install . &&
        python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/opt/render/project/src/backend/.fastembed_cache')"
      startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
      healthCheckPath: /api/v1/health/live
      envVars:
        - key: PYTHON_VERSION
          value: "3.13"
        - key: ENVIRONMENT
          value: production
        - key: ALLOW_TEST_TOKENS
          value: "false"
        - key: EMBEDDING_CACHE_DIR
          value: /opt/render/project/src/backend/.fastembed_cache
        - key: DATABASE_URL
          sync: false          # secrets set in dashboard, never committed
        - key: SUPABASE_URL
          sync: false
        - key: SUPABASE_PUBLISHABLE_KEY
          sync: false
        - key: SUPABASE_SECRET_KEY
          sync: false
        - key: OPENROUTER_API_KEY
          sync: false
        - key: OPENROUTER_MODELS
          sync: false
        - key: CORS_ALLOWED_ORIGINS
          sync: false
        - key: OPENROUTER_APP_URL
          sync: false
  ```
  Check that the cache path is inside the directory Render keeps from build to runtime. Only `/opt/render/project/src` persists between the build and run phases.
- **Verify:**
  - The Render build log shows the model download.
  - The runtime logs show **no** download on the first `/chat` or upload after a cold start.

### 1.4 Pin runtime versions to match CI
- **Problem:** CI runs Python **3.13** and Node **20** (`.github/workflows/ci.yml:36,95`). Render and Vercel default to their own versions.
- **Fix:**
  - Set `PYTHON_VERSION=3.13` in `render.yaml` (see 1.3).
  - Add `"engines": { "node": "20.x" }` to `frontend/package.json`, which Vercel honours.
- **Verify:** both build logs print the pinned versions.

### 1.5 Make the keep-alive actually prove liveness
- **Problem:** `.github/workflows/keepalive.yml` curls Supabase `/rest/v1/` with the anon key and ends every step with `|| echo "...completed"`, so it **can never fail**. The REST root also may not count as database activity.
- **Fix:**
  - Make `BACKEND_URL/api/v1/health/ready` the primary ping. It runs a real DB query, which keeps Supabase active and also wakes Render.
  - Add `--retry 3 --retry-delay 30 --max-time 120` to cover Render cold starts.
  - Remove the `|| echo` so a real outage fails the workflow run and sends a GitHub notification.
  - Keep the Supabase REST ping as a secondary step with `continue-on-error: true`.
- **Verify:**
  - A manual `workflow_dispatch` run succeeds against the live backend.
  - A run with a bogus `BACKEND_URL` fails visibly.

### 1.6 Measure memory against Render's 512 MB
- **Problem:** fastembed (ONNX), PyMuPDF, LangChain and LangGraph share one 512 MB process, and the peak has never been measured. An out-of-memory kill during ingest looks like a random 502.
- **Fix:**
  - Run the backend locally with `ENVIRONMENT=production`-like settings under `/usr/bin/time -v uvicorn …`, or in a `docker run --memory=512m python:3.13-slim` container.
  - Upload the largest allowed document (5 MB PDF, 300-chunk cap) and run a chat request alongside it.
  - Record the peak RSS.
- **Verify:**
  - Peak RSS is under ~400 MB, leaving headroom.
  - If it isn't, lower `EMBEDDING_BATCH_SIZE` to 8 and/or `MAX_CHUNKS_PER_DOCUMENT`, re-measure, and record the numbers in `docs/deployment.md`.

---

## Phase 2: Supabase (manual, in the dashboard)

1. Create a Free project and save the DB password in a password manager.
2. Copy the **session pooler** connection string (pooler host, port **5432**). Do not use the direct host, which is IPv6-only, or the transaction pooler on 6543.
3. Apply the migrations in order:
   ```bash
   for f in supabase/migrations/000{1,2,3}_*.sql; do psql "$POOLER_URL" -v ON_ERROR_STOP=1 -f "$f"; done
   ```
4. **Verify RLS** before inserting any data:
   - `select relname, relrowsecurity from pg_class where relname in ('documents','document_chunks','feedback','daily_usage_counters');` should be `t` for all four.
   - `curl -s "$SUPABASE_URL/rest/v1/documents?select=*" -H "apikey: $ANON" -H "Authorization: Bearer $ANON"` should return `[]`.
5. **Storage:** create the private bucket `source-documents` with a 5 MB limit and MIME allowlist `application/pdf, text/plain, text/markdown, application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
6. **Auth:**
   - Turn off "Allow new users to sign up" so signup is invite-only.
   - Set the Site URL and Redirect URLs to the Vercel URL. Use a placeholder first and update it in Phase 4.
   - Invite the demo or reviewer accounts through Authentication → Users → Invite.
7. **JWKS:** `curl $SUPABASE_URL/auth/v1/.well-known/jwks.json` should return at least one asymmetric key (RS256/ES256). If the project is still on a legacy HS256 secret, migrate the signing keys in the dashboard. Production rejects HS256.
8. **Seed the demo corpus:** run `python backend/scripts/seed_demo_corpus.py` (from 1.1) with the production `DATABASE_URL` and Supabase keys exported only in that shell session.

**Verify:**
- RLS check passes.
- Bucket is private.
- Signup is disabled.
- `select count(*) from documents where is_public` is greater than 0.

---

## Phase 3: Render backend

1. In Render, create a New Blueprint from the GitHub repo, which picks up `render.yaml`.
2. Fill in the `sync: false` secrets in the dashboard:
   - `DATABASE_URL`: the session pooler string from Phase 2.2, as `postgresql+psycopg://…:5432/postgres`.
   - `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`.
   - `OPENROUTER_API_KEY`, and `OPENROUTER_MODELS` set to the slugs verified in 0.1.
   - `CORS_ALLOWED_ORIGINS` and `OPENROUTER_APP_URL`: a placeholder until the Vercel URL is known.
   - Keep the defaults for `LLM_DAILY_REQUEST_BUDGET=40` (under the 50/day ceiling with headroom), `SIGNUP_MODE=invite` and `ALLOW_PAID_MODEL=false`.
3. Deploy.

**Verify:**
- `curl https://<svc>.onrender.com/api/v1/health/live` returns `{"status":"ok"}`.
- `curl …/health/ready` returns 200, which means the DB is reachable through the pooler.
- The startup log shows `env=production` and the expected model list, with no secret values printed.
- An unauthenticated `POST /api/v1/chat` returns 401.
- A request with a `test-token` returns 401, confirming the test tokens are disabled in production.

---

## Phase 4: Vercel frontend

1. Import the repo into Vercel with:
   - **Root Directory** `frontend`;
   - framework preset **Vite**;
   - build `npm run build`, output `dist`;
   - Node 20 (see 1.4).
2. Set **only** these environment variables:
   - `VITE_API_BASE_URL=https://<svc>.onrender.com/api/v1`
   - `VITE_SUPABASE_URL=https://<ref>.supabase.co`
   - `VITE_SUPABASE_ANON_KEY=<publishable/anon key>`
3. Deploy, then **loop back** with the final `https://<app>.vercel.app` domain:
   - In Render, set `CORS_ALLOWED_ORIGINS` and `OPENROUTER_APP_URL` to it, then redeploy. Exact origin, no `*`.
   - In Supabase Auth, set the Site URL and Redirect URLs to it.

**Verify:**
- Run `grep -rE "sk-or-|service_role|SUPABASE_SECRET" frontend/dist` locally on a production build. It should find nothing.
- The browser devtools show no CORS errors on `/documents` and `/chat`.

---

## Phase 5: GitHub wiring

1. Add the repo secrets `BACKEND_URL` (the Render URL with no trailing slash), `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
2. Trigger **Supabase and Backend Keepalive** manually with `workflow_dispatch`.

**Verify:**
- The run succeeds.
- The Render logs show the `/health/ready` hit.
- The schedule (Mon/Thu 06:00 UTC) is visible under Actions.

---

## Phase 6: Production smoke test (AGENTS.md §19)

- [ ] Sign in with an invited account. The sign-up path is blocked for uninvited emails.
- [ ] The data-handling disclaimer appears before the first upload.
- [ ] Upload a small public PDF. The response is **202** / `processing`, and polling reaches `ready`.
- [ ] The document row, its chunks and the Storage object all exist.
- [ ] A known-answer question returns an answer with `[S1]`. The citation's filename, page and excerpt match the real chunk.
- [ ] An out-of-corpus question gets an **abstention** that isn't styled as an error.
- [ ] A greeting ("hi") returns the conversational reply and doesn't consume the LLM budget (check `daily_usage_counters`).
- [ ] As **user B**: user A's document ID returns 404 for get, preview, delete and chat filter. The public demo docs are visible but not deletable (403).
- [ ] An anon-key Data API query on `documents` and `document_chunks` returns `[]`.
- [ ] Deleting the document removes the Storage object and all its chunk rows.
- [ ] Budget exhaustion is tested **in a local, non-production run** with `LLM_DAILY_REQUEST_BUDGET=1`: you get a 429 `llm_daily_budget_exhausted` with `reset_at`, and the UI shows the reset time. Do not burn the production quota.
- [ ] Provider failure, tested locally with a mock: fallback moves to the next `:free` slug and never reaches a paid one.
- [ ] Cold start: after more than 15 minutes idle, record the time to first `/health/live` and to the first chat. Note both in `docs/deployment.md`.

---

## Phase 7: Post-deploy polish

- Add the live demo URL, invite instructions and screenshots (sign-in, cited answer, abstention, citation panel) to the README.
- Record the measured cold-start times and the 1.6 memory peak in `docs/deployment.md`.
- **Rollback notes:**
  - Render: redeploy a previous commit from the dashboard.
  - Vercel: use Instant Rollback to a previous deployment.
  - Supabase migrations are **additive only**. Never edit an applied migration; add a new `000N_*.sql`.
- Set a monthly reminder to re-check the `:free` slugs, since models disappear without notice.

---

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| A `:free` model slug is removed | Chat returns provider errors | Allowlist fallback; update `OPENROUTER_MODELS` in Render (no redeploy of code needed); monthly slug check |
| Visitors exhaust 50/day quota | Distinct 429 with reset time | `LLM_DAILY_REQUEST_BUDGET=40`, deterministic rewrite first, greeting shortcut; optional one-time OpenRouter top-up → 1000/day |
| Supabase pauses after inactivity | `/health/ready` 503, demo down | Keep-alive workflow (1.5) twice weekly, failing loudly |
| Render OOM during ingest | 502 on upload, row stuck | Measure (1.6), small batch size, chunk cap, stale-row recovery (1.2) |
| Spin-down kills BackgroundTask | Row stuck in `processing` | Stale-row recovery on startup (1.2); user can re-upload |
| Secret leaked to frontend or git | Key abuse | Only `VITE_*` public vars on Vercel; `dist/` grep (Phase 4); `sync: false` in `render.yaml` |
| Cold start (~1 min) looks broken | Reviewer bounces | Frontend cold-start messaging; README note; keep-alive also wakes Render |

---

## Progress tracker

- [x] **Phase 0: Pre-flight**
  - [x] 0.1 Live limits and `:free` slugs re-verified
  - [x] 0.2 Port drift settled, working tree committed, CI green
- [x] **Phase 1: Pre-deploy code work**
  - [x] 1.1 Public demo corpus seed script
  - [x] 1.2 Stale `processing` recovery on startup
  - [x] 1.3 `render.yaml` + build-time model download
  - [x] 1.4 Python 3.13 / Node 20 pinned
  - [x] 1.5 Keep-alive hardened
  - [x] 1.6 Memory measured under 512 MB
- [x] **Phase 2: Supabase** provisioned, RLS verified, bucket, invite-only auth, JWKS, seeded
- [ ] **Phase 3: Render** deployed, health checks green, test tokens rejected
- [ ] **Phase 4: Vercel** deployed, no secrets in bundle, CORS and redirect URLs finalized
- [ ] **Phase 5: GitHub** secrets set, keep-alive run green
- [ ] **Phase 6: Smoke test** checklist complete
- [ ] **Phase 7: Post-deploy** README, measurements, rollback notes
