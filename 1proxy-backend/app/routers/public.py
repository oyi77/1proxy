"""Public endpoints — no auth required (or lightweight auth)."""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

from app.database import get_db
from app.db_storage import db_storage

router = APIRouter(tags=["public"])


@router.get("/")
@limiter.limit("200/minute")
async def root(request: Request):
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


@router.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request, session: AsyncSession = Depends(get_db)):
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


@router.get("/api/v1/stats")
@limiter.limit("60/minute")
async def get_stats(request: Request, session: AsyncSession = Depends(get_db)):
    stats = await db_storage.get_stats(session)
    user_count = await db_storage.count_users(session)
    source_count = await db_storage.count_sources(session)
    stats["total_users"] = user_count
    stats["total_sources"] = source_count
    return stats


@router.get("/api/v1/sources")
@limiter.limit("60/minute")
async def list_sources(request: Request, session: AsyncSession = Depends(get_db)):
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
