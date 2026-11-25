# Lyftr AI — Delivery Roadmap

> Source of truth: [PRD.md](PRD.md)
> Delivery window: 24 hours from kickoff
> Status: Planning
> Detailed task list: [todo.md](todo.md)

## 1. Mission

Ship a public, full-stack LLM chat application that stays useful when an API key fails, serves repeated prompts from cache, remembers multi-turn conversations in SQLite, reports exact per-request metadata, starts locally with one command, and is demonstrated with a clear video and README.

Success is not "the chat works." Success is that the exact API and UI contract works under normal use, rate limits, simulated failures, cache hits, container restarts, and a public deployment.

## 2. Release scope and priorities

| Priority | Scope | Cut rule |
|---|---|---|
| **P0** | Exact three-endpoint API, two-key failover, simulation hook, LiteLLM caching, per-request tokens, SQLite history, Docker Compose, Makefile, public deployment, backend tests, README, demo video | Never cut |
| **P1** | System prompt field, polished Tailwind UI, persistence tests, structured logging, accessibility, local-without-Docker docs | Cut only after P0 is green |
| **P2** | Extra animations, screenshots, optional frontend component tests, additional polish | Cut first when time is short |

Out-of-scope items are listed in the PRD: authentication, multi-session UI, streaming, markdown rendering, Redis, semantic caching, multi-provider routing, horizontal scaling, CI/CD, and analytics.

## 3. Timeline at a glance

All times are relative to kickoff. Replace `T+` offsets with calendar timestamps when the build starts.

| Phase | Window | Duration | Primary goal |
|---|---:|---:|---|
| 0. Setup and spikes | T+0–2 | 2h | Validate model, cache, usage, and failover assumptions; scaffold repo; choose deployment target |
| 1. Backend foundation | T+2–7 | 5h | Working contract: config, SQLite, gateway, failover, caching, API routes |
| 2. Frontend | T+7–11 | 4h | Complete chat UI with metadata, system prompt, loading, and error states |
| 3. Testing and hardening | T+11–14 | 3h | Automated contract suite green; real-provider smoke test |
| 4. Docker and local stack | T+14–17 | 3h | Clean `make up`; volume persistence; production-shaped images |
| 5. Deployment and live verification | T+17–20 | 3h | Public URLs; cache, failover, CORS, and restart verified |
| 6. Documentation and demo | T+20–22 | 2h | README complete; 2–3 minute demo recorded |
| 7. Final QA, buffer, submission | T+22–24 | 2h | Contract audit, secret audit, submission form, contingency |

The final two hours are intentionally reserved for verification and submission. If an earlier phase slips, reduce P2/P1 polish rather than borrowing from this buffer.

## 4. Milestones and gates

| Milestone | Target | Deliverable | Exit criteria |
|---|---:|---|---|
| **M0 — Assumptions proven** | T+2 | Spike notes, scaffold, `.env.example`, chosen host | Current model works; LiteLLM cache hit works with stored usage; custom key hits across keys/sessions; two keys available; host supports a persistent volume and single always-on instance |
| **M1 — Backend contract complete** | T+7 | Running API locally | `/health`, `/chat`, and history match the contract; live and cached replies work; single-key and wildcard simulation work; 503 and 422 are exact; failed requests persist nothing |
| **M2 — Frontend complete** | T+11 | Running UI against local API | All required `data-testid` values exist; input clears after send; metadata renders; errors and Retry work; system prompt persists/resets; mobile and keyboard smoke tests pass |
| **M3 — Quality gate** | T+14 | Green test suite | P0 unit and API tests pass without live keys; real-provider smoke test passes; no known contract gaps; logs reveal no secrets |
| **M4 — Local stack gate** | T+17 | Dockerized stack | Clean checkout plus populated `.env` starts with `make up`; backend on 8000 and frontend on 3000; restart preserves SQLite history; images are multi-stage and backend runs non-root |
| **M5 — Live gate** | T+20 | Public deployment | Public frontend/backend connected; CORS correct; cache hit, failover, 503, token metadata, and restart persistence verified on live URLs |
| **M6 — Submission package** | T+22 | README + video | All six README sections complete; repo public and secret-free; 2–3 minute video shows chat, cache, failover, 503, and metadata |
| **M7 — Submitted** | T+24 | Submission form completed | URLs, repository, and video submitted; backup video and final commit saved |

## 5. Workstreams

| Workstream | Key outputs | Depends on | Notes |
|---|---|---|---|
| **Discovery and spikes** | Model verification, cache-key verification, usage preservation, host choice | Gemini keys, LiteLLM docs | Must finish before backend implementation; this is the highest-risk area |
| **Backend platform** | Config, SQLite repository, schema, health checks | Spike results | Build the repository and config first; the gateway depends on both |
| **LLM gateway** | Failover, cache, simulation, metadata, timeouts | Config + repository | Deep module; keep it isolated and unit-testable |
| **API and contract** | Three routes, validation, errors, CORS | Gateway + repository | Freeze the contract before frontend work |
| **Frontend** | Chat UI, metadata, system prompt, errors, accessibility | API contract | Shell and design can start before the backend is fully ready |
| **QA** | Unit, contract, persistence, manual UI tests | Backend + frontend | Start test infrastructure as soon as the app factory exists |
| **Platform/DevOps** | Dockerfiles, Compose, Makefile, deployment, volume | Backend + frontend | Create the host account and volume early; do not wait until T+17 |
| **Docs and demo** | README, curl verification, video, submission | Working deployed stack | Draft README sections in parallel from T+7 |

This is a solo build, so the "workstreams" are parallel tracks owned by the same developer. The intent is to expose dependencies, not to imply separate teams.

## 6. Critical path and dependencies

```text
Provider/cache spike
        │
        ▼
Config + SQLite repository
        │
        ▼
LLM gateway (failover + cache + simulation)
        │
        ▼
Chat service + API contract
        │
        ├──────────────► Frontend shell and UI (starts after contract freeze)
        │
        ▼
Backend tests + real-provider smoke
        │
        ▼
Docker + Makefile + volume
        │
        ▼
Public deployment + live verification
        │
        ▼
README + demo video + submission
```

Key dependencies:

- **Deployment platform decision by T+2.** A host without a persistent volume or always-on instance invalidates the SQLite requirement and can jeopardize the demo. Choose early.
- **Model and cache spike by T+2.** If the model ID is retired or LiteLLM does not preserve usage on cache hits, the backend design must adapt before UI work begins.
- **Contract freeze by T+7.** Frontend test IDs and metadata rendering must not chase backend field changes after M1.
- **Docker base by T+17.** Deployment should consume the same image used locally. Do not build a separate deployment path.
- **Live verification by T+20.** The demo depends on public URLs, warm instances, and a persistent volume.

## 7. Release gates and pass criteria

### Gate 0 — Assumptions proven

- Current Gemini model completes live.
- In-memory cache returns the identical reply with usage.
- Custom cache key hits across two keys and new sessions.
- Two independent keys are available.
- Deployment host supports a Docker backend, persistent volume, and always-on single instance.

### Gate 1 — Contract complete

- All three endpoints return the exact required fields and statuses.
- Failover and simulation matrix passes locally.
- Cache labels, tokens, latency, key ID, and fallback count are correct.
- 422, 404, 503, and 500 responses are JSON with no stack traces.

### Gate 2 — UI complete

- Every required `data-testid` is present with exact content.
- Input clears immediately after send.
- Live and cache metadata are visible and distinct.
- Errors are readable and retryable.
- System prompt applies for the session and can be reset.

### Gate 3 — Tests green

- P0 unit and API tests pass with no live keys and no network.
- Persistence survives app recreation.
- Real-provider smoke test confirms the deployed assumptions.
- Coverage reviewed against the 80% goal for gateway, service, repository, and API layers; this is a quality signal, not a hard release gate.

### Gate 4 — Local stack

- Clean `make up` works with a populated `.env`.
- Backend on 8000, frontend on 3000.
- SQLite volume survives `docker compose restart` and recreation.
- Images are multi-stage and the backend runs non-root.

### Gate 5 — Live

- Public frontend and backend connected.
- `/health` reports keys and cache.
- Multi-turn, cache hit, failover, 503, and restart persistence verified.
- CORS preflight includes `X-Simulate-Failure`.
- Live URLs load without login.

### Gate 6 — Submission package

- README uses the six required headings and includes verification commands.
- Repo is public and contains no secrets, databases, or build artifacts.
- Demo video is 2–3 minutes, has voice, and shows every required behavior.

### Gate 7 — Submitted

- Submission form completed.
- Backup video link and final commit saved.
- All P0 TODO items checked.

## 8. Risks and contingencies

| Risk | Likelihood | Impact | Trigger | Response |
|---|---|---|---|---|
| Assignment's example Gemini model is retired | High | High | Model ID fails at T+0–2 | Use a current stable Flash-Lite model; keep `LLM_MODEL` configurable |
| LiteLLM default cache key includes API key or other request state | Medium | High | Cache misses across keys/sessions | Use an explicit custom cache key; verify with two keys and two sessions |
| LiteLLM does not preserve usage on cache hits | Medium | High | Cached response lacks tokens | Store a small SQLite usage sidecar keyed by the cache key |
| Free-tier keys share a project quota | Medium | Medium | Both keys fail together | Use separate Google AI Studio projects; keep failover and clean 503 |
| Deployment host lacks a persistent volume | Medium | High | Volume unavailable or ephemeral | Switch to Fly.io/Railway by T+17; do not accept lost history |
| Free host cold start delays requests | Medium | Medium | First request slow or times out | Warm the backend before each demo; keep loading UI and timeouts generous |
| CORS blocks the simulation header | Low | High | Preflight fails in browser/tools | Explicitly allow `X-Simulate-Failure`; test from the live origin |
| Frontend built with wrong API URL | Low | High | UI cannot reach backend | Set `VITE_API_BASE_URL` at build time; verify the production bundle |
| SQLite lock contention or concurrent interleaving | Low | Medium | 500s or stale context under concurrency | WAL, busy timeout, per-session lock, single worker |
| Scope creep into streaming/auth/multi-session | Medium | High | P0 tasks slip | Enforce the out-of-scope list; defer to post-MVP |
| Demo reveals a cache or failover gap | Low | High | Live verification fails | Re-run gates 5 and 6; keep a 2-hour buffer |

## 9. Contingency plan

- **If the model spike fails:** switch to the nearest stable Gemini Flash/Flash-Lite model and re-run usage/cache checks. Do not build the UI until a real completion works.
- **If cache-key behavior is unreliable:** own the cache key explicitly. If usage is missing, add the SQLite sidecar. Do not replace LiteLLM's cache with a custom implementation, because the assignment requires LiteLLM's built-in cache.
- **If deployment volume issues appear:** switch backend host by T+17. Preserve the same Docker image and `DATABASE_URL` contract.
- **If time runs short:** protect P0 contract, deployment, tests, README, and demo. Cut visual polish, optional component tests, screenshots, and extra animations.
- **If the demo cannot show browser failover:** use curl against the live API and show the raw JSON response; the header contract is backend-facing.

## 10. Post-MVP roadmap

These items are intentionally outside the 24-hour submission. They represent the natural next steps after the assignment.

### Now — 24-hour delivery

- Exact contract, two-key failover, LiteLLM cache, per-request metadata, SQLite history, Docker, public deployment, tests, README, demo.

### Next — 2–4 weeks

| Theme | Work |
|---|---|
| Conversation experience | Session sidebar, history restore, streaming responses, markdown rendering, regenerate/edit/delete |
| Identity | User accounts, authenticated sessions, per-user data isolation |
| Infrastructure | Redis cache for multiple workers, a managed database option for future scale, CI/CD pipeline, preview environments |
| Reliability | Multi-provider routing, health dashboards, alerts, retry budgets, rate limiting |
| Quality | Frontend E2E tests, load tests, contract tests in CI, observability and tracing |

### Later — 1–3 months

| Theme | Work |
|---|---|
| Platform | Team workspaces, sharing, roles, admin key management |
| Cost and quality | Usage budgets, evaluation dashboards, semantic caching, model picker and auto-routing |
| Reach | PWA/mobile experience, localization, accessibility audit at scale |
| Security | Abuse detection, content moderation, audit logs, secret rotation |

## 11. Operating cadence

- **T+2:** Gate 0 review; confirm model, cache, keys, and hosting.
- **T+7:** Gate 1 review; freeze the API contract.
- **T+11:** Gate 2 review; UI feature-complete.
- **T+14:** Gate 3 review; test suite green.
- **T+17:** Gate 4 review; `make up` clean and persistent.
- **T+20:** Gate 5 review; public deployment verified.
- **T+22:** Gate 6 review; README and video complete.
- **T+24:** Gate 7; submit.

At each checkpoint, update [todo.md](todo.md), record any decision changes in the PRD, and explicitly decide what to cut if the phase is behind.

## 12. Definition of shipped

The release is shipped when every P0 item in [todo.md](todo.md) is checked, all seven gates pass, the public frontend and backend are reachable and connected, the repository is public and secret-free, and the submission form is complete with the live URLs and demo video.
