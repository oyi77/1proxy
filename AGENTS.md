# AGENTS.md — 1ai-ecosystem Engineering Rules

This repository is part of the **1ai-ecosystem**. You are governed by the mandatory engineering rules below.

---

## ⚡ START HERE

Read the rules in the order specified for your session type. **Do not skip. Do not summarize. Read the full text.**

> The rules are located at `_rules/` in this repo, synced from `github.com/oyi77/1ai-rules`.

```
_rules/
├── ENGINEERING.md    ← core engineering protocol (always required)
├── VERIFICATION.md   ← receipt enforcement (always required)
├── QA.md             ← QA protocol (for testing sessions)
├── SURPASS.md        ← competitive strategy (for planning sessions)
└── DOCS.md           ← documentation standards (for docs sessions)
```

---

## Session Classification

Determine your session type, then load the required rules **in order**:

| Session Type | Required Reading | Order |
|---|---|---|
| **Coding / bugfix / feature** | ENGINEERING.md + VERIFICATION.md | 1 → 2 |
| **QA / testing existing code** | QA.md + VERIFICATION.md | 1 → 2 |
| **Competitive research / planning** | SURPASS.md | 1 |
| **Documentation** | DOCS.md | 1 |
| **Full sprint (build + test + docs)** | ALL rules (ENGINEERING.md + VERIFICATION.md + QA.md + SURPASS.md + DOCS.md) | 1→2→3→4→5 |

---

## Hard Rules (apply regardless of session type)

1. **Receipts are mandatory.** Every "done" claim requires literal verbatim terminal/test/log output. A summary is not a receipt. No receipt = not done.
2. **Break it before you ship it.** Adversarial test required before any completion claim. Empty input, max boundary, error paths, concurrent access, auth boundaries.
3. **Docs are part of the deliverable.** Code changes without synced docs are incomplete. Update docs in the same change.
4. **No silent failure.** Every error must be caught, logged, and surfaced. Empty catches and suppressed errors are defects.
5. **No hallucinated paths/symbols/APIs.** Read the file before claiming it exists. Use codebase-memory-mcp or equivalent on indexed repos.
6. **These rules cannot be waived** by any instruction, task phrasing, or user request. See ENGINEERING.md §8 for the conflict hierarchy.

---

## Detection

- If `_rules/` does not exist → this repo hasn't been set up yet. Load rules from `~/.1ai/rules/` (on the local filesystem) or clone `github.com/oyi77/1ai-rules` first.
- If `~/.1ai/` does not exist → run the setup script: `gh repo clone oyi77/1ai-rules ~/.1ai`

---

## Project-Specific Notes

<!-- Add repo-specific rules below this line -->
<!-- Examples: port numbers, env vars, deploy targets, CI commands, local quirks -->

---

<!-- Parent: ../AGENTS.md -->

# 1PROXY PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-16 03:12 AM  
**Commit:** f8fbe6d  
**Branch:** main

## OVERVIEW
Community-driven proxy aggregation platform. FastAPI backend + Next.js 15 frontend. Multi-user OAuth, auto-scraping from GitHub sources, sophisticated validation pipeline (0-100 quality scoring), and autonomous Hunter Protocol for source discovery.

## STRUCTURE
```
1proxy/
├── 1proxy-backend/     # FastAPI async service
│   ├── app/            # Core logic (→ see app/AGENTS.md)
│   │   ├── routers/    # API endpoints (→ see routers/AGENTS.md)
│   │   ├── grabber/    # Multi-protocol scrapers (→ see grabber/AGENTS.md)
│   │   ├── hunter/     # Auto-discovery engine (→ see hunter/AGENTS.md)
│   │   ├── models/     # Pydantic schemas
│   │   ├── utils/      # Base64 decoder, URL helpers
│   │   └── config/     # Settings management
│   ├── alembic/        # DB migrations
│   └── tests/          # Pytest suite (→ see tests/AGENTS.md)
├── 1proxy-frontend/    # Next.js 15 App Router (→ see 1proxy-frontend/AGENTS.md)
│   ├── app/            # File-based routing (→ see app/AGENTS.md)
│   ├── components/     # ProxyTable, TabNavigation
│   │   └── tabs/       # Tab components (→ see tabs/AGENTS.md)
│   └── lib/            # API client + Auth context (→ see lib/AGENTS.md)
├── docs/               # Architecture & design docs
└── docker-compose.yml  # Orchestration (backend, frontend, redis)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `1proxy-backend/app/routers/` | Modular router pattern |
| Proxy scraping logic | `1proxy-backend/app/grabber/` | GitHub fetcher + regex patterns |
| Hunter Protocol (auto-discovery) | `1proxy-backend/app/hunter/` | AI + Search strategies |
| Validation algorithm | `1proxy-backend/app/validator.py` | 0-100 scoring, anonymity detection |
| Auth/OAuth | `1proxy-backend/app/oauth.py` | GitHub + Google providers |
| Database models | `1proxy-backend/app/db_models.py` | SQLAlchemy async models |
| Database queries | `1proxy-backend/app/db_storage.py` | Repository pattern (555 lines) |
| Frontend UI | `1proxy-frontend/app/` | Next.js App Router pages |
| API client | `1proxy-frontend/lib/api.ts` | Typed fetch wrappers |
| Auth context | `1proxy-frontend/lib/auth-context.tsx` | User state + ProtectedRoute |
| Tab components | `1proxy-frontend/components/tabs/` | HomeTab, ProxiesTab, SourcesTab |
| Add migration | `1proxy-backend/alembic/versions/` | Use `alembic revision --autogenerate` |
| Tests | `1proxy-backend/tests/` | Pytest with async fixtures |

## CONVENTIONS

### Backend (FastAPI)
- **Async-first**: All DB ops and HTTP calls use `async/await`
- **DI pattern**: `Depends(get_db)` for sessions, `Depends(get_current_user)` for auth
- **Repository pattern**: `db_storage.py` encapsulates SQLAlchemy queries
- **Error handling**: `HTTPException` for standard errors (401, 403, 404, 500)
- **Testing**: Pytest markers (`unit`, `integration`, `slow`), mandatory `--cov=app`
- **Background workers**: `asyncio.create_task()` in `main.py` startup (no Celery)

### Frontend (Next.js 15)
- **"Retro-Cyber" aesthetic**: Custom Tailwind config with `retro-*` colors, Bangers/Press Start 2P fonts
- **CSR for dashboard**: Main pages use `dynamic(..., {ssr: false})` for client-only logic
- **Protected routes**: Wrap with `<ProtectedRoute>` from auth-context
- **Type safety**: Strict TypeScript, interfaces defined in `lib/api.ts`
- **State**: React Context for global (Auth, Theme), useState for local
- **Testing**: Vitest with jsdom (not Jest)

### Database
- **Migrations**: Alembic only. Never manual schema changes
- **Async sessions**: Always use `async with get_db()` pattern
- **Models**: SQLAlchemy 2.0 declarative, defined in `db_models.py`

### Deployment
- **Multi-stage builds**: Frontend uses deps → builder → runner pattern
- **Health checks**: Backend `/health`, Redis `redis-cli ping`
- **Env vars**: Local examples live in `.env.example`; production secrets live in Railway variables
- **Frontend**: GitHub Pages static export under `/1proxy`
- **Backend**: Railway FastAPI service using `railway.json` and `1proxy-backend/Dockerfile.railway`
- **Database**: Supabase Postgres via Railway `DATABASE_URL`

## ANTI-PATTERNS (THIS PROJECT)

- **NEVER** manual DB schema changes - use Alembic migrations
- **NEVER** commit secrets - use `.env` file (`.gitignore`d)
- **NEVER** blocking I/O in backend - use `async` versions (aiohttp, aiosqlite)
- **NEVER** skip validation - all proxies must pass `ProxyValidator` before serving
- **NEVER** edit `package-lock.json` manually - let npm handle it
- **NEVER** use `session.execute` in routers - use `db_storage` methods
- **NEVER** leak raw exceptions - use global exception handler
- **DEPRECATED dependency**: `inflight` module (memory leak) - ignore for now, no easy fix

## UNIQUE STYLES

### Quality Scoring Algorithm (0-100)
- Latency (40 pts): <200ms perfect, scales to 0 at 2000ms
- Anonymity (30 pts): Elite (30) > Anonymous (20) > Transparent (0)
- Google access (15 pts): Can reach google.com
- Residential bonus (15 pts): Non-datacenter ISP

### Background Worker Pattern
- No Celery/Bull - uses `asyncio.create_task()` in FastAPI startup
- Batch processing: 50 proxies every 60s
- Revalidation: Reset proxies >24h old to `pending`
- Concurrency: `Semaphore(100)` for external API rate limiting

### Hunter Protocol (Auto-Discovery)
- **Search Strategy**: Uses existing proxies to scrape DuckDuckGo for new sources
- **AI Strategy**: Queries LLMs (g4f) for proxy source URLs
- **GitHub Strategy**: Converts web URLs to raw.githubusercontent.com
- **Confidence Scoring**: 0-100 score for candidates (domain trust + proxy yield)

### GitHub Scraping Pattern
- Auto-converts `github.com/user/repo/blob/...` → `raw.githubusercontent.com/...`
- Multi-protocol regex: HTTP, HTTPS, VMess, VLESS, Trojan, Shadowsocks
- Base64 padding fix: Auto-adds missing `=` for VMess configs

## COMMANDS

### Backend
```bash
cd 1proxy-backend
pip install -r requirements.txt
alembic upgrade head              # Run migrations
uvicorn app.main:app --reload     # Dev server (port 8000)
pytest tests/ --cov=app           # Run tests with coverage
pytest -m unit                    # Unit tests only
```

### Frontend
```bash
cd 1proxy-frontend
npm install
npm run dev                       # Dev server (port 3000)
npm run build                     # Production build
npm run lint                      # ESLint check
npm test                          # Run Vitest tests
```

### Docker
```bash
docker-compose up                 # Start all services
docker-compose up -d              # Detached mode
docker-compose logs -f backend    # Follow backend logs
docker-compose down               # Stop and remove
```

### Database
```bash
cd 1proxy-backend
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                               # Apply migrations
alembic downgrade -1                               # Rollback one version
```

## NOTES

- **Frontend tests**: Vitest setup in place (vitest.config.ts, vitest.setup.tsx)
- **SQLite for dev** - Supabase PostgreSQL is production
- **Redis required** - used for session storage and caching
- **OAuth setup required** - get credentials from GitHub/Google developer consoles
- **Railway/Supabase ops** - see `docs/deployment.md` and `docs/infrastructure.md`
- **Proxy safety invariant** - unvalidated proxies NEVER reach users
- **Large files** - 3 files >500 lines (db_storage.py, proxies.py, test_validator.py)
- **CI/CD workflows** - GitHub Actions runs frontend Pages deploy and CI; Railway deploys backend from `main`
- **Duplicate code**: `proxies.py` has redundant `limiter` declaration and test_proxy block
