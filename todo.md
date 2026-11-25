# Lyftr AI — Implementation TODO

> Source of truth: [PRD.md](PRD.md)
> Delivery window: 24 hours from kickoff
> Status: Not started
> Rule: keep every **P0** item green before spending time on polish.

## How to use this list

- **P0** — required by the assignment, the contract, deployment, or evaluation. Do not cut.
- **P1** — required for a quality submission or a stated PRD decision.
- **P2** — polish or optional improvement; cut first if time runs short.
- Mark tasks `[x]` when done, `[~]` when in progress, and `[!]` when blocked.
- Work top to bottom within each phase. Phases may overlap only where explicitly noted.
- If a phase slips by more than 30 minutes, cut P2 work, not P0 work.

## Critical path

`provider/cache spike → config + SQLite → LLM gateway → chat API → frontend → tests → Docker → deploy → live verification → demo → submit`

---

## Phase 0 — Setup and spikes (T+0–2)

### Repository and tooling

- [ ] P0 Initialize a Git repository; add `.gitignore` entries for env files, SQLite databases, Python caches, `node_modules`, and build outputs.
- [ ] P0 Create the assignment's required top-level layout: backend, frontend, Compose file, Makefile, environment template, README.
- [ ] P0 Scaffold the FastAPI backend with locked dependencies: FastAPI, Uvicorn, LiteLLM, SQLAlchemy, aiosqlite, pydantic-settings, pytest tooling.
- [ ] P0 Scaffold the React + Vite + TypeScript frontend with Tailwind CSS.
- [ ] P0 Create `.env.example` with every backend and frontend variable and safe placeholders.
- [ ] P0 Add the PRD and assignment brief to the repo docs or link them from the README.

### Provider and cache spike (must pass before UI work)

- [ ] P0 Create two Gemini API keys from separate Google AI Studio projects.
- [ ] P0 Verify the current model ID (`gemini/gemini-3.5-flash-lite` or the nearest stable Flash-Lite model) works through LiteLLM.
- [ ] P0 Confirm one live completion returns non-empty text and usage tokens.
- [ ] P0 Enable LiteLLM's in-memory cache; confirm a second identical call is a cache hit with identical text, stored usage, and lower latency.
- [ ] P0 Confirm the cache-hit signal is detectable per request.
- [ ] P0 Confirm an explicit custom cache key can exclude API key, key ID, session ID, and simulation state while still hitting across keys and sessions.
- [ ] P0 Confirm cache TTL behavior.
- [ ] P0 Confirm a simulated 429 can fail a chosen key without a network call.
- [ ] P1 Record spike results in a short note or in the README design section.

### Decisions

- [ ] P0 Choose a deployment platform with Docker support, a persistent volume, an always-on single instance, HTTPS, and env-based secrets. Record the choice.
- [ ] P0 Record the final model ID and a fallback model ID.
- [ ] P0 Record cache TTL, per-attempt timeout, and overall timeout.
- [ ] P0 Freeze the API and UI contract; any change must update the PRD and tests.

**Gate 0:** model/cache/usage spike passes; repo scaffold runs; deployment target is chosen.

---

## Phase 1 — Backend foundation (T+2–7)

### Configuration and startup

- [ ] P0 Build typed settings for all environment variables.
- [ ] P0 Validate at least two keys, non-empty origins, a usable database URL, and numeric bounds.
- [ ] P0 Parse keys in order and assign `key_1`…`key_n`; reject empty or duplicate keys.
- [ ] P0 Initialize LiteLLM's in-memory cache with TTL and the custom cache key.
- [ ] P0 Configure timeouts, temperature, max output tokens, and the default system prompt.
- [ ] P0 Add an application factory for tests; create the schema on startup.
- [ ] P0 Fail fast with a clear log message on invalid config; never print secrets.

### SQLite repository

- [ ] P0 Add an async SQLAlchemy engine with aiosqlite; honor `DATABASE_URL`.
- [ ] P0 Enable WAL mode, foreign keys, and a busy timeout.
- [ ] P0 Create the `sessions` and `messages` tables plus a `(session_id, id)` index.
- [ ] P0 Implement repository methods: read session/prompt, read ordered history, atomically save an exchange, check database health.
- [ ] P0 Store assistant metadata JSON with every contract field.
- [ ] P0 Ensure failed requests write no session, no messages, and no prompt change.

### Failure simulation

- [ ] P0 Parse `X-Simulate-Failure` pairs, wildcard `*`, whitespace, and duplicate keys (last wins).
- [ ] P0 Ignore unknown key IDs, malformed pairs, and unsupported statuses.
- [ ] P0 Honor the header only when `ENABLE_FAILURE_SIMULATION=true`; otherwise ignore it completely.
- [ ] P0 Scope simulated failures to one request and bypass cache reads/writes when active.

### LLM gateway and key pool

- [ ] P0 Build the full message list: effective system prompt, stored history, new message.
- [ ] P0 Compute the explicit cache key from model, full messages, and generation parameters; exclude keys, session IDs, and simulation state.
- [ ] P0 Call LiteLLM with caching enabled; normalize a cache hit to `LLM_CACHE`, null key, zero fallbacks, and stored usage.
- [ ] P0 Iterate keys in order on a miss; one attempt per key; disable LiteLLM's own retry layer per attempt.
- [ ] P0 Classify 429, quota, 5xx, timeout, connection, authentication, and empty replies as failover-eligible.
- [ ] P0 Enforce per-attempt and overall timeouts.
- [ ] P0 Return model, latency, token usage, key ID, and fallback count.
- [ ] P0 Map all-keys-failed to the exact 503 domain error; persist nothing.
- [ ] P0 Never expose API keys; use key IDs only.

### Chat service and API

- [ ] P0 Add Pydantic validation: session 1–128 chars, message 1–4,000 after trim, system prompt ≤4,000 after trim, malformed JSON returns 422.
- [ ] P0 Add a per-session async lock; allow different sessions to proceed in parallel.
- [ ] P0 Implement system-prompt semantics: default, override, reset on empty, persist only on success.
- [ ] P0 Measure latency with a monotonic clock; return integer milliseconds including lock wait, provider work, and DB write.
- [ ] P0 Implement `GET /health` with exact required fields; return 503 when not ready.
- [ ] P0 Implement `POST /chat` with the exact success shape.
- [ ] P0 Implement `GET /sessions/{session_id}/messages`: oldest first, no system prompt, exact 404 detail.
- [ ] P0 Add JSON error handlers for 422, exact 503, exact 404, and 500; no HTML or stack traces.
- [ ] P0 Configure CORS from `ALLOWED_ORIGINS`; allow `Content-Type` and `X-Simulate-Failure`.
- [ ] P0 Disable generated docs routes in deployed environments.
- [ ] P1 Add structured request logs: request ID, source, key ID, fallback count, latency, tokens, outcome; no message content or keys.

### Backend acceptance

- [ ] P0 `GET /health` returns the exact 200 shape.
- [ ] P0 `POST /chat` returns a live reply with complete metadata.
- [ ] P0 A follow-up message uses prior history.
- [ ] P0 Repeating the first message in a new session returns `LLM_CACHE` with null key and zero fallbacks.
- [ ] P0 `X-Simulate-Failure: key_1=429` returns a real reply from `key_2` with one fallback.
- [ ] P0 `X-Simulate-Failure: *=429` returns the exact 503 and stores nothing.
- [ ] P0 The history endpoint matches stored turns.
- [ ] P0 Invalid input returns 422 JSON.

**Gate 1:** backend contract passes the manual curl matrix with no unhandled errors.

---

## Phase 2 — Frontend (T+7–11)

### Foundation

- [ ] P1 Define Tailwind theme tokens: warm off-white, ink, signal green, amber, typography, spacing.
- [ ] P1 Build the responsive app shell: header, session indicator, transcript area, sticky composer.
- [ ] P1 Add a typed API client using `VITE_API_BASE_URL`, with error normalization and timeout handling.
- [ ] P1 Generate a new session ID on every page load; keep the transcript in memory only.

### Chat experience

- [ ] P0 Add the `chat-input` textarea; Enter sends, Shift+Enter inserts a newline, show a 4,000-character counter.
- [ ] P0 Disable Send for empty/pending input; add the `send-button`.
- [ ] P0 Clear the input immediately after sending.
- [ ] P0 Render user and assistant messages; wrap each assistant reply in `assistant-message`.
- [ ] P0 Add exact metadata test IDs: `meta-source`, `meta-model`, `meta-latency` (`N ms`), `meta-input-tokens`, `meta-output-tokens`.
- [ ] P0 Make `LIVE_INFERENCE` and `LLM_CACHE` visually distinct.
- [ ] P0 Add the optimistic user bubble, pending indicator, and duplicate-submit guard.
- [ ] P0 On success, append the assistant reply and metadata; scroll to the latest message and restore focus.
- [ ] P0 On failure, remove the optimistic bubble, show a readable inline error with Retry, and keep the composer empty.
- [ ] P1 Add the `system-prompt-input` panel; send its value on every request; empty resets to the default; explain session scope.
- [ ] P1 Add friendly 503, 422, and network error copy; never blank the screen; dismiss the error on a new send.
- [ ] P1 Add accessibility: labels, landmarks, aria-live, focus rings, tab order, contrast, reduced motion.
- [ ] P1 Verify mobile layout and long-conversation scrolling.

### Frontend acceptance

- [ ] P0 Send with both the button and Enter; input is empty immediately after send.
- [ ] P0 Every assistant message has all required test IDs with exact values.
- [ ] P0 Live and cached replies render correctly.
- [ ] P0 503 and network errors are readable and retryable.
- [ ] P1 System prompt persists and resets correctly.
- [ ] P1 Keyboard-only and mobile smoke tests pass.

**Gate 2:** the UI contract is complete against the local backend.

---

## Phase 3 — Testing and hardening (T+11–14)

### Test infrastructure

- [ ] P0 Set up pytest with an async client, app factory, temporary SQLite database per test, and an injected fake LLM gateway.
- [ ] P0 Make the fake gateway support live delays, cache semantics, per-key failures, and usage.
- [ ] P1 Add shared fixtures for settings, client, and seeded sessions.
- [ ] P0 Confirm the test suite makes no real network calls.

### Unit tests

- [ ] P0 Failure-header parser: valid, wildcard, whitespace, duplicates, unknown keys, malformed pairs, invalid statuses, disabled flag.
- [ ] P0 Cache-key builder: same/different model, message, history, prompt, temperature, max tokens; excludes keys, session, simulation.
- [ ] P0 Error classification: 429, quota, 5xx, timeout, connection, authentication, empty reply.
- [ ] P0 Key fallback: order, counts, all-fail, per-attempt timeout.
- [ ] P0 Token and latency normalization.

### API contract tests

- [ ] P0 Health fields and unhealthy 503.
- [ ] P0 Chat success shape, types, non-empty reply, session echo.
- [ ] P0 Validation matrix: missing/empty fields, over-limit message, over-limit system prompt, malformed JSON; nothing persisted.
- [ ] P0 All keys fail: exact 503 and nothing persisted.
- [ ] P0 History: 404, oldest-first order, session isolation, metadata, system prompt excluded.
- [ ] P0 Multi-turn context and separate-session isolation.
- [ ] P0 System prompt: default, override, reset, failure rollback.
- [ ] P0 Failure simulation matrix: single key, multi-key, wildcard, disabled, malformed, real answer.
- [ ] P0 Cache behavior: `LIVE_INFERENCE` then `LLM_CACHE`, identical reply, null key, zero fallback, preserved tokens, faster hit.
- [ ] P0 Cache and simulation interaction: prewarm, then simulate failure and confirm live failover.
- [ ] P0 Errors are JSON with `detail`; no HTML or stack traces.
- [ ] P1 Persistence across app recreation; schema auto-create; metadata round-trip.
- [ ] P1 Concurrent requests in different sessions.

### Frontend verification

- [ ] P0 Run the manual checklist: test IDs, input clearing, live/cache labels, errors, system prompt.
- [ ] P1 Add lightweight component tests for the metadata strip and composer if time remains.

### Real-provider smoke test

- [ ] P0 Verify the final model ID, live usage, real cache hit, both real keys, and the failover header.
- [ ] P0 Re-run the automated suite with no live keys configured.
- [ ] P1 Review coverage; target 80% on backend domain modules, but do not block release on the number.

**Gate 3:** `make test` is green; all P0 tests pass; no known contract gaps.

---

## Phase 4 — Docker and local stack (T+14–17)

- [ ] P0 Backend multi-stage Dockerfile: pinned dependencies, slim runtime, non-root user, `PORT`, health check.
- [ ] P0 Frontend multi-stage Dockerfile: Node build, unprivileged nginx, SPA fallback, gzip, asset caching, build arg for `VITE_API_BASE_URL`.
- [ ] P0 Compose stack: backend on 8000, frontend on 3000, env file, `/data` volume, health checks, dependency ordering.
- [ ] P0 Configure the backend to run exactly one worker/process; document that multi-worker deployment is unsupported.
- [ ] P0 Makefile: `up`, `down`, plus useful `logs`/`test`; `up` checks `.env`; `down` preserves the data volume.
- [ ] P0 Clean `make up` test from a fresh state; both URLs are reachable.
- [ ] P0 Restart persistence test: send messages, restart, confirm history remains.
- [ ] P0 Add `.dockerignore`; confirm no secrets or dev artifacts enter images.
- [ ] P1 Check image sizes and document them.
- [ ] P1 Test and document local run without Docker.

**Gate 4:** a clean checkout with a populated `.env` starts with `make up`; restart keeps history.

---

## Phase 5 — Deployment (T+17–20)

- [ ] P0 Deploy the backend with Docker, one always-on instance, one worker, a persistent volume at `/data`, env vars, and the health check.
- [ ] P0 Set `ENABLE_FAILURE_SIMULATION=true` on the deployed backend.
- [ ] P0 Deploy the frontend static build with `VITE_API_BASE_URL` pointing at the live backend.
- [ ] P0 Set `ALLOWED_ORIGINS` to the exact live frontend origin.
- [ ] P0 Verify the public `/health` shape.
- [ ] P0 Verify live multi-turn chat.
- [ ] P0 Verify a live cache hit in a new session.
- [ ] P0 Verify live failover with `key_1=429`.
- [ ] P0 Verify `*=429` returns 503 and adds nothing to history.
- [ ] P0 Restart the backend and confirm history survives.
- [ ] P0 Verify CORS preflight including `X-Simulate-Failure`.
- [ ] P1 Check cold-start behavior and warm the backend before demos.
- [ ] P1 Record the final live URLs.

**Gate 5:** every deployment verification step passes on public URLs.

---

## Phase 6 — Documentation and demo (T+20–22)

- [ ] P0 README headings: Live URLs, Run locally, Design decisions, Verification, Setup Used, Bonus features.
- [ ] P0 Add the architecture overview, request flow, and API contract summary.
- [ ] P0 Add curl examples for health, chat, history, cache, and failover.
- [ ] P0 Add the environment variable reference and audit `.env.example`.
- [ ] P0 Add the verification guide: cache hit, failover, 503, token metadata, persistence.
- [ ] P0 Document limitations: single instance, in-memory cache reset, anonymous sessions, simulation hook.
- [ ] P0 Check the public repo: no secrets, local databases, build artifacts, or `.env`; README links work.
- [ ] P0 Draft the demo script: live URLs, multi-turn, metadata, cache, failover, 503, history, architecture.
- [ ] P0 Record a 2–3 minute video with voice; verify audio and screen legibility.
- [ ] P1 Add optional screenshots or a short GIF.
- [ ] P1 Proofread the README end to end.

**Gate 6:** README is complete and the demo video is recorded and watchable.

---

## Phase 7 — Final QA, buffer, and submission (T+22–24)

- [ ] P0 Contract audit: endpoint names, methods, fields, statuses, error bodies, and every `data-testid`.
- [ ] P0 Re-run backend tests, `make up`, and the live smoke tests.
- [ ] P0 Confirm no keys in Git history; `.env` is untracked; `.env.example` has placeholders only.
- [ ] P0 Confirm the repository is public and reachable without login.
- [ ] P0 Test the live frontend and backend in an incognito window.
- [ ] P0 Complete the submission form with the frontend URL, backend URL, repository URL, and demo video.
- [ ] P0 Save a backup of the demo video and tag the final commit.
- [ ] P1 Update this TODO and `roadmap.md` with final status.
- [ ] P1 Keep a 30-minute contingency for deployment or cold-start issues.

**Gate 7:** submission is complete and every P0 item is checked.

---

## Definition of done

- [ ] All mandatory API and UI contract items are verified.
- [ ] Failover, cache labeling, per-request tokens, multi-turn history, and SQLite persistence are verified.
- [ ] Docker, Compose, Makefile, and the deployed stack are verified.
- [ ] Backend tests are green and the README is complete.
- [ ] Demo video is recorded and the submission form is completed.

---

## Open decisions and blockers

| Item | Deadline | Status |
|---|---|---|
| Deployment platform with a persistent volume | T+2 | Pending |
| Final Gemini model ID verified through LiteLLM | T+2 | Pending |
| Cache usage preserved on hit, or sidecar needed | T+2 | Pending |
| Final default system prompt copy | T+6 | Pending |
| Demo recording setup and script rehearsal | T+20 | Pending |

---

## Useful commands and checks

```bash
# Local setup
cp .env.example .env
make up
make test

# Health
curl -s "$API_URL/health"

# First request
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s-demo-1","message":"What is the capital of France?"}'

# Repeat the same first message in a new session
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s-demo-2","message":"What is the capital of France?"}'

# Fail over from key_1 to key_2
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: key_1=429" \
  -d '{"session_id":"s-demo-3","message":"Explain failover in one sentence."}'

# Force all keys to fail
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: *=429" \
  -d '{"session_id":"s-demo-4","message":"This should return 503."}'

# Stored history
curl -s "$API_URL/sessions/s-demo-1/messages"
```
