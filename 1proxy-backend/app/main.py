# FastAPI Application Entry Point
from app.config import settings

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.models import SourceConfig, SourceType
from app.grabber import GitHubGrabber
from app.sources import SourceRegistry
from app.database import init_db, AsyncSessionLocal, get_db, AsyncSession
from app.db_storage import db_storage
from app.routers import auth, sources, proxies, notifications, validation, admin
from app.dependencies import require_admin
from app.db_models import User
from app.background_validator import background_validation_worker
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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


# CORS middleware configuration - support HF Spaces, GitHub Pages, and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        settings.API_URL,
        "http://localhost:3000",
        "http://localhost:8000",
        "https://*.hf.space",
        "https://*.spaces.huggingface.tech",
        "https://*.github.io",  # GitHub Pages support
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

from app.admin.scraping_admin import router as scraping_admin_router

app.include_router(scraping_admin_router)

grabber = GitHubGrabber()


@app.on_event("startup")
async def startup():
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
            await session.commit()
            logger.info(
                f"✅ Admin user created/verified: {admin_user.username} (ID: {admin_user.id})"
            )
            logger.info("✅ Admin sources seeded")
        except Exception as e:
            logger.warning(f"⚠️  Startup error (non-critical): {e}")
            await session.rollback()

    # STARTUP STABILIZER: Wait for HF Space to pass health check before spawning workers
    async def delayed_workers():
        logger.info("⏳ Stabilizer: Waiting 15s before starting background workers...")
        await asyncio.sleep(15)

        logger.info("🚀 Stabilizer: Spawning background workers...")
        # Start validation worker with reduced batch size for HF
        asyncio.create_task(
            background_validation_worker(batch_size=20, interval_seconds=60)
        )

        # Import and start auto-scraper
        from app.background_validator import background_scraper_worker

        asyncio.create_task(background_scraper_worker(interval_minutes=10))
        logger.info("✅ Stabilizer: Background workers active")

    asyncio.create_task(delayed_workers())


@app.get("/")
async def root():
    return {
        "name": "1proxy API",
        "version": "2.0.0",
        "status": "running",
        "features": {
            "multi_user": True,
            "oauth": ["github", "google"],
            "advanced_filtering": True,
            "export_formats": ["txt", "json", "csv"],
        },
        "endpoints": {
            "health": "/health",
            "auth": "/auth/*",
            "my_sources": "/api/v1/my-sources",
            "advanced_search": "/api/v1/proxies/advanced",
            "export": "/api/v1/proxies/export",
            "public_sources": "/api/v1/sources",
        },
    }


@app.get("/health")
async def health_check(session: AsyncSession = Depends(get_db)):
    proxy_count = await db_storage.count_proxies(session)
    source_count = await db_storage.count_sources(session)
    user_count = await db_storage.count_users(session)
    return {
        "status": "healthy",
        "database": "connected",
        "proxies": proxy_count,
        "sources": source_count,
        "users": user_count,
    }


@app.post("/api/v1/proxies/scrape", response_model=dict)
async def scrape_proxies(
    source: SourceConfig, current_user: User = Depends(require_admin)
):
    async with AsyncSessionLocal() as session:
        try:
            proxies = await grabber.extract_proxies(source)
            proxies_data = []
            for p in proxies:
                data = p.model_dump() if hasattr(p, "model_dump") else p.__dict__
                proxies_data.append(
                    {
                        "url": f"{data.get('protocol', 'http')}://{data.get('ip')}:{data.get('port')}",
                        "protocol": data.get("protocol", "http"),
                        "ip": data.get("ip"),
                        "port": data.get("port"),
                        "country_code": data.get("country_code"),
                        "country_name": data.get("country_name"),
                        "city": data.get("city"),
                        "latency_ms": data.get("latency_ms"),
                        "speed_mbps": data.get("speed_mbps"),
                        "anonymity": data.get("anonymity"),
                        "proxy_type": data.get("proxy_type"),
                    }
                )
            added = await db_storage.add_proxies(session, proxies_data)

            validation_results = await db_storage.validate_and_update_proxies(
                session, limit=min(added, 100)
            )

            return {
                "source": str(source.url),
                "scraped": len(proxies),
                "added": added,
                "validated": validation_results["validated"],
                "failed": validation_results["failed"],
                "total": await db_storage.count_proxies(session),
            }
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Request timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/proxies", response_model=dict)
async def list_proxies(
    protocol: Optional[str] = Query(
        None, description="Filter by protocol (http, vmess, vless, trojan, shadowsocks)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db),
):
    proxies, total = await db_storage.get_proxies(
        session=session, protocol=protocol, limit=limit, offset=offset, is_working=True
    )

    proxy_list = []
    for p in proxies:
        proxy_list.append(
            {
                "id": p.id,
                "url": p.url,
                "protocol": p.protocol,
                "ip": p.ip,
                "port": p.port,
                "country_code": p.country_code,
                "country_name": p.country_name,
                "city": p.city,
                "latency_ms": p.latency_ms,
                "speed_mbps": p.speed_mbps,
                "anonymity": p.anonymity,
                "quality_score": p.quality_score,
                "is_working": p.is_working,
                "last_validated": p.last_validated.isoformat()
                if p.last_validated
                else None,
                "source": str(p.source_id),
            }
        )

    return {
        "total": total,
        "count": len(proxies),
        "offset": offset,
        "limit": limit,
        "proxies": proxy_list,
    }

    return {
        "total": total,
        "count": len(proxies),
        "offset": offset,
        "limit": limit,
        "proxies": proxy_list,
    }


@app.get("/api/v1/stats")
async def get_stats(session: AsyncSession = Depends(get_db)):
    stats = await db_storage.get_stats(session)
    user_count = await db_storage.count_users(session)
    source_count = await db_storage.count_sources(session)

    stats["total_users"] = user_count
    stats["total_sources"] = source_count

    return stats


@app.post("/api/v1/proxies/demo")
async def demo_scrape(current_user: User = Depends(require_admin)):
    async with AsyncSessionLocal() as session:
        source = SourceConfig(
            url="https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            type=SourceType.GITHUB_RAW,
        )
        try:
            proxies = await grabber.extract_proxies(source)
            proxies_data = []
            sample_list = []
            for p in proxies:
                data = p.model_dump() if hasattr(p, "model_dump") else p.__dict__
                proxy_data = {
                    "url": f"{data.get('protocol', 'http')}://{data.get('ip')}:{data.get('port')}",
                    "protocol": data.get("protocol", "http"),
                    "ip": data.get("ip"),
                    "port": data.get("port"),
                    "country_code": data.get("country_code"),
                    "country_name": data.get("country_name"),
                    "city": data.get("city"),
                    "latency_ms": data.get("latency_ms"),
                    "speed_mbps": data.get("speed_mbps"),
                    "anonymity": data.get("anonymity"),
                    "proxy_type": data.get("proxy_type"),
                }
                proxies_data.append(proxy_data)
                if len(sample_list) < 5:
                    sample_list.append(data)

            added = await db_storage.add_proxies(session, proxies_data)

            validation_results = await db_storage.validate_and_update_proxies(
                session, limit=min(added, 50)
            )

            return {
                "message": "Demo scrape completed",
                "source": str(source.url),
                "scraped": len(proxies),
                "added": added,
                "validated": validation_results["validated"],
                "failed": validation_results["failed"],
                "total_stored": await db_storage.count_proxies(session),
                "sample": sample_list,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sources")
async def list_sources(session: AsyncSession = Depends(get_db)):
    sources = await db_storage.get_sources(session, enabled_only=False)
    return {
        "total": len(sources),
        "enabled": len([s for s in sources if s.enabled]),
        "sources": [
            {
                "id": s.id,
                "url": s.url,
                "type": s.type,
                "enabled": s.enabled,
                "name": s.name,
                "is_admin_source": s.is_admin_source,
                "validated": s.validated,
                "total_scraped": s.total_scraped,
            }
            for s in sources
        ],
    }


@app.post("/api/v1/proxies/scrape-all")
async def scrape_all_sources(current_user: User = Depends(require_admin)):
    async with AsyncSessionLocal() as session:
        sources = SourceRegistry.get_enabled_sources()
        results = []
        total_scraped = 0
        total_added = 0
        total_validated = 0
        total_failed = 0

        for source in sources:
            try:
                proxies = await grabber.extract_proxies(source)
                proxies_data = []
                for p in proxies:
                    data = p.model_dump() if hasattr(p, "model_dump") else p.__dict__
                    proxies_data.append(
                        {
                            "url": f"{data.get('protocol', 'http')}://{data.get('ip')}:{data.get('port')}",
                            "protocol": data.get("protocol", "http"),
                            "ip": data.get("ip"),
                            "port": data.get("port"),
                            "country_code": data.get("country_code"),
                            "country_name": data.get("country_name"),
                            "city": data.get("city"),
                            "latency_ms": data.get("latency_ms"),
                            "speed_mbps": data.get("speed_mbps"),
                            "anonymity": data.get("anonymity"),
                            "proxy_type": data.get("proxy_type"),
                        }
                    )
                added = await db_storage.add_proxies(session, proxies_data)

                validation_results = await db_storage.validate_and_update_proxies(
                    session, limit=min(added, 50)
                )

                total_scraped += len(proxies)
                total_added += added
                total_validated += validation_results["validated"]
                total_failed += validation_results["failed"]
                results.append(
                    {
                        "url": str(source.url),
                        "status": "success",
                        "scraped": len(proxies),
                        "added": added,
                        "validated": validation_results["validated"],
                        "failed": validation_results["failed"],
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "url": str(source.url),
                        "status": "failed",
                        "error": str(e),
                        "scraped": 0,
                        "added": 0,
                        "validated": 0,
                        "failed": 0,
                    }
                )

        return {
            "message": f"Scraped {len(sources)} sources",
            "total_scraped": total_scraped,
            "total_added": total_added,
            "total_validated": total_validated,
            "total_failed": total_failed,
            "total_stored": await db_storage.count_proxies(session),
            "results": results,
        }


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
