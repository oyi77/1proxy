# 1PROXY BACKEND CORE (APP)

**Location:** `1proxy-backend/app/`  
**Focus:** FastAPI core logic, validation pipeline, and background workers.

## OVERVIEW
Contains the central application logic for 1proxy, including the asynchronous database storage layer, sophisticated proxy validation pipeline, and background scraping/validation workers.

## STRUCTURE
```
app/
├── routers/              # API endpoints (Proxies, Sources, Auth, Admin)
├── grabber/              # Multi-protocol scrapers (GitHub, Base64, Regex)
├── models/               # Pydantic request/response schemas
├── utils/                # Shared helper functions (Base64, URL parsing)
├── db_storage.py         # Repository pattern (all SQLAlchemy queries)
├── db_models.py          # SQLAlchemy 2.0 async ORM models
├── validator.py          # 0-100 Quality Scoring & Anonymity detection
├── background_validator.py # Perpetual validation & revalidation loops
├── dependencies.py       # DI for Auth (JWT) and DB sessions
├── auth.py               # Token crypto (PyJWT)
└── database.py           # Async engine and session factory
```

## WHERE TO LOOK
| Task | File |
|------|------|
| Edit API logic | `routers/*.py` |
| Change DB queries | `db_storage.py` |
| Adjust Quality Score | `validator.py` |
| Modify Auth Flow | `auth.py` / `dependencies.py` |
| Add new Scraper | `grabber/*.py` |
| Define DB Schema | `db_models.py` |

## CONVENTIONS
- **Repository Pattern**: Never use `session.execute` in routers. Call `db_storage` methods.
- **Dependency Injection**: Use `Depends(get_db)` for sessions, `Depends(require_user)` for security, `Depends(require_admin)` for admin-only endpoints.
- **Async-First**: Use `aiohttp` for external calls and `await` for all DB operations.
- **Background Workers**: Triggered in `main.py` via `asyncio.create_task()`.
- **Quality Score (0-100)**: Defined in `ProxyValidator.calculate_quality_score()`.
- **Validation Pipeline**: Batch processing (50/min) to avoid rate limits.
- **Rate Limiting**: Use `@limiter.limit("N/period")` decorator on endpoints. Public endpoints: 100/hour, testing: 10/minute.
- **Error Handling**: Use global exception handler. Never leak raw exceptions to users.
- **Logging**: Use `logging.logger` not `print()`. Log levels: INFO (operations), ERROR (failures).
- **Security**: All SECRET_KEY must be set in env. Admin endpoints protected by default.
- **Performance**: Use `selectinload()` for relationships, bulk inserts for multiple records, GROUP BY for aggregations.

## NEW ENDPOINTS (2026-01-13)
- **POST /api/v1/proxies/test**: Test any proxy URL interactively (rate limited: 10/min)
- **GET /api/v1/proxies/export?format=pac**: Export PAC (Proxy Auto-Config) file for browsers
- **GET /api/v1/proxies/random?exclude=IP1,IP2**: Smart rotation with IP exclusion list

## SECURITY REQUIREMENTS
- **Admin Endpoints**: All `/api/v1/admin/*` routes require `require_admin` dependency
- **Scrape Endpoints**: All scraping operations (`/scrape`, `/scrape-all`, `/demo`) require admin auth
- **Secret Key**: App fails fast on startup if SECRET_KEY is missing or weak
- **Error Leakage**: Global exception handler prevents stack traces in responses

## PERFORMANCE OPTIMIZATIONS
- **N+1 Prevention**: All `get_proxies()` queries use `selectinload(Proxy.source)`
- **Bulk Operations**: `add_proxies()` uses SQLite upsert (INSERT ... ON CONFLICT DO UPDATE)
- **Query Optimization**: `get_stats()` uses single GROUP BY instead of looped counts
- **Connection Pooling**: SQLAlchemy configured with pool_size=20, max_overflow=30, pool_pre_ping=True

## ANTI-PATTERNS
- **NO** synchronous database calls (use `AsyncSession`).
- **NO** direct DB model instantiation in routers (use `models/` Pydantic schemas).
- **NO** blocking `time.sleep()` (use `asyncio.sleep()`).
- **NO** hardcoded secrets (import from `app.config` or use env vars).
- **NO** unvalidated proxies in user-facing endpoints.
- **NO** `print()` statements (use `logging.logger`).
- **NO** raw exception returns to users (use global handler).
- **NO** row-by-row inserts for bulk data (use bulk upsert).
- **NO** looped COUNT queries (use GROUP BY).
- **NO** missing `selectinload()` on relationships accessed in loops.
