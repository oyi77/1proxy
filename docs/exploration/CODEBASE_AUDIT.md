# Codebase Audit —  Base Audit — 2025-07-04

## Stack

| Layer | Technology | Version | Status |
|-------|------------|---------|--------|
| Backend API | FastAPI | 0.138.0 | 🟢 Current |
| ASGI Server | Uvicorn | 0.49.0 | 🟢 Current |
| Validation | Pydantic | 2.13.4 | 🟢 Current |
| ORM | SQLAlchemy | 2.0.51 | 🟢 Current |
| Migrations | Alembic | 1.16.4 | 🟡 Behind (1.18.5) |
| HTTP Client | aiohttp / httpx | 3.14.1 / 0.27.0 | 🟢 Current |
| Auth | Authlib / python-jose | 1.6.10 / 3.5.0 | 🟡 Authlib behind (1.7.2) |
| Crypto | cryptography / passlib | 49.0.0 / 1.7.4 | 🟢 Current |
| Rate Limiting | slowapi | 0.1.9 | 🟢 Current |
| Observability | Prometheus client | 0.25.0 | 🟢 Current |
| Frontend | Next.js | 15.5.15 | 🟢 Current |
| UI | React 19 + Tailwind | Latest | 🟢 Current |

---

## Directory Structure

```
1proxy/
├── 1proxy-backend/           # FastAPI backend
│   ├── app/
│   │   ├── admin/            # Admin endpoints (scraping, scheduling)
│   │   ├── config/           # Configuration
│   │   ├── grabber/          # Proxy source fetching (GitHub, web)
│   │   ├── hunter/           # Proxy discovery strategies (GitHub, Reddit, etc.)
│   │   ├── models/           # Pydantic models (Candidate, Proxy, Source)
│   │   ├── routers/          # API endpoints (auth, proxies, sources, admin)
│   │   ├── services/         # Business logic (insights, usage)
│   │   ├── utils/            # Base64 decoder
│   │   ├── auth.py           # OAuth (GitHub/Google), JWT
│   │   ├── background_validator.py  # Scheduled scraping/validation
│   │   ├── database.py       # SQLAlchemy async engine, WAL mode
│   │   ├── db_models.py      # SQLAlchemy models
│   │   ├── db_storage.py     # CRUD operations
│   │   ├── lifecycle_workers.py    # Revalidation, cleanup, tier workers
│   │   ├── main.py           # FastAPI app, startup/shutdown
│   │   ├── metrics.py        # Prometheus metrics
│   │   ├── oauth.py          # OAuth flows
│   │   ├── proxy_rotator.py  # Round-robin, sticky session
│   │   ├── source_validator.py
│   │   ├── sources.py        # Source registry
│   │   ├── storage.py        # Legacy storage interface
│   │   └── validator.py      # Proxy validation logic
│   ├── alembic/              # 10 migrations
│   ├── tests/                # Unit + integration tests
│   └── requirements.txt
├── 1proxy-frontend/          # Next.js 15 dashboard
│   ├── app/                  # App Router pages
│   ├── components/           # ProxyTable, tabs, theme
│   └── lib/                  # API client, auth context
└── docker-compose*.yml       # Dev + prod stacks
```

---

## Static Analysis

### Code Smells / Tech Debt

| Location | Issue | Severity |
|----------|-------|----------|
| `app/routers/auth.py:63` | Pydantic V1 `class Config` deprecated | 🟡 Medium |
| `app/routers/sources.py:38` | Pydantic V1 `class Config` deprecated | 🟡 Medium |
| `app/routers/proxies.py:22` | Pydantic V1 `class Config` deprecated | 🟡 Medium |
| `app/db_storage.py:185-230` | Nested loops in `add_proxies` - O(n²) per batch | 🟡 Medium |
| `app/main.py:233-302` | Startup handler does too much (DB init, admin user, seeding, workers) | 🟡 Medium |
| `app/grabber/github_grabber.py` | Hardcoded GitHub API limits, no retry config | 🟡 Medium |
| `app/hunter/strategies/*.py` | Strategies duplicate HTTP client setup | 🟡 Medium |
| `alembic/versions/412f1c5bb27a` | ~~`op.alter_column` fails on SQLite~~ **FIXED** | ✅ Done |
| `alembic/versions/a77d14e2bb80` | ~~`op.add_column` without batch~~ **FIXED** | ✅ Done |

### Dead Code / Unused

- `app/storage.py` — Legacy interface, superseded by `db_storage.py`
- `app/source_validator.py` — Not imported anywhere
- `app/dependencies.py` — Only `get_db`, could be inlined

### Security

| Check | Status |
|-------|--------|
| SQL Injection | ✅ SQLAlchemy ORM + parameterized queries |
| XSS | ✅ API-only backend, frontend sanitizes |
| CSRF | ✅ Stateless JWT + SameSite cookies |
| Auth Bypass | ✅ OAuth2 + JWT with `require_admin` guards |
| Secrets in Code | ✅ `.env.example` only, no hardcoded secrets |
| Rate Limiting | ✅ slowapi on all endpoints |
| Dependency Vulns | 🟡 Authlib 1.6.10 → 1.7.2 (minor) |

---

## Test Coverage

| Test Type | Count | Coverage |
|-----------|-------|----------|
| Unit | 40 | Core validators, parsers, extractors, models |
| Integration | 7 | Auth, admin, grabber, hunter, export, scraping |

**Critical Paths Without Tests:**
- `db_storage.add_proxies` bulk insert (partial)
- `background_validator.background_scraper_worker`
- `lifecycle_workers` (revalidation, cleanup, tier)
- `proxy_rotator` round-robin/sticky logic
- OAuth callback flows (GitHub/Google)

---

## Performance

| Area | Current | Bottleneck |
|------|---------|------------|
| Proxy Insert | ~100/sec (SQLite) | SQLite write lock under concurrent workers |
| Health Check | <10ms | N/A |
| Proxy List API | ~50ms (1000 proxies) | N/A |
| Validation | ~200ms/proxy (HTTP) | Network I/O, not CPU |
| Scraping | ~30 sources parallel | External HTTP latency |

**Recent Improvements (this session):**
- ✅ SQLite WAL mode (`journal_mode=WAL`, `synchronous=NORMAL`)
- ✅ Staggered worker startup (reduces startup contention)
- ✅ `batch_alter_table` for all migrations

---

## Architecture Score

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Scalability** | 🟡 | SQLite limits horizontal scaling; ready for PostgreSQL |
| **Maintainability** | 🟢 | Clean separation: routers → storage → models |
| **Extensibility** | 🟢 | Hunter strategies, grabber plugins, source registry |
| **Observability** | 🟢 | Prometheus metrics, structured logging, health endpoint |
| **Security** | 🟢 | OAuth2, JWT, RBAC, rate limiting, no hardcoded secrets |

---

## Quick Wins (High Impact, Low Effort)

1. **Migrate Pydantic V1 `Config` to `ConfigDict`** in 3 router files — 15 min
2. **Inline `dependencies.py`** — 5 min
3. **Remove `storage.py` and `source_validator.py`** — 5 min
4. **Add test for `proxy_rotator`** — 30 min
5. **Upgrade Alembic to 1.18.5** — 10 min (test migrations)
6. **Add request timeout config to hunters/grabbers** — 30 min

---

## Scheduled Improvements (High Impact, High Effort)

1. **PostgreSQL Migration** — Replace SQLite for production concurrency (GAP-008)
2. **CAPTCHA/JS Rendering** — Integrate playwright/2captcha for anti-bot (GAP-001, GAP-002)
3. **Rotation Strategy Plugin System** — Weighted, least-conn, ML-adaptive (GAP-101)
4. **GraphQL API** — For flexible frontend queries (GAP-006)
5. **Webhooks** — Proxy events (validated, failed, tier changed) (GAP-007)
6. **AI Proxy Scoring** — ML model predicting success per domain (GAP-206)
7. **Cost-Aware Routing** — Cheapest working proxy per domain (GAP-207)
8. **Plugin Architecture** — Custom validation/rotation/health plugins (GAP-208)