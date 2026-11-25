# Lyftr AI — Full-Stack LLM Chat with Key Failover & Caching

A production-grade chat application that integrates Google's Gemini API with automatic key failover, intelligent response caching, and persistent SQLite history. Designed for resilience, cost efficiency, and transparent per-request metadata.

## 1.  Run Locally

### With Docker (recommended)

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your Gemini API keys:**
   ```bash
   # In .env, replace placeholders with real keys from https://aistudio.google.com/apikey
   LLM_API_KEYS=key-1,key-2
   ALLOWED_ORIGINS=http://localhost:3000
   ```

3. **Start the full stack:**
   ```bash
   make up
   ```

4. **Access the app:**
   - Frontend: http://localhost:3000
   - Backend health: http://localhost:8000/health
   - API docs: http://localhost:8000/docs (if enabled)

5. **Stop the stack:**
   ```bash
   make down
   ```

6. **View logs:**
   ```bash
   make logs
   ```

### Without Docker (local development)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./app.db
export LLM_API_KEYS=key-1,key-2
export ALLOWED_ORIGINS=http://localhost:3000
export ENABLE_FAILURE_SIMULATION=true
python -m uvicorn app.main:app --reload --port 8000
```

**Frontend (in a new terminal):**
```bash
cd frontend
npm install
export VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

The frontend will be available at http://localhost:3000.

---

## 2. Design Decisions

### Key Failover & Resilience

- **Multi-key pool:** Configure 2+ Gemini API keys across separate Google projects. When a key hits a 429 (rate limit), 500 (server error), or quota exhaustion, the system automatically tries the next key in order.
- **Failure simulation:** The `/chat` endpoint honors the `X-Simulate-Failure` header (when `ENABLE_FAILURE_SIMULATION=true`) to test failover without exhausting real keys. Format: `X-Simulate-Failure: key_1=429,key_2=500` or `*=429` for all keys.
- **Exact error handling:** When all keys fail, the endpoint returns HTTP 503 with `{"detail": "all providers unavailable"}` and **does not** store the failed request in history.

### Caching with LiteLLM

- **In-memory cache:** LiteLLM caches responses by a custom key: `model + system_prompt + full_message_history + generation_parameters` (excluding API key, session ID, and simulation state).
- **Cache visibility:** Every response includes a `resolution_source` field:
  - `LIVE_INFERENCE`: Generated fresh from the API
  - `LLM_CACHE`: Returned from the cache (faster, same reply)
- **Per-request tokens:** Token usage is tracked individually for each request, not as a conversation total. Cache hits preserve the original usage.

### SQLite Session Storage

- **Per-session history:** Each chat session (identified by `session_id`) maintains its own conversation history in SQLite. The client sends only the new message; the backend assembles the full context from history.
- **Persistent volume:** The database file lives in a Docker volume (`/data/app.db`). History survives container restarts and stack recreation.
- **Automatic schema:** The database schema is created on startup if it doesn't exist.
- **System prompt scoping:** System prompts are session-scoped and can be overridden per request or reset by clearing the prompt field.

### Architecture Overview

```
Frontend (React + Vite)
    ↓ (HTTP POST /chat, GET /sessions/{id}/messages)
FastAPI Backend
    ├─→ Failure Simulation Parser (X-Simulate-Failure)
    ├─→ LLM Gateway (LiteLLM)
    │    ├─→ Cache Check (in-memory)
    │    ├─→ Key Failover Loop
    │    └─→ Usage Tracking
    ├─→ Chat Service (session management)
    └─→ SQLite Repository (message storage)
        └─→ Database (SQLite /data/app.db)
```

### Request Flow

1. **User sends a message** in the frontend.
2. **Frontend generates a session ID** (persisted for the page load) and sends `POST /chat`.
3. **Backend retrieves the session's history** from SQLite.
4. **Gateway assembles the full message list** (system prompt + history + new message).
5. **Gateway computes a cache key** (model + messages + params, excluding API key/session/simulation).
6. **If cache hit:** Return the cached reply, `LLM_CACHE`, and stored usage. **latency_ms is low.**
7. **If cache miss:** Try keys in order until one succeeds.
   - On error (429, 500, quota, timeout): **increment fallback_attempts and try the next key.**
   - On success: Store the reply and usage in cache; return `LIVE_INFERENCE`, the key ID, and fallback count.
8. **Failed requests** (all keys exhausted) return HTTP 503 and **do not** save to history.
9. **Successful responses** are stored in SQLite as a new message pair (user + assistant with metadata).

---

## 3. Verification

### Cache Hits & Per-Request Tokens

1. **Send the same first message in two different sessions:**

   ```bash
   # Session 1
   curl -s -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"session_id":"s-demo-1","message":"What is 2+2?"}' | jq .metadata

   # Session 2 (same message, different session)
   curl -s -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"session_id":"s-demo-2","message":"What is 2+2?"}' | jq .metadata
   ```

   **Expected:** The second response shows `"resolution_source": "LLM_CACHE"` with the same tokens and reply, faster latency.

2. **Multi-turn context:**

   ```bash
   # First message
   curl -s -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"session_id":"s-multi","message":"My name is Alice."}' | jq .reply

   # Follow-up (backend includes prior history)
   curl -s -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"session_id":"s-multi","message":"What is my name?"}' | jq .reply
   ```

   **Expected:** The bot correctly remembers "Alice."

### Key Failover

1. **Simulate key_1 failing:**

   ```bash
   curl -s -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -H "X-Simulate-Failure: key_1=429" \
     -d '{"session_id":"s-failover","message":"Hello"}' | jq .metadata.key_id
   ```

   **Expected:** `"key_2"` (the next key in the pool).

2. **Force all keys to fail:**

   ```bash
   curl -s -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -H "X-Simulate-Failure: *=429" \
     -d '{"session_id":"s-fail-all","message":"Test"}' \
     | jq .
   ```

   **Expected:** HTTP 503 with `{"detail": "all providers unavailable"}`. The session history **should not** contain this request.

### Session History & Persistence

1. **Retrieve session history:**

   ```bash
   curl -s "http://localhost:8000/sessions/s-multi/messages" | jq .
   ```

   **Expected:** An array of alternating user and assistant messages, oldest first. Assistant messages include metadata (excluding the full `key_id` and `fallback_attempts`).

2. **Restart the backend and confirm history survives:**

   ```bash
   docker compose restart backend
   # Wait for backend to be healthy...
   curl -s "http://localhost:8000/sessions/s-multi/messages" | jq '.messages | length'
   ```

   **Expected:** Same number of messages as before the restart.

### Health & Configuration

```bash
curl -s "http://localhost:8000/health" | jq .
```

**Expected:** `{"status": "ok", "keys_configured": 2, "cache_enabled": true}` (or the actual count of keys).

---

## 4. Setup Used

### Editor & Environment
- **Editor:** VS Code
- **Python:** 3.11+, with uv for fast dependency installation
- **Node:** 20+, npm 10+

### Key Technologies
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **Backend:** FastAPI, Uvicorn, SQLAlchemy (async), aiosqlite
- **LLM Integration:** LiteLLM 1.110+
- **Caching:** LiteLLM's built-in in-memory cache
- **Database:** SQLite with async support
- **Deployment:** Docker + Docker Compose (local), Fly.io (backend), Vercel (frontend)
- **Testing:** pytest with async fixtures, fake gateway for deterministic tests

### AI Tools Used
- Claude (Kiro) for code generation, architecture design, and troubleshooting

---

## Useful Commands

### Local Development
```bash
# Start the full stack
make up

# View logs
make logs

# Run backend tests
make test

# Stop the stack
make down

# Clean up containers and volumes
make clean
```

### Manual API Testing
```bash
# Health check
curl -s "http://localhost:8000/health" | jq .

# Single turn
curl -s -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s-1","message":"Hello"}'

# Cache test
curl -s -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s-2","message":"Hello"}' | jq .metadata.resolution_source

# Failover test
curl -s -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: key_1=429" \
  -d '{"session_id":"s-3","message":"Hello"}' | jq .metadata.key_id

# History
curl -s "http://localhost:8000/sessions/s-1/messages" | jq .
```

---

## Project Structure

```
LyftrAI/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # Uvicorn entrypoint
│   │   ├── api.py            # FastAPI factory and routes
│   │   ├── config.py         # Settings and validation
│   │   ├── database.py       # SQLite async setup
│   │   ├── repository.py     # Message and session storage
│   │   ├── gateway.py        # LiteLLM gateway with failover
│   │   ├── service.py        # Chat service logic
│   │   ├── schemas.py        # Pydantic models
│   │   ├── errors.py         # Custom exceptions
│   │   ├── cache_key.py      # Cache key builder
│   │   └── simulation.py     # Failure simulation parser
│   ├── tests/
│   │   ├── conftest.py       # pytest fixtures
│   │   ├── fakes.py          # Fake gateway for testing
│   │   ├── test_api.py
│   │   ├── test_gateway.py
│   │   ├── test_cache_key.py
│   │   ├── test_simulation.py
│   │   ├── test_persistence.py
│   │   └── test_config.py
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx          # React entry point
│   │   ├── index.css         # Tailwind setup
│   │   ├── types.ts          # TypeScript types
│   │   ├── api.ts            # API client
│   │   ├── utils.ts          # Utilities
│   │   └── components/
│   │       ├── Chat.tsx      # Main chat container
│   │       ├── Header.tsx
│   │       ├── ChatTranscript.tsx
│   │       ├── UserBubble.tsx
│   │       ├── AssistantBubble.tsx
│   │       ├── MetadataDisplay.tsx
│   │       ├── ChatComposer.tsx
│   │       ├── SystemPromptPanel.tsx
│   │       ├── LoadingIndicator.tsx
│   │       └── ErrorMessage.tsx
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── .dockerignore
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── package.json
├── docker-compose.yml
├── Makefile
├── .env.example
├── README.md (this file)
├── roadmap.md (delivery timeline)
├── todo.md (task checklist)
└── .gitignore
```

---

## Limitations & Known Issues

- **Single instance:** The backend runs with one worker. Multi-worker deployment would require a shared cache (Redis) due to LiteLLM's in-memory cache being process-local.
- **Anonymous sessions:** No user accounts; sessions are identified by client-generated IDs only.
- **Cache reset on restart:** In-memory cache is lost when the backend restarts. SQLite history survives.
- **Simulation hook requires explicit enablement:** The `X-Simulate-Failure` header is only honored when `ENABLE_FAILURE_SIMULATION=true`. Never enable this in production.

---

## Troubleshooting

### "all providers unavailable" on first request
- Confirm both API keys are valid and have quota remaining.
- Check that `LLM_API_KEYS` in `.env` has at least 2 keys, comma-separated, with no spaces.

### Frontend cannot reach backend
- Verify `VITE_API_BASE_URL` in `.env` matches your backend URL.
- Check CORS settings: `ALLOWED_ORIGINS` must include the frontend's origin.
- Confirm the backend is healthy: `curl http://localhost:8000/health`

### Database errors after restart
- Ensure the Docker volume is mounted at `/data` in both the backend Dockerfile and compose file.
- Check permissions: the app runs as a non-root user; ensure the volume is writable.

### Cold start delays
- The backend may take 30–40 seconds to start (health check start period). The compose file waits for it.
- The frontend waits for the backend to be healthy before starting.

---

## License

This project is part of a learning assignment and is provided as-is.

---

**Built with care by Samriddhi, using Claude (Kiro) AI assistance.**
