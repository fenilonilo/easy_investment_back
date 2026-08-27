# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run (Docker — recommended):**
```bash
docker compose up --build
```
Requires ports `6379`, `5433` and `8000` free. Starts the API, Redis and `postgres_ai` (pgvector, for the AI agent).

**Run locally (without Docker):**
```bash
uv run uvicorn main:app --reload
```
Requires a running Redis on `localhost:6379` and PostgreSQL on port `5432`.

**Add a dependency:**
```bash
uv add <package>
```

**Run tests:**
```bash
uv run pytest
```

**Ingest the AI knowledge base** (one-off; idempotent). Requires `postgres_ai` up and `GOOGLE_API_KEY` set:
```bash
uv run python scripts/ingest_knowledge.py
```

**Interactive API docs:** `http://localhost:8000/docs`

## Architecture

This is a **FastAPI** application with a layered architecture:

```
main.py               → App entry point; lifespan, routers, CORS middleware
api/                  → HTTP layer (routers); thin, delegates to services
  ai_router.py        → /ai endpoints (chat, SSE stream, sessions)
services/             → Business logic (AssetService); orchestrates provider + cache
  ai/                 → AI agent layer
    chat_service.py   → Runs the agent, streams SSE, manages sessions
    agent_factory.py  → Builds the Agno Agent per conversation
    tools.py          → Market tools (via AssetService) + watchlist write tools
    prompts.py        → Agent description + instructions (pt-BR)
    context.py        → UserContext dataclass (no ORM leaks into streaming)
infrastructure/       → External integrations
  providers.py        → IAssetProvider / YahooFinanceProvider (yfinance + httpx)
  cache.py            → ICacheProvider / RedisCache (redis.asyncio)
  database.py         → SQLAlchemy engine + get_db() dependency (PostgreSQL)
  ai/                 → Agno wiring
    runtime.py        → AIRuntime singleton built in the lifespan
    agent_db.py       → AsyncPostgresDb (agent sessions + summaries)
    knowledge.py      → Knowledge + PgVector + Gemini embedder
    model_router.py   → Gemini → Groq fallback with Redis circuit breaker
models/               → SQLAlchemy ORM models + Pydantic schemas (same file per domain)
core/
  config.py           → Env vars (SECRET_KEY, REDIS_URL, CACHE_TTL_SECONDS, AI_*)
  security.py         → JWT auth, bcrypt hashing, get_current_user() dependency
knowledge_docs/       → Curated RAG corpus (11 pt-BR markdown docs)
scripts/              → ingest_knowledge.py (one-off knowledge ingestion)
tests/                → pytest suite (no live LLM calls)
```

### Key design patterns

- **Provider abstraction**: `IAssetProvider` (ABC) decouples the router/service from yfinance. To swap the data source, implement the interface and inject it in `asset_router.py:get_asset_service()`.
- **Cache abstraction**: `ICacheProvider` (ABC) wraps Redis. `AssetService` uses it for read-through caching with per-operation TTLs (quote: 60s, history/financials/dividends: 1h–24h, news: 30min, search: 1h).
- **yfinance is synchronous**: All `yfinance` calls are wrapped in `loop.run_in_executor()` or `run_in_threadpool()` to avoid blocking the async event loop.
- **All asset and AI endpoints require JWT auth** (`Depends(get_current_user)`); auth and user endpoints are public.

### Ticker auto-formatting (`providers.py:_format_ticker`)

- 5+ chars ending in digit → appends `.SA` (B3, e.g. `PETR4` → `PETR4.SA`)
- Known crypto symbols → appends `-USD` (e.g. `BTC` → `BTC-USD`)
- Otherwise passes through unchanged (US stocks)

### Infrastructure

- **Database**: PostgreSQL at `host.docker.internal:5432`, database `easy_finace`. Connection hardcoded in `infrastructure/database.py` — override via `.env` if needed. Sync engine (`create_engine` + psycopg2), no Alembic; schema is created by hand.
- **AI database**: separate `postgres_ai` compose service (`pgvector/pgvector:pg17`), host port `5433`, from `AI_DATABASE_URL`. Uses psycopg3 (`postgresql+psycopg://`).
- **Redis**: URL from `REDIS_URL` env var (default: `redis://localhost:6379`).
- **Auth**: JWT (HS256), 1-hour expiration. `SECRET_KEY` and `ALGORITHM` from `.env`.

### Data models (`models/`)

- `models/user.py`: `User` (ORM), `UserWatchlist` (JSONB tickers column), `UserCreate`/`UserResponse`/`UserUpdate` (Pydantic).
- `models/asset.py`: `Asset`, `AssetQuote`, `HistoryPoint`, `Dividend`, `Financials`, `NewsItem` (all Pydantic).
- `models/ai.py`: `ChatRequest`/`ChatResponse`, `SessionInfo`, `SessionDetail`, `MessageItem`, `SessionSummaryResponse` (all Pydantic v2).

## AI agent subsystem (`/ai`)

An Agno-based chat agent focused on asset management and financial-metric education.

### Where things live

- **`AIRuntime`** (`infrastructure/ai/runtime.py`) is built once in the `main.py` lifespan and stored on `app.state.ai_runtime`. It holds the Agno DB, the model router and the lazily-built `Knowledge`. This is the first lifespan in the project — everything else is still built per request.
- **`AIChatService`** (`services/ai/chat_service.py`) is built per request from that runtime, mirroring `asset_router.py:get_asset_service()`.

### Constraints that shaped the design

- **`Knowledge.__post_init__` does blocking I/O** — it calls `vector_db.exists()` and `create()`. Building it in the lifespan would hang API startup whenever `postgres_ai` is down, taking the unrelated asset endpoints with it. So it is built on first use, in a threadpool, with a 60s negative-cache backoff after failure. `get_knowledge()` returning `None` is a supported state: the agent runs without RAG.
- **SQLAlchemy is synchronous** here. Watchlist reads/writes inside the agent go through `run_in_threadpool`, and the watchlist tools open their **own** `SessionLocal` — the request session is already closed by the time a tool runs inside a streaming generator.
- **`get_current_user` returns a session-bound ORM object.** It never reaches the agent: `services/ai/context.py:UserContext` snapshots the primitive fields while the request session is alive.
- **JSONB mutation needs `flag_modified`** (same as `api/profile_router.py:52`), otherwise the watchlist tool commits nothing.

### Model fallback

`ModelRouter` (`infrastructure/ai/model_router.py`) prefers Gemini. On an availability error (429/503/timeout) the run is retried once on Groq and Gemini is quarantined in Redis for `AI_FALLBACK_COOLDOWN_SECONDS`. Credential errors (401/403, "API key not valid") deliberately do **not** trigger fallback — they surface as 502 instead of being masked. The circuit breaker only needs `get`/`set`, so `ICacheProvider` was left unchanged.

In streaming, the switch only happens before the first token; a mid-stream failure emits an `error` frame rather than restarting the response.

### Session ownership

Every route taking a `session_id` verifies ownership, `/ai/chat` included — resuming someone else's session would load their history into the model's context. `assert_can_use_session()` looks the session up **without** the `user_id` filter on purpose: with the filter, another user's session comes back as `None` and is indistinguishable from a new session, which would then be created over it. Unauthorized access returns 404, never 403.

### Agent database

The Agno tables (sessions, summaries, knowledge contents, vectors) live in the `postgres_ai` compose service, not in `easy_finace`. Agno creates and migrates them itself, which is why this subsystem needs no Alembic — the project still has no migration tool.

### Pydantic version note

The project runs **Pydantic v2** (`uv.lock` pins 2.12.5). Older code uses v1-style APIs (`.json()`, `.parse_raw()`, `.dict()`) that still work through v2's deprecation shims. Write new schemas with v2 APIs (`model_dump`, `model_validate_json`).
