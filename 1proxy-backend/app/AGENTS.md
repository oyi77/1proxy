# 1PROXY BACKEND CORE (APP)

**Location:** `1proxy-backend/app/`  
**Focus:** FastAPI core logic, validation pipeline, and background workers.

## OVERVIEW
Central application logic for 1proxy: asynchronous database storage, sophisticated proxy validation (0-100 scoring), and perpetual background workers for scraping/validation.

## STRUCTURE
```
app/
├── routers/              # API endpoints (→ see routers/AGENTS.md)
├── grabber/              # Multi-protocol scrapers (→ see grabber/AGENTS.md)
├── hunter/               # Auto-discovery engine (→ see hunter/AGENTS.md)
├── models/               # Pydantic request/response schemas
├── utils/                # Shared helpers (Base64, URL parsing)
├── config/               # Settings management
├── db_storage.py         # Repository pattern (555 lines - all SQLAlchemy queries)
├── db_models.py          # SQLAlchemy 2.0 async ORM models
├── validator.py          # 0-100 Quality Scoring & Anonymity detection
├── background_validator.py # Perpetual validation/revalidation loops
├── dependencies.py       # DI for Auth (JWT) and DB sessions
├── auth.py               # Token crypto (PyJWT)
├── oauth.py              # GitHub/Google OAuth flows
├── source_validator.py   # Source URL validation logic
└── main.py               # FastAPI app + worker initialization
```

## WHERE TO LOOK
| Task | File |
|------|------|
| Edit API logic | `routers/*.py` |
| Change DB queries | `db_storage.py` (ONLY place for session.execute) |
| Adjust Quality Score | `validator.py` → `calculate_quality_score()` |
| Modify Auth Flow | `auth.py` / `dependencies.py` / `oauth.py` |
| Add new Scraper | `grabber/*.py` |
| Add discovery strategy | `hunter/strategies/*.py` |
| Define DB Schema | `db_models.py` |
| Background worker logic | `background_validator.py` |

## CONVENTIONS
- **Repository Pattern**: Never use `session.execute` in routers. Call `db_storage` methods.
- **Dependency Injection**: Use `Depends(get_db)` for sessions, `Depends(require_user)` for auth, `Depends(require_admin)` for admin endpoints.
- **Async-First**: Use `aiohttp` for external calls and `await` for all DB operations.
- **Background Workers**: Triggered in `main.py` via `asyncio.create_task()`.
- **Quality Score (0-100)**: Defined in `ProxyValidator.calculate_quality_score()`.
- **Validation Pipeline**: Batch processing (50/min) to avoid rate limits.
- **Rate Limiting**: Use `@limiter.limit("N/period")` decorator. Public: 100/hour, testing: 10/min.
- **Error Handling**: Use global exception handler. Never leak raw exceptions.
- **Logging**: Use `logging.logger` not `print()`. Levels: INFO (operations), ERROR (failures).

## SECURITY REQUIREMENTS
- **Admin Endpoints**: All `/api/v1/admin/*` routes require `require_admin` dependency
- **Scrape Endpoints**: All scraping operations require admin auth
- **Secret Key**: App fails fast on startup if SECRET_KEY missing/weak
- **Error Leakage**: Global exception handler prevents stack traces in responses

## PERFORMANCE OPTIMIZATIONS
- **N+1 Prevention**: All `get_proxies()` queries use `selectinload(Proxy.source)`
- **Bulk Operations**: `add_proxies()` uses SQLite upsert (INSERT ... ON CONFLICT DO UPDATE)
- **Query Optimization**: `get_stats()` uses single GROUP BY instead of looped counts
- **Connection Pooling**: SQLAlchemy configured with pool_size=20, max_overflow=30, pool_pre_ping=True

## ANTI-PATTERNS
- **NO** synchronous database calls (use `AsyncSession`)
- **NO** direct DB model instantiation in routers (use `models/` Pydantic schemas)
- **NO** blocking `time.sleep()` (use `asyncio.sleep()`)
- **NO** hardcoded secrets (import from `app.config` or env vars)
- **NO** unvalidated proxies in user-facing endpoints
- **NO** `print()` statements (use `logging.logger`)
- **NO** raw exception returns to users (use global handler)
- **NO** row-by-row inserts for bulk data (use bulk upsert)
- **NO** looped COUNT queries (use GROUP BY)
- **NO** missing `selectinload()` on relationships accessed in loops

## KNOWN ISSUES
- **Duplicate `app` declaration**: `main.py` has two `app = FastAPI()` statements (merge artifact)
- **Regex duplication**: IP validation exists in both `grabber/patterns.py` and `validator.py`
- **Base64 padding logic**: Duplicated in `utils/base64_decoder.py` and `grabber/parsers.py`
