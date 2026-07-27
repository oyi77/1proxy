# FastAPI Application Entry Point
from app.config import settings

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database import (
    init_db,
    AsyncSessionLocal,
    get_db,
    AsyncSession,
    database_keepalive_worker,
    dispose_database,
)
from app.db_storage import db_storage
from app.routers import auth, sources, proxies, notifications, validation, admin
from app.routers import public, scrape
from app.admin.scraping_admin import router as scraping_admin_router
from app.db_models import User
from app.background_validator import background_validation_worker
from app.lifecycle_workers import revalidation_worker, cleanup_worker, priority_tier_worker
from app.metrics import metrics_app
import asyncio
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup initialisation and shutdown cleanup."""
    # --- STARTUP ---
    app.state.background_tasks = set()
    await init_db()

    async with AsyncSessionLocal() as session:
        try:
            admin_user = await db_storage.get_or_create_user(
                session=session,
                oauth_provider="local",
                oauth_id="admin",
                email="admin@1proxy.local",
                username="admin",
                role="admin",
            )
            await db_storage.seed_admin_sources(session, admin_user.id)
            logger.info(
                f"✅ Admin user created/verified: {admin_user.username} (ID: {admin_user.id})"
            )
        except Exception as e:
            logger.warning(f"⚠️  Startup error (non-critical): {e}")
            await session.rollback()

    # STARTUP STABILIZER: Let Railway pass health checks before spawning workers.
    async def delayed_workers():
        logger.info("⏳ Stabilizer: Waiting 15s before starting background workers...")
        await asyncio.sleep(15)

        logger.info("🚀 Stabilizer: Spawning background workers (staggered)...")
        # Start validation worker with a conservative production batch size.
        _track_background_task(
            background_validation_worker(batch_size=20, interval_seconds=60),
            "proxy-validation-worker",
        )
        await asyncio.sleep(2)  # Stagger to reduce SQLite contention

        # Import and start auto-scraper
        from app.background_validator import background_scraper_worker

        _track_background_task(
            background_scraper_worker(interval_minutes=10), "proxy-scraper-worker"
        )
        await asyncio.sleep(2)

        _track_background_task(
            database_keepalive_worker(interval_seconds=300),
            "database-keepalive-worker",
        )
        await asyncio.sleep(1)

        _track_background_task(
            revalidation_worker(batch_size=20, interval_seconds=60),
            "proxy-revalidation-worker",
        )
        await asyncio.sleep(1)

        _track_background_task(
            cleanup_worker(interval_minutes=30),
            "proxy-cleanup-worker",
        )
        await asyncio.sleep(1)

        _track_background_task(
            priority_tier_worker(interval_hours=6),
            "proxy-tier-worker",
        )
        await asyncio.sleep(1)

        # Continuous lightweight healthcheck for the "working" pool
        from app.healthcheck_worker import healthcheck_worker

        _track_background_task(
            healthcheck_worker(),
            "proxy-healthcheck-worker",
        )
        logger.info("✅ Stabilizer: Background workers active")

    _track_background_task(delayed_workers(), "startup-delayed-workers")

    yield

    # --- SHUTDOWN ---
    tasks = getattr(app.state, "background_tasks", set())
    for task in list(tasks):
        task.cancel()

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    await dispose_database()


app = FastAPI(
    lifespan=lifespan,
    description="""
## Community-Driven Proxy Aggregation Platform

1proxy provides a high-performance, multi-user proxy aggregation platform where anyone can contribute proxy sources while maintaining public access to all validated proxies.

### Key Features
- **Multi-Protocol Support**: HTTP, HTTPS, SOCKS4, SOCKS5, VMess, VLESS, Trojan, Shadowsocks
- **Advanced Filtering**: Filter by protocol, country, anonymity level, quality score, speed, and validation status
- **Quality Scoring**: 0-100 score based on latency, anonymity, Google access, and residential bonus
- **Multi-User OAuth**: GitHub and Google authentication with role-based access control
- **Auto-Discovery**: Hunter Protocol for automatic proxy source discovery
- **Background Workers**: Continuous scraping and validation with configurable intervals
- **Export Options**: Download proxies in TXT, JSON, CSV, or PAC format

### Authentication
Most endpoints are public. To contribute sources or access personal data, use OAuth login via `/auth/github` or `/auth/google`.
Protected endpoints require a Bearer token in the `Authorization` header.

### Rate Limiting
- Public endpoints: 100 requests/hour
- Authenticated endpoints: 60 requests/minute
- Admin endpoints: 30 requests/minute

### Contact
- GitHub: [oyi77/1proxy](https://github.com/oyi77/1proxy)
- API Base URL: https://1proxy-api.aitradepulse.com
- Frontend: https://oyi77.is-a.dev/1proxy/
""",
    version="2.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    contact={
        "name": "1proxy Support",
        "url": "https://github.com/oyi77/1proxy/issues",
        "email": "support@1proxy.example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/oyi77/1proxy/blob/main/LICENSE",
    },
    servers=[
        {"url": "https://1proxy-api.aitradepulse.com", "description": "Production server (Railway)"},
        {"url": "http://localhost:8000", "description": "Local development server"},
    ],
    tags_metadata=[
        {
            "name": "authentication",
            "description": "OAuth2 authentication endpoints for GitHub and Google providers. Handle login, callbacks, and user profile access.",
        },
        {
            "name": "proxies",
            "description": "Proxy browsing, filtering, export, and testing. Public endpoints for accessing validated proxies with advanced filtering options.",
        },
        {
            "name": "sources",
            "description": "Proxy source management. Users can add, update, and monitor their own sources. Admin endpoints for global source management.",
        },
        {
            "name": "validation",
            "description": "On-demand proxy validation. Test individual proxies for connectivity, anonymity level, and quality scoring.",
        },
        {
            "name": "admin",
            "description": "Administrative endpoints for user management, platform statistics, and system health. Requires admin role.",
        },
        {
            "name": "notifications",
            "description": "User notification system. Retrieve and manage in-app notifications for source validation results and system alerts.",
        },
    ],
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount Prometheus metrics
app.mount("/metrics", metrics_app)


# Global exception handler to prevent leaking internal errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions and return a safe error message.
    Log the full error details for debugging.
    """
    import uuid
    import traceback

    error_id = str(uuid.uuid4())[:8]
    logger.error(
        f"Unhandled exception [{error_id}]: {exc}",
        exc_info=True,
        extra={
            "error_id": error_id,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "error_id": error_id,
        },
    )


# CORS middleware configuration - support Railway, GitHub Pages, and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        settings.API_URL,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://*.github.io",  # GitHub Pages support
        "https://*.railway.app",  # Railway support
        "https://oyi77.is-a.dev",  # Main domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Next.js frontend static files (built with standalone output)
# Check multiple possible locations for the frontend build
frontend_paths = [
    "/app/frontend",
    "/app/1proxy-frontend",
    os.path.join(os.path.dirname(__file__), "../../1proxy-frontend"),
]

frontend_path = None
for fp in frontend_paths:
    if os.path.exists(os.path.join(fp, "server.js")):
        frontend_path = fp
        break

if frontend_path:
    logger.info(f"📦 Serving frontend from: {frontend_path}")
    # Mount the Next.js build output
    app.mount(
        "/static",
        StaticFiles(directory=os.path.join(frontend_path, ".next/static")),
        name="static",
    )
    app.mount("/_next", StaticFiles(directory=frontend_path), name="next")

    @app.get("/favicon.ico")
    async def favicon():
        favicon_path = os.path.join(frontend_path, "public/favicon.ico")
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path)
        return JSONResponse(status_code=204, content={})


app.include_router(auth.router)
app.include_router(sources.router)
app.include_router(proxies.router)
app.include_router(notifications.router)
app.include_router(validation.router)
app.include_router(admin.router)
app.include_router(scraping_admin_router)
app.include_router(public.router)
app.include_router(scrape.router)


def _track_background_task(coro, name: str):
    def _on_done(task: asyncio.Task):
        app.state.background_tasks.discard(task)
        if task.cancelled():
            logger.info(f"⏹️  Background task cancelled: {name}")
        elif exc := task.exception():
            logger.error(f"💥 Background task crashed: {name} — {exc}")
    task = asyncio.create_task(coro, name=name)
    app.state.background_tasks.add(task)
    task.add_done_callback(_on_done)
    return task


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
