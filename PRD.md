# PRD: Lyftr AI — Resilient LLM Chat with Key Failover and Response Caching

| Field | Value |
|---|---|
| Status | Draft |
| Date | 2026-11-24 |
| Source brief | Lyftr AI Full-Stack Assignment |
| Target | 24-hour build, deployment, and demo |
| Stack | React, FastAPI, LiteLLM, SQLite, Docker |

---

## Problem Statement

People using AI chat products expect a conversation to keep working. In practice, LLM providers rate-limit individual API keys, exhaust free-tier quotas, return transient 5xx errors, and occasionally time out. When an app depends on a single key, one provider hiccup turns into a broken screen, a lost message, or an unhandled exception. Users do not care which key or provider failed; they care that their next message gets an answer.

Users also have no visibility into how an answer was produced. They cannot tell whether a reply was generated live or served from cache, which model answered, how long it took, or how many tokens the request consumed. That opacity makes it hard to trust performance, understand cost, or verify that caching is actually working.

For the team building this, the challenge is to prove that a small full-stack AI application can be resilient, fast, and transparent without adding external infrastructure. The system must fail over automatically across at least two API keys, cache repeated prompts using LiteLLM's built-in cache, persist multi-turn history in SQLite, expose exact per-request metadata, and run both locally with one command and publicly on the internet.

## Solution

Build a full-stack chat application called Lyftr AI:

- A polished React chat interface for multi-turn conversations, with an optional per-session system prompt and a metadata strip under every assistant reply.
- A FastAPI backend that owns session history, validates every request, and exposes exactly the required API contract.
- A LiteLLM gateway configured with at least two Google Gemini API keys. Each request attempts keys in a deterministic order and automatically fails over on rate limits, quota errors, 5xx responses, timeouts, and other provider failures. If every key fails, the user gets a clean, readable 503 rather than a crash.
- LiteLLM's in-memory response cache, keyed by the model plus the full prompt (system prompt, stored history, and new message). Cache hits are labeled `LLM_CACHE`, return the identical reply and stored token usage, report no key, and return faster than live calls.
- SQLite storage for sessions and messages, mounted on a Docker volume so history survives container restarts. The schema is created automatically at startup.
- A failure-simulation hook so failover can be demonstrated on demand without exhausting real quotas. Requests with an active simulation directive bypass the response cache so the failover behavior is always visible.
- Multi-stage Dockerfiles, Docker Compose, a Makefile with `up` and `down`, environment-only configuration, a complete README, and a backend test suite covering the contract.

The result is a deployable, single-instance application that stays usable when a key fails, answers repeated prompts instantly, remembers the active conversation, and shows exactly how each reply was produced.

---

## User Stories

### Chat experience

1. As a visitor, I want the chat interface to load ready to use, so that I can start a conversation without setup.
2. As a visitor, I want each page load to start a fresh session, so that conversations do not leak between visits.
3. As a visitor, I want to type a message and press Enter or click Send, so that I can chat naturally.
4. As a visitor, I want Shift+Enter to insert a newline, so that I can write multi-line messages.
5. As a visitor, I want the input cleared immediately after a message is sent, so that I can type my next message right away.
6. As a visitor, I want to see my messages and assistant replies in chronological order, so that I can follow the conversation.
7. As a visitor, I want a visible loading indicator while a reply is pending, so that I know the request is in progress.
8. As a visitor, I want the Send button disabled for empty or whitespace-only input, so that I cannot submit invalid messages.
9. As a visitor, I want a character counter and a 4,000-character limit, so that I know the maximum message size before I hit it.
10. As a visitor, I want long conversations to scroll smoothly and keep the latest message in view, so that I do not lose my place.

### Metadata and transparency

11. As a visitor, I want to see whether each reply came from live inference or cache, so that I understand how the answer was produced.
12. As a visitor, I want to see the exact model that answered, so that I know which model produced the reply.
13. As a visitor, I want to see per-reply latency in milliseconds, so that I can judge responsiveness.
14. As a visitor, I want to see input and output tokens for each reply, so that I can understand per-request usage.
15. As a visitor, I want token counts to describe only the current request, never a running conversation total, so that the numbers stay meaningful.
16. As a visitor, I want cached replies to be visually distinct from live replies, so that I can spot a cache hit at a glance.
17. As a visitor, I want cached replies to repeat the exact original answer, so that repeated questions are consistent.
18. As a visitor, I want cached replies to return faster than live calls, so that repeat questions feel instant.

### System prompt

19. As a visitor, I want an optional system prompt field, so that I can steer the assistant's behavior for my session.
20. As a visitor, I want my system prompt to persist across turns in the session, so that I do not have to re-enter it.
21. As a visitor, I want to change the system prompt mid-session, so that I can adjust the assistant's behavior.
22. As a visitor, I want clearing the system prompt to restore the default behavior, so that I can reset my session instructions without reloading.
23. As a visitor, I want a clear explanation that the system prompt is per-session, so that I understand its scope.
24. As a visitor, I want the system prompt to be excluded from the visible message history, so that the transcript stays clean.

### Reliability and failover

25. As a visitor, I want the app to keep answering when the first API key is rate-limited, so that a provider quota issue does not break my conversation.
26. As a visitor, I want automatic failover when a key returns a quota, 5xx, timeout, connection, or authentication error, so that transient provider problems are invisible to me.
27. As a visitor, I want a readable message if every key fails, so that I am never left with a blank screen or a stack trace.
28. As a visitor, I want a failed request to leave no partial turn in history, so that retries and later turns behave correctly.
29. As a visitor, I want a retry action after a failure, so that I can recover without retyping.
30. As a developer, I want a failure-simulation header, so that I can demonstrate failover without burning real quota.
31. As a developer, I want simulated failures to affect only the current request, so that real key health is not changed.
32. As a developer, I want simulation to be switchable by environment variable, so that it can be disabled outside evaluation.
33. As a developer, I want the successful key id and number of failed attempts in the response metadata, so that I can verify failover.
34. As a developer, I want simulated-failure requests to bypass the cache, so that the expected failover result is deterministic even for repeated prompts.
35. As a developer, I want a simulated request to return a real answer from the next key, never an error wrapped in a 200, so that the demo is honest.

### Caching

36. As a developer, I want the cache key to include the model and the full prompt, so that different questions or system prompts never collide.
37. As a developer, I want the same first message in a new session to hit the cache, so that caching works across sessions.
38. As a developer, I want a cache hit to report `LLM_CACHE`, a null key id, and zero fallback attempts, so that metadata matches the contract.
39. As a developer, I want a cache hit to reuse the token usage stored with the original response, so that token metadata stays accurate.
40. As a developer, I want cache hits to be measurably faster than live inference, so that the performance benefit is demonstrable.
41. As a developer, I want cache entries to expire after a configurable TTL, so that memory use is bounded.
42. As a developer, I want the health endpoint to report that caching is enabled, so that deployment checks can confirm it.

### History and multi-turn state

43. As a visitor, I want the assistant to remember earlier messages in the session, so that follow-up questions make sense.
44. As a visitor, I want separate session IDs to stay isolated, so that my conversation never mixes with another session.
45. As a developer, I want session history stored in SQLite, so that it survives process and container restarts.
46. As a developer, I want the history endpoint to return messages oldest first without the system prompt, so that clients can reconstruct the transcript.
47. As a developer, I want an unknown session to return 404, so that missing sessions are distinguishable from empty ones.
48. As a developer, I want the schema created automatically on startup, so that deployment needs no manual migration step.
49. As a developer, I want failed requests not to create sessions or messages, so that storage reflects only successful exchanges.

### Operations, deployment, and quality

50. As an operator, I want a health endpoint that checks the database, key pool, and cache, so that I can verify readiness.
51. As an operator, I want every configuration value supplied through environment variables, so that secrets and URLs are never hardcoded.
52. As an operator, I want the stack to start with one command, so that local review and demos are fast.
53. As an operator, I want multi-stage, small Docker images with non-root runtime users, so that deployment is fast and secure.
54. As an operator, I want SQLite data on a named volume, so that history survives restarts.
55. As an operator, I want CORS restricted to the configured frontend origins, so that only approved clients can call the API.
56. As a reviewer, I want public frontend and backend URLs, so that I can test the deployed system without logging in.
57. As a reviewer, I want a README with live URLs, local run steps, design decisions, and verification instructions, so that I can validate every criterion quickly.
58. As a reviewer, I want a 2–3 minute demo video showing chat, cache hits, and failover, so that I can see the system working end to end.
59. As a security-minded operator, I want API keys and stack traces never exposed to clients or logs, so that the public deployment is safe.
60. As a product owner, I want the implementation to match the API and UI contract exactly, so that automated checks pass without workarounds.
61. As a developer, I want backend tests for validation, failover, caching, token metadata, and persistence, so that regressions are caught before deployment.
62. As a developer, I want tests to run without live API keys, so that the suite is deterministic and safe to run anywhere.

---

## Implementation Decisions

### Architecture overview

The request path is:

1. The browser creates a new session ID on page load and sends `POST /chat` with the session ID, message, and optional system prompt.
2. FastAPI validates the request, acquires a per-session lock, and loads the stored system prompt and message history from the SQLite repository.
3. The chat service builds the full message list: effective system prompt, prior user/assistant turns, and the new user message.
4. The LLM gateway computes the cache key and invokes LiteLLM with caching enabled. LiteLLM checks the cache before contacting a provider, so a hit returns without inference; otherwise the gateway attempts each configured key in order until one succeeds.
5. On success, the chat service writes the user message and assistant message in one SQLite transaction, including the assistant metadata JSON.
6. The API returns the reply and per-request metadata. On failure, it returns the contract error and writes nothing.

The application runs as a single backend process. This is deliberate: LiteLLM's in-memory cache and the per-session locking are process-local, and SQLite is the only allowed store. The deployment must not scale the backend to multiple instances or workers.

### Modules to build

| Module | Responsibility | Conceptual interface |
|---|---|---|
| Configuration and startup | Load and validate environment settings; initialize the cache; create the database schema; fail fast on invalid configuration. | Typed settings object; validated key pool; initialized cache; schema ready. |
| Failure-simulation parser | Parse `X-Simulate-Failure` into a request-scoped map of key IDs to status codes. | Given the raw header and the configured key IDs, return a map of simulated failures. Malformed directives are ignored; `*` expands to all keys. |
| LLM gateway and key pool | Own all LiteLLM interaction, cache lookup, key iteration, failure classification, and metadata extraction. | Given a full message list and a simulation map, return a result containing reply, source, model, key ID, fallback count, latency, and token usage. Raise a single domain error when every key fails. |
| Cache-key builder | Produce a deterministic cache key from the model, full message list, and generation parameters, excluding API keys, key IDs, session IDs, and simulation state. | Given model, messages, and parameters, return a stable key. |
| Chat service | Orchestrate validation, session locking, context assembly, prompt persistence, gateway calls, atomic persistence, and response metadata. | Given session ID, message, optional system prompt, and simulation map, return a chat result or a domain error. |
| Session repository | Own all SQLite access and transaction boundaries. | Read stored system prompt; read ordered history; persist a successful exchange atomically; check database health. |
| API layer | Expose the three required routes, enforce Pydantic validation, configure CORS, and translate domain errors into exact JSON responses. | HTTP endpoints and JSON shapes defined below. |
| Frontend API client | Call the backend, normalize errors, and expose typed chat and metadata models. | Send chat request; parse success or error; never expose credentials. |
| Chat UI | Manage session state, system prompt, transcript, composer, pending state, errors, and metadata display. | React components with the required `data-testid` hooks. |
| Design system | Define the visual language, tokens, message cards, badges, spacing, and responsive behavior. | Tailwind-based theme and reusable presentation components. |
| Operations assets | Dockerfiles, Compose, Makefile, environment template, README, and test commands. | One-command local stack and reproducible deployment. |

The LLM gateway is the deepest module. It hides cache semantics, provider errors, key ordering, timeouts, simulation, and usage normalization behind one small result type. The repository is the second deep module: the rest of the app never sees SQL.

### Provider and model choice

- Use Google Gemini through LiteLLM, with at least two API keys in the pool.
- The default model is a current stable Gemini Flash-Lite model, initially `gemini/gemini-3.5-flash-lite`, chosen for low latency and cost. The exact model ID is configurable through `LLM_MODEL`.
- Gemini 2.0 Flash, used in the assignment example, is retired and must not be used. Gemini 2.5 Flash is deprecated and should also be avoided.
- Before implementation is considered complete, verify the chosen model ID works through the installed LiteLLM version and the Gemini API. If not, switch to the nearest stable Flash/Flash-Lite model without changing application behavior.
- Use two keys from separate Google AI Studio projects where possible, so a shared project quota cannot take down both keys at once.
- The model name returned to the frontend is the LiteLLM model string from configuration, such as `gemini/gemini-3.5-flash-lite`.

### Key pool and failover policy

- Keys are parsed from `LLM_API_KEYS` in order and assigned IDs `key_1`, `key_2`, and so on. At least two keys are required; startup fails with a clear error if fewer are present.
- Each request starts at `key_1` and walks the pool in order. This is deterministic, easy to reason about, and makes failover demonstrations predictable. Load spreading across keys is explicitly out of scope.
- Each key gets one attempt per request. The gateway does not retry the same key, and LiteLLM's own retry layer is disabled per attempt so fallback counts and simulated failures stay exact.
- Failover-eligible failures include HTTP 429, quota or billing exhaustion, all 5xx responses, request timeouts, connection failures, authentication failures, and empty or whitespace-only completions. The gateway uses LiteLLM's typed exceptions rather than parsing error strings.
- A per-attempt timeout and an overall request budget are enforced so a slow provider cannot hang the request indefinitely. Defaults are 30 seconds per attempt and 60 seconds overall, configurable by environment.
- `fallback_attempts` is the number of keys that failed before the successful key. A direct `key_1` success reports 0. A success on `key_2` after `key_1` failed reports 1.
- On success, metadata reports the successful key ID, never the key itself. On a cache hit, `key_id` is null and `fallback_attempts` is 0.
- If every key fails, the gateway raises one domain error. The API maps it to HTTP 503 with the exact body `{"detail": "all providers unavailable"}`. Nothing is persisted.
- LiteLLM is the provider gateway and cache. The ordered key-fallback policy is a thin application layer around LiteLLM because it needs deterministic per-key identity, exact fallback counts, and request-scoped failure simulation. LiteLLM's Router was considered but rejected for this assignment: its deployment selection and retry internals do not expose per-key identity and simulation hooks cleanly enough to satisfy the contract.

### Response caching

- Enable LiteLLM's built-in in-memory cache at startup. `cache_enabled` is true in the health response. No Redis, disk service, or external cache is used.
- Use an explicit custom cache key instead of LiteLLM's default key generation. The key is a stable hash of the model, full message list (system prompt plus history plus new message), and generation parameters that affect output (at minimum temperature and max output tokens). API keys, key IDs, session IDs, and failure-simulation state are excluded.
- This guarantees that the same first message in a new session hits the cache, while a different message, different history, or different system prompt misses.
- LiteLLM performs the cache read before it contacts a provider. On a hit, no inference call is made; the reply text is identical to the original; token usage is taken from the cached response; `resolution_source` is `LLM_CACHE`; `key_id` is null; `fallback_attempts` is 0. The gateway normalizes these cache-hit values even if an earlier key attempt in the same request had already failed.
- Cache hits must be measurably faster than live calls. Automated tests inject a delay into the fake gateway to prove the ordering without relying on real network timing.
- Requests with an active failure-simulation directive bypass both cache reads and cache writes. This guarantees that `key_1=429` still demonstrates failover on a previously cached prompt, and `*=429` still returns 503 rather than a cached success.
- Cache entries expire after a configurable TTL, default 1 hour, to bound memory. The cache resets on process restart; that is acceptable for this assignment and documented.
- Use LiteLLM's documented cache-hit signal, captured per request, to set `resolution_source`. Do not infer cache hits from latency.
- Verify early that LiteLLM preserves token usage in cached responses. If it does not, store a small usage sidecar in SQLite keyed by the same cache key, without replacing LiteLLM's cache.

### Data model and persistence

Add a sessions table in addition to the required messages table.

**sessions**

| Column | Type | Notes |
|---|---|---|
| `session_id` | TEXT, primary key | Client-generated, 1–128 characters. |
| `system_prompt` | TEXT, nullable | Effective system prompt for the session. Never returned in history. |
| `created_at` | TEXT, not null | UTC ISO-8601. |
| `updated_at` | TEXT, not null | UTC ISO-8601, updated on each successful exchange. |

**messages**

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER, primary key, autoincrement | Defines chronological order. |
| `session_id` | TEXT, not null, indexed | References the sessions table. |
| `role` | TEXT, not null | `user` or `assistant`. |
| `content` | TEXT, not null | Trimmed user message or assistant reply. |
| `metadata` | TEXT, nullable | JSON string, assistant messages only. |
| `created_at` | TEXT, not null | UTC ISO-8601. |

- Add an index on `(session_id, id)` for history reads.
- Enable SQLite WAL mode, foreign keys, and a busy timeout.
- Store assistant metadata with all fields needed to reproduce the history response: resolution source, model, latency, input tokens, output tokens, key ID, and fallback attempts.
- Persist the user message and assistant message, plus the session row and effective system prompt, in a single transaction. If anything fails, roll back the entire exchange.
- Never persist a request that returns 422, 503, or 500. A session row is created only by the first successful exchange.
- Use parameterized SQL through SQLAlchemy 2.0's async engine with the `aiosqlite` driver. Honor the `sqlite:////data/app.db` URL format directly.
- Create the schema automatically at startup. No migration framework is needed for this scope.
- Store timestamps in UTC and return them only where useful; the public API does not require timestamps.

### Session and system-prompt semantics

- The client generates a new session ID on each page load, using a UUID-based identifier prefixed with `s-` and kept under 128 characters.
- An unknown session ID starts a new session on the first successful chat request.
- On the first successful exchange, the effective system prompt is the trimmed value supplied by the client if non-empty, otherwise the configured default system prompt. It is stored on the session row.
- On later requests, an omitted `system_prompt` field means "use the stored prompt." A non-empty value replaces the stored prompt for the session. An explicitly empty or whitespace-only value resets the session to the default system prompt.
- A prompt change is persisted atomically with the successful exchange. A failed request does not change the stored prompt.
- The history endpoint never returns the system prompt.
- The full stored history is sent to the model on each turn. Message content is limited to 4,000 characters; no additional history truncation is required for this assignment.
- A per-session async lock serializes simultaneous chat requests in the same session so history order is deterministic. Different sessions can proceed in parallel.
- Sessions are anonymous. Anyone who knows a session ID can read its history. ID unguessability is the only protection; authentication is out of scope.

### API contract

The backend exposes exactly these routes under its base URL. All request and response bodies are JSON. Extra response fields are allowed; required fields must never be missing or renamed. Disable FastAPI's generated documentation routes (`/docs`, `/redoc`, and `/openapi.json`) in deployed environments so the public API surface contains only the three contract routes; they may remain enabled in local development if desired.

#### `GET /health`

Return 200 only when the app is running, the database responds to a health query, the key pool has at least two keys, and the cache is initialized.

```json
{
  "status": "ok",
  "keys_configured": 2,
  "cache_enabled": true
}
```

If any readiness condition fails, return 503 with a JSON `detail` field. Never return HTML.

#### `POST /chat`

Request:

```json
{
  "session_id": "s-7f3a",
  "message": "What is the capital of France?",
  "system_prompt": "Answer concisely."
}
```

| Field | Type | Rule |
|---|---|---|
| `session_id` | string | Required, 1–128 characters. Unknown IDs start a new session. |
| `message` | string | Required, 1–4,000 characters after trimming whitespace. |
| `system_prompt` | string | Optional. Non-empty values override the session prompt; empty values reset to the default. Maximum 4,000 characters after trimming. |

Success response, 200:

```json
{
  "session_id": "s-7f3a",
  "reply": "The capital of France is Paris.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-3.5-flash-lite",
    "latency_ms": 812,
    "input_tokens": 42,
    "output_tokens": 9,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

| Metadata field | Type | Meaning |
|---|---|---|
| `resolution_source` | string | Exactly `LIVE_INFERENCE` or `LLM_CACHE`. |
| `model` | string | LiteLLM model name that produced the reply. |
| `latency_ms` | integer | Server-measured request time in milliseconds. |
| `input_tokens` | integer | Prompt tokens for this request only: system prompt, history, and new message. |
| `output_tokens` | integer | Completion tokens for this reply only. |
| `key_id` | string or null | Answering key ID such as `key_1`; null on cache hits. Never the key value. |
| `fallback_attempts` | integer | Keys that failed before success; 0 on cache hits. |

`reply` must always be non-empty on a 200. An empty provider completion is treated as a failed attempt.

#### `GET /sessions/{session_id}/messages`

Return the stored history of one session, oldest first, without the system prompt.

```json
{
  "session_id": "s-7f3a",
  "messages": [
    {
      "role": "user",
      "content": "What is the capital of France?"
    },
    {
      "role": "assistant",
      "content": "The capital of France is Paris.",
      "metadata": {
        "resolution_source": "LIVE_INFERENCE",
        "model": "gemini/gemini-3.5-flash-lite",
        "latency_ms": 812,
        "input_tokens": 42,
        "output_tokens": 9,
        "key_id": "key_1",
        "fallback_attempts": 0
      }
    }
  ]
}
```

- Return 404 with `{"detail": "session not found"}` for an unknown session.
- User messages include only `role` and `content`. Assistant messages include `role`, `content`, and `metadata`.
- The history endpoint never creates a session and never includes the system prompt.

#### Errors

Every error is JSON with a `detail` field. No stack trace, HTML error page, or raw provider response is ever returned.

| Case | Status | Body |
|---|---:|---|
| Missing or empty `session_id` or `message`, message over 4,000 characters, system prompt over 4,000 characters, malformed JSON | 422 | FastAPI's default validation shape with `detail` |
| Every key failed or timed out | 503 | `{"detail": "all providers unavailable"}` |
| Unknown session in history lookup | 404 | `{"detail": "session not found"}` |
| Unexpected internal error | 500 | `{"detail": "internal server error"}` |

A request that fails for any reason is not added to session history.

#### Failure simulation header

`POST /chat` accepts `X-Simulate-Failure`:

- Format: comma-separated `<key_id>=<status>` pairs.
- `*` means every configured key.
- Allowed statuses: `429`, `500`, `502`, `503`.
- Whitespace around pairs and values is tolerated.
- Unknown key IDs and malformed directives are ignored; if no valid directives remain, the header has no effect.
- If a key appears more than once, the last valid directive wins.
- The header is honored only when `ENABLE_FAILURE_SIMULATION=true`. Otherwise it is ignored completely.
- Each directive is scoped to the current request only. It never changes stored key state or any other request.
- A simulated failure counts as an attempt and increments `fallback_attempts`. The next healthy key must return a real completion.
- If every key is simulated as failing, return 503 with the exact all-providers-unavailable body and persist nothing.
- Any request with at least one valid active simulation directive bypasses cache reads and writes.

Expected results with two configured keys:

| Header | Expected result |
|---|---|
| `key_1=429` | 200 from `key_2`, `fallback_attempts` 1 |
| `key_1=500` | 200 from `key_2`, `fallback_attempts` 1 |
| `key_1=429,key_2=500` | 503, nothing persisted |
| `*=429` | 503, nothing persisted |
| Header sent while simulation is disabled | Header ignored; normal behavior |

A simulated request must return a real answer, never an error message wrapped in a 200.

#### CORS

- Read allowed origins from `ALLOWED_ORIGINS` as a comma-separated list.
- Allow `GET`, `POST`, and `OPTIONS`.
- Allow the `Content-Type` and `X-Simulate-Failure` request headers. The custom header must survive preflight.
- Do not use wildcard origins in the deployed environment.
- No credentials or cookies are used.

### Latency and token accounting

- Measure latency with a monotonic clock from the start of chat handling (including any per-session lock wait) to immediately before the response is returned, including cache lookup, provider attempts, and the SQLite write.
- Return latency as an integer number of milliseconds.
- Cache hits must still be faster than live calls in practice; they avoid the provider round trip.
- Normalize provider usage into `input_tokens` and `output_tokens`. Use LiteLLM's canonical usage fields; do not estimate from characters.
- Input tokens include the effective system prompt, all stored history, and the new user message.
- Token values are per request, never cumulative.
- On a cache hit, return the usage stored with the cached response.
- If a provider omits usage, return 0 for the missing field and log a warning; do not substitute conversation totals.

### Frontend experience

**Stack and design direction**

- React with Vite and TypeScript, styled with Tailwind CSS.
- A calm, editorial chat workspace rather than a generic purple-gradient AI page: warm off-white canvas, ink-black text, a signal-green accent for live inference, and a warm amber accent for cache hits.
- A compact product header with the Lyftr AI name and a subtle live-session indicator.
- Assistant replies in soft bordered cards; user messages in a solid accent-tinted bubble aligned to the right.
- Metadata as a quiet monospace strip below each assistant reply, readable but visually secondary.
- A sticky composer at the bottom with a character counter and a clear Send button.
- A collapsible "Session instructions" panel above the transcript for the system prompt.
- Responsive down to small mobile widths; comfortable spacing and readable line lengths on desktop.
- Light theme only. Dark mode is out of scope.

**Session and request lifecycle**

- Generate a new session ID on each page load. Do not restore sessions across reloads.
- Keep the transcript only in memory.
- On send: trim the message, reject empty input, clear the input immediately, append an optimistic user message, disable the composer, and show a pending indicator.
- On success: mark the user message delivered and append the assistant reply with its metadata.
- On failure: remove the optimistic user bubble so the visible transcript matches stored history, and show an inline error card with a friendly message, the server `detail` when useful, and a Retry action. The composer stays empty. Retry resends the same text.
- A new send dismisses the previous error card.
- Never render an error as an assistant success message.
- Scroll to the latest message after each turn and return focus to the composer.
- Prevent duplicate submissions while a request is in flight.

**Input behavior**

- Use a textarea that grows with content up to a reasonable height.
- Enter sends; Shift+Enter inserts a newline.
- Enforce a 4,000-character maximum and show a counter.
- Send is disabled when the trimmed value is empty or a request is pending.
- Show a concise hint for keyboard behavior.

**System prompt behavior**

- The panel starts collapsed or subtly visible, with helper text explaining that it applies only to the current session.
- The field value is sent with every chat request, including when empty. Empty means "reset to the default prompt" and non-empty means "use this prompt for the session."
- The backend persists the effective prompt for later turns.
- The panel should explain that changes apply from the next message onward.
- The history transcript never displays the system prompt as a message.

**Required UI contract**

Each assistant reply is wrapped in an element with `data-testid="assistant-message"`. Inside it:

| `data-testid` | Element | Required content |
|---|---|---|
| `assistant-message` | Container of each assistant reply | Reply text plus all metadata elements below |
| `meta-source` | Inside each assistant message | Exactly `LIVE_INFERENCE` or `LLM_CACHE` |
| `meta-model` | Inside each assistant message | The exact `model` value |
| `meta-latency` | Inside each assistant message | Latency formatted like `812 ms` |
| `meta-input-tokens` | Inside each assistant message | The `input_tokens` integer |
| `meta-output-tokens` | Inside each assistant message | The `output_tokens` integer |
| `chat-input` | Text input or textarea | Empty immediately after sending |
| `send-button` | Send button | Sends the message |
| `system-prompt-input` | System prompt field | Present because the feature is built |

Additional test IDs, such as `user-message`, `error-message`, or `loading-indicator`, are allowed. The required elements must contain exactly the specified values; put labels such as "In" or "Out" outside the numeric elements so tests can read plain integers.

**Error presentation**

- 503: "All AI providers are unavailable right now. Please try again in a moment." with a Retry action.
- 422: show the validation detail in readable form; the UI should normally prevent this case.
- Network or unexpected error: a generic connection message with Retry.
- Errors must never blank the screen or replace the transcript.

**Accessibility**

- Label the chat input and system prompt field.
- Use semantic landmarks and buttons.
- Announce new assistant messages with a polite live region.
- Maintain visible focus rings and logical tab order.
- Ensure color contrast for metadata labels and badges.
- Respect reduced-motion preferences for non-essential animation.
- Errors are announced and associated with the failed action.

### Configuration

All configuration is supplied through environment variables. The backend validates required settings at startup and fails fast with an actionable message.

**Backend**

| Variable | Required | Default | Meaning |
|---|---:|---|---|
| `LLM_API_KEYS` | Yes | none | Comma-separated Gemini keys; at least 2. Key IDs follow order. |
| `LLM_MODEL` | No | `gemini/gemini-3.5-flash-lite` | LiteLLM model string. |
| `DATABASE_URL` | Yes | `sqlite:////data/app.db` in Docker | SQLite URL. |
| `ALLOWED_ORIGINS` | Yes | `http://localhost:3000` | Comma-separated CORS origins. |
| `ENABLE_FAILURE_SIMULATION` | No | `false` | Enables the failure-simulation header. |
| `DEFAULT_SYSTEM_PROMPT` | No | A concise helpful-assistant prompt | Used when a session has no override. |
| `CACHE_TTL_SECONDS` | No | `3600` | LiteLLM in-memory cache TTL. |
| `KEY_ATTEMPT_TIMEOUT_SECONDS` | No | `30` | Timeout per key attempt. |
| `REQUEST_TIMEOUT_SECONDS` | No | `60` | Overall provider budget. |
| `LLM_TEMPERATURE` | No | `0.2` | Generation temperature, part of the cache key. |
| `LLM_MAX_OUTPUT_TOKENS` | No | `1024` | Completion cap, part of the cache key. |
| `LOG_LEVEL` | No | `INFO` | Application log level. |
| `PORT` | No | `8000` | HTTP port inside the backend container. |

**Frontend**

| Variable | Required | Default | Meaning |
|---|---:|---|---|
| `VITE_API_BASE_URL` | Yes in deployed builds | `http://localhost:8000` locally | Backend base URL baked into the frontend build. |

- `.env.example` lists every variable with safe placeholder values.
- Real keys never appear in the repository, build output, frontend bundle, logs, or API responses.
- The deployed backend sets `ENABLE_FAILURE_SIMULATION=true` as required by the assignment.

### Docker and local orchestration

- **Backend image:** multi-stage build. The builder stage installs pinned Python dependencies; the runtime stage copies only the virtual environment and application code, uses a slim base, creates and runs as a non-root user, exposes the configured port, and includes a health check against `/health`.
- **Frontend image:** multi-stage build. The Node stage installs dependencies and runs the production build with `VITE_API_BASE_URL`; the runtime stage serves static assets from a small unprivileged nginx image with SPA fallback, gzip, and long-lived asset caching.
- **Compose:** runs both services, publishes backend on `localhost:8000` and frontend on `localhost:3000`, passes environment variables, mounts a named volume at `/data`, and waits for the backend health check. The frontend build argument defaults to the local backend URL.
- **Persistence:** the SQLite file lives under `/data`, configured through `DATABASE_URL`, so history survives container recreation.
- **Makefile:** `make up` validates that `.env` exists, builds and starts the stack in the background, and prints both local URLs. `make down` stops the stack without deleting the data volume. Helpful targets such as `logs` and `test` may be added; `up` and `down` are mandatory.
- **Local without Docker:** documented backend virtual-environment setup, migrations-on-startup, and frontend dev server. The database defaults to a local file when not running in Compose.
- All configuration flows through environment variables; Compose defaults are safe for local use.

### Deployment

The exact platform is decided during implementation, using this checklist:

- Backend supports container deployment and matches the Docker image.
- A persistent volume can be mounted at `/data`, because SQLite history must survive restarts.
- The backend runs as a single always-on instance; no autoscaling, multiple replicas, or multiple workers.
- Public HTTPS URL with no login.
- Environment variables and secrets are configured in the platform dashboard, never committed.
- Health checks target `/health`.
- Frontend is deployed as a static site with `VITE_API_BASE_URL` set to the live backend URL.
- `ALLOWED_ORIGINS` contains the exact live frontend origin, with no wildcard.
- The free tier is sufficient or the cost is acceptable for the evaluation window.

Candidate combinations are Fly.io or Railway for the backend with a persistent volume, and Vercel, Netlify, or Cloudflare Pages for the frontend. Render is acceptable only if its plan provides a persistent disk and avoids scale-to-zero during evaluation.

Deployment verification:

- Load the live frontend and complete a multi-turn conversation.
- Confirm metadata appears for every reply.
- Repeat a first message in a new session and confirm `LLM_CACHE`, identical text, null key, and lower latency.
- Use `X-Simulate-Failure` to confirm `key_1=429` succeeds on `key_2` and `*=429` returns 503.
- Restart the backend and confirm history survives via the history endpoint.
- Confirm CORS preflight succeeds from the deployed frontend origin, including the simulation header.
- Warm the backend before the demo to avoid cold-start delays.

### Observability, security, and error handling

- Log one structured record per chat request: request ID, session ID, resolution source, model, key ID, fallback count, latency, token counts, and outcome. Never log message content, system prompts, API keys, or raw provider payloads.
- Log key IDs only, never key values.
- Redact provider errors before logging if they might contain credentials.
- Use a global exception handler that logs the server-side traceback but returns `{"detail": "internal server error"}` to the client.
- Keep FastAPI's default 422 shape for validation errors; ensure malformed JSON also produces JSON, not HTML.
- Validate all input lengths before any provider or database work.
- Use parameterized queries; never interpolate user input into SQL.
- Restrict CORS to configured origins and explicitly allow the simulation header.
- Enforce a per-attempt and overall timeout so failover cannot hang indefinitely.
- Do not expose provider keys through response fields, logs, health checks, or the frontend bundle.
- Session IDs are unguessable UUIDs, but there is no authentication; document this as an assignment-scope limitation.
- The failure-simulation header is intentionally unauthenticated while enabled; document that it is an evaluation hook and can be disabled by environment variable.

### Documentation and deliverables

The README must use the required headings:

1. **Live URLs**
2. **Run locally** (with Docker and without)
3. **Design decisions** (key fallback, caching, SQLite session storage)
4. **Verification** (how to see failover, cache hits, and per-message token usage)
5. **Setup Used** (editor and AI tools)
6. **Bonus features** (system prompt field and why it was added)

Also include:

- Architecture overview and request flow.
- Complete API contract summary with curl examples for `/health`, `/chat`, the history endpoint, and failure simulation.
- Environment variable reference.
- Testing commands and coverage summary.
- Deployment notes and the persistent-volume rationale.
- Known limitations: single instance, in-memory cache resets on restart, anonymous sessions, simulation hook.
- A short demo-video checklist.

`.env.example` must include every variable with placeholders and no real secrets.

---

## Testing Decisions

### What makes a good test

A good test exercises observable behavior through a stable boundary: HTTP status codes, response JSON, database contents, cache-source labels, and failover outcomes. It does not assert internal call order beyond the documented key-attempt policy, inspect private methods, or depend on real provider responses. Tests must be deterministic, run without network access or live API keys, and use isolated temporary databases.

### Test layers

**1. Pure unit tests**

- Failure-header parsing: single key, multiple keys, wildcard, whitespace, duplicate keys, unknown keys, malformed pairs, invalid status codes, disabled flag.
- Cache-key construction: same model and messages produce the same key; a different message, history, system prompt, model, temperature, or max-token setting produces a different key; API keys, key IDs, session IDs, and simulation state do not affect the key.
- Error classification: rate limit, quota, 5xx, timeout, connection, authentication, and empty completion are failover-eligible.
- Key-pool fallback: ordered attempts, success on the second key, counts, all-fail domain error, per-attempt timeout.
- Token and latency normalization: integer values, cached usage preserved, per-request semantics.

**2. API contract tests**

Use FastAPI's test client or an ASGI transport with a temporary SQLite file and an injected fake LLM gateway. Cover:

- `GET /health`: exact required fields; 200 when healthy; 503 when the database check or key pool is unavailable.
- `POST /chat` success: exact top-level shape, non-empty reply, all metadata fields and types, session ID echo.
- Validation: missing session, missing message, empty and whitespace-only message, 4,001-character message, 4,001-character system prompt, malformed JSON; all return 422 JSON and persist nothing.
- All keys fail: exact 503 detail, no user or assistant message stored, no session created.
- History: unknown session returns 404; known session returns oldest-first messages; system prompt is absent; assistant metadata is present; user messages have no metadata; sessions are isolated.
- Multi-turn: a follow-up request receives prior history in the prompt; separate sessions do not leak into each other.
- System prompt: default applies when absent; non-empty override persists; empty value resets to default; changes are not persisted on failure; history excludes it.
- Failure simulation: `key_1=429` succeeds on `key_2`; `key_1=500` succeeds on `key_2`; both fail returns 503; `*=429` returns 503; header ignored when disabled; malformed header ignored; simulated request returns a real reply.
- Cache behavior: first request is `LIVE_INFERENCE`; an identical first message in a new session is `LLM_CACHE` with identical reply, null key, zero fallback attempts, and preserved tokens; a different message is live; a system-prompt change forces a miss; cache hits are faster when the fake gateway includes a live-call delay.
- Cache and simulation interaction: prewarm a prompt, then send it with `key_1=429` and confirm a live `key_2` response rather than a cache hit.
- Error handling: no HTML responses, no stack traces, and all failure bodies have `detail`.

**3. Persistence tests**

- Recreate the app against the same temporary SQLite file and confirm history survives.
- Confirm the schema is created automatically in an empty database.
- Confirm failed requests leave no session, message, or prompt change.
- Confirm assistant metadata round-trips through JSON storage.

**4. Frontend verification**

Automated frontend E2E is not part of the core suite. Verify manually with a checklist:

- Send a message with the button and with Enter; Shift+Enter inserts a newline.
- Input is empty immediately after send.
- Every assistant reply contains all required `data-testid` elements with exact values.
- Cache hits show `LLM_CACHE`; live replies show `LIVE_INFERENCE`.
- Latency renders as `N ms`; token elements contain plain integers.
- 503 and network errors show readable inline errors with Retry; the transcript stays usable.
- System prompt applies to later turns and can be reset.
- Layout works at mobile and desktop widths; keyboard focus and live-region announcements work.

### Real-provider verification

The automated suite uses a fake gateway at the LiteLLM boundary. Separately, run a manual smoke test against the real Gemini API to confirm:

- The configured model ID is accepted.
- Usage values are populated.
- LiteLLM's in-memory cache returns an identical reply with a cache-hit signal.
- Two real keys both work and failover can be triggered with the simulation header.

This manual smoke test is documented in the README and repeated against the deployed backend.

### Prior art

The repository is greenfield, so this suite establishes the project's testing conventions: an application factory with injected settings, a fake LLM gateway, a temporary SQLite database per test, and HTTP-level assertions. Future tests should follow those patterns rather than introduce global state or live-network dependencies.

### Test commands and targets

- `make test` runs the backend suite locally.
- Tests are also runnable inside the backend container.
- Target meaningful coverage of the gateway, chat service, repository, validation, and API layers; 80% or higher on backend domain modules is a reasonable goal, not a hard gate.

---

## Out of Scope

- User accounts, authentication, authorization, and multi-tenant isolation beyond unguessable session IDs.
- A session sidebar, conversation list, history restore across reloads, or session deletion/export.
- Streaming responses, SSE, WebSockets, or token-by-token rendering.
- Markdown rendering, syntax highlighting, copy buttons, regenerate, edit, or delete-message actions.
- File, image, audio, or voice input.
- Using providers other than Gemini, running multiple models at once, or building a model picker. The single model ID is deployment-configurable, but only one Gemini model is active at a time.
- Redis, Postgres, vector databases, semantic caching, or any external storage.
- Horizontal scaling, multiple backend workers, shared caches, or distributed session locks.
- Rate limiting, abuse prevention, content moderation, prompt-injection defenses, or cost controls beyond the token cap.
- Usage dashboards, analytics, billing, or admin key management.
- A model picker or per-user model settings.
- Internationalization and dark mode.
- Automated frontend end-to-end tests and CI/CD pipelines.
- Guaranteed availability of the free hosting tier after the evaluation window.

---

## Further Notes

### Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| The assignment's example model, Gemini 2.0 Flash, is retired. | Live inference fails immediately. | Use a current stable Flash-Lite model, keep `LLM_MODEL` configurable, and verify it through LiteLLM before building the UI. |
| Free-tier keys share a project quota. | Both keys hit 429 at the same time. | Create keys in separate Google AI Studio projects where possible; failover still covers transient errors. |
| LiteLLM's default cache key includes request-specific values such as the API key. | Cross-key or cross-session cache hits fail. | Use an explicit cache key derived only from model, full messages, and generation parameters. Test two keys and two sessions. |
| LiteLLM does not preserve usage on cache hits. | Token metadata is wrong on `LLM_CACHE`. | Verify in the first cache spike; if needed, store a SQLite usage sidecar keyed by the same cache key. |
| Cache-hit detection is unreliable. | Wrong `resolution_source` labels. | Capture LiteLLM's documented cache-hit signal per request; never infer from latency. |
| In-memory cache is per process. | Multiple workers or replicas produce inconsistent hits. | Run exactly one backend instance and one worker; document the constraint. |
| SQLite lives on an ephemeral filesystem. | History disappears on restart. | Deploy on a platform with a persistent volume mounted at `/data`; verify with a restart test. |
| Free hosting cold starts delay the first request. | Demo looks slow or times out. | Warm the backend before the demo; keep the frontend pending state and timeouts generous. |
| CORS preflight blocks the simulation header. | Failover demo fails from the browser or tools. | Explicitly allow `X-Simulate-Failure` and test preflight from the deployed origin. |
| Frontend is built with the wrong API URL. | Deployed UI cannot reach the backend. | Set `VITE_API_BASE_URL` at build time, verify the production bundle, and test from the live origin. |
| A provider returns an empty completion. | 200 with an empty reply violates the contract. | Treat empty or whitespace-only replies as failed attempts and continue the key pool. |
| The failure-simulation hook is publicly enabled. | Anyone can force 503s. | Accept for evaluation; document the hook and the environment switch. |
| Concurrent requests to one session interleave history. | Replies use stale context. | Per-session async lock plus single-process deployment. |
| SQLite lock contention. | 500 errors under concurrency. | WAL mode, busy timeout, short transactions, and single-worker deployment. |

### Decisions deferred to implementation

- Final hosting platform for the backend, selected against the persistent-volume and always-on checklist.
- Final Gemini model ID, verified against the installed LiteLLM version and the live API.
- Final cache TTL value, defaulting to one hour.
- Exact visual styling details within the stated design direction.

### Suggested 24-hour execution plan

| Window | Focus |
|---|---|
| Hours 0–2 | Scaffold backend and frontend; create environment template; verify Gemini model and LiteLLM caching with a real key spike. |
| Hours 2–7 | Build configuration, repository, cache-key builder, failure parser, LLM gateway, chat service, and API routes. |
| Hours 7–11 | Build the React chat UI, system prompt panel, metadata strip, loading and error states, and responsive styling. |
| Hours 11–14 | Add backend tests for contract, failover, caching, history, and validation; fix gaps. |
| Hours 14–17 | Write multi-stage Dockerfiles, Compose, Makefile, and verify `make up` from a clean state. |
| Hours 17–20 | Deploy frontend and backend, configure CORS and secrets, verify persistent volume and restart survival. |
| Hours 20–22 | Complete README, curl verification guide, and deployment smoke tests. |
| Hours 22–24 | Record the demo video, run the submission checklist, and submit. |

### Demo video outline (2–3 minutes)

1. Show the live frontend and backend health endpoint.
2. Send a message, then a follow-up that depends on the first, and show multi-turn memory.
3. Point out `LIVE_INFERENCE`, model, latency, and per-message token counts.
4. Reload to start a new session, send the same first message, and show `LLM_CACHE`, identical text, null key, and lower latency.
5. Send a fresh message with `X-Simulate-Failure: key_1=429` via curl or the browser tooling, and show `key_2` with one fallback attempt.
6. Send `*=429` and show the clean 503 with nothing added to history.
7. Show the history endpoint and explain SQLite volume persistence.
8. Close with the architecture and README verification steps.

### Definition of done

- All three API endpoints match the contract exactly, including status codes, field names, and error bodies.
- Two or more keys are configured; 429, quota, 5xx, timeout, and connection failures fail over automatically.
- `X-Simulate-Failure` works for single-key, multi-key, and wildcard cases, and is disabled when the flag is off.
- Cache hits return `LLM_CACHE`, identical replies, stored token usage, null key, zero fallbacks, and lower latency.
- Per-request input and output tokens are accurate and displayed under every assistant reply.
- Multi-turn history is stored in SQLite, survives restarts, and stays isolated by session.
- The history endpoint returns oldest-first messages without the system prompt and 404s for unknown sessions.
- The frontend has every required `data-testid`, clears the input after send, and handles errors readably.
- `make up` starts backend on port 8000 and frontend on port 3000 from a clean checkout with a populated `.env`.
- Dockerfiles are multi-stage, runtime images are small, and the backend runs as non-root.
- Deployment is public, connected, CORS-correct, and backed by a persistent volume.
- Backend tests pass without live keys and cover validation, failover, caching, history, prompt semantics, and persistence.
- README contains the six required sections plus verification commands, live URLs, and the test/verification steps.
- `.env.example` is complete and contains no real secrets.
- The GitHub repository is public and contains only the intended project files; no keys, local databases, build artifacts, or environment files are committed.
- The submission form is completed with the live frontend URL, live backend URL, public repository URL, and demo video link.
- Demo video shows chat, cache hit, failover, 503, and token metadata.

### PRD publication note

This repository is not yet initialized as a Git repository and has no GitHub remote, so the PRD is stored as `PRD.md` at the project root. Once the repository is created, this document can be published as the tracking GitHub issue without content changes.
