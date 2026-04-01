# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run (Docker — recommended):**
```bash
docker compose up --build
```
Requires port `6379` free. Starts both the API (port `8000`) and Redis.

**Run locally (without Docker):**
```bash
uv run uvicorn main:app --reload
```
Requires a running Redis on `localhost:6379` and PostgreSQL on port `5432`.

**Add a dependency:**
```bash
uv add <package>
```

**Interactive API docs:** `http://localhost:8000/docs`

## Architecture

This is a **FastAPI** application with a layered architecture:

```
main.py               → App entry point; registers routers and CORS middleware
api/                  → HTTP layer (routers); thin, delegates to services
services/             → Business logic (AssetService); orchestrates provider + cache
infrastructure/       → External integrations
  providers.py        → IAssetProvider / YahooFinanceProvider (yfinance + httpx)
  cache.py            → ICacheProvider / RedisCache (redis.asyncio)
  database.py         → SQLAlchemy engine + get_db() dependency (PostgreSQL)
models/               → SQLAlchemy ORM models + Pydantic schemas (same file per domain)
core/
  config.py           → Env vars (SECRET_KEY, REDIS_URL, CACHE_TTL_SECONDS)
  security.py         → JWT auth, bcrypt hashing, get_current_user() dependency
```

### Key design patterns

- **Provider abstraction**: `IAssetProvider` (ABC) decouples the router/service from yfinance. To swap the data source, implement the interface and inject it in `asset_router.py:get_asset_service()`.
- **Cache abstraction**: `ICacheProvider` (ABC) wraps Redis. `AssetService` uses it for read-through caching with per-operation TTLs (quote: 60s, history/financials/dividends: 1h–24h, news: 30min, search: 1h).
- **yfinance is synchronous**: All `yfinance` calls are wrapped in `loop.run_in_executor()` or `run_in_threadpool()` to avoid blocking the async event loop.
- **All asset endpoints require JWT auth** (`Depends(get_current_user)`); auth and user endpoints are public.

### Ticker auto-formatting (`providers.py:_format_ticker`)

- 5+ chars ending in digit → appends `.SA` (B3, e.g. `PETR4` → `PETR4.SA`)
- Known crypto symbols → appends `-USD` (e.g. `BTC` → `BTC-USD`)
- Otherwise passes through unchanged (US stocks)

### Infrastructure

- **Database**: PostgreSQL at `host.docker.internal:5432`, database `easy_finace`. Connection hardcoded in `infrastructure/database.py` — override via `.env` if needed.
- **Redis**: URL from `REDIS_URL` env var (default: `redis://localhost:6379`).
- **Auth**: JWT (HS256), 1-hour expiration. `SECRET_KEY` and `ALGORITHM` from `.env`.

### Data models (`models/`)

- `models/user.py`: `User` (ORM), `UserWatchlist` (JSONB tickers column), `UserCreate`/`UserResponse`/`UserUpdate` (Pydantic).
- `models/asset.py`: `Asset`, `AssetQuote`, `HistoryPoint`, `Dividend`, `Financials`, `NewsItem` (all Pydantic).

### Pydantic version note

The codebase uses Pydantic v1-style APIs (`.json()`, `.parse_raw()`, `.dict()`). There are compatibility shims in `AssetService` for v2, but the project is effectively on v1.
