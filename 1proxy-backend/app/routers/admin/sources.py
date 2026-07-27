"""Admin source management endpoints — seed sources, CRUD for admin proxy sources."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.db_models import ProxySource, User
from app.dependencies import require_admin
from app.db_storage import db_storage
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

sources_router = APIRouter()


@sources_router.post("/seed-sources")
@limiter.limit("5/minute")
async def seed_sources(
    request: Request,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Manually seed admin sources from admin_sources.json."""
    count_before = await session.execute(
        select(func.count())
        .select_from(ProxySource)
        .where(ProxySource.is_admin_source.is_(True))
    )
    existing = count_before.scalar() or 0
    if existing > 0:
        return {"message": f"Already seeded ({existing} admin sources exist)", "count": 0}

    await db_storage.seed_admin_sources(session, current_user.id)

    count_after = await session.execute(
        select(func.count())
        .select_from(ProxySource)
        .where(ProxySource.is_admin_source.is_(True))
    )
    seeded = (count_after.scalar() or 0) - existing
    logger.info(f"Admin {current_user.email} seeded {seeded} admin sources")
    return {"message": f"Seeded {seeded} admin sources from JSON", "count": seeded}


# ── Models ──


class AdminSourceCreate(BaseModel):
    url: str
    type: str
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True


class AdminSourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    url: Optional[str] = None
    type: Optional[str] = None


# ── CRUD endpoints ──


@sources_router.get("/sources", response_model=dict)
@limiter.limit("30/minute")
async def admin_list_sources(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """List all admin-managed proxy sources."""
    sources, total = await db_storage.get_admin_sources(session, limit=limit, offset=offset)
    return {
        "total": total,
        "count": len(sources),
        "offset": offset,
        "limit": limit,
        "sources": [
            {
                "id": s.id,
                "url": s.url,
                "type": s.type,
                "name": s.name,
                "description": s.description,
                "enabled": s.enabled,
                "validated": s.validated,
                "validation_error": s.validation_error,
                "total_scraped": s.total_scraped,
                "success_rate": s.success_rate,
                "last_scraped": s.last_scraped.isoformat() if s.last_scraped else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "is_admin_source": s.is_admin_source,
            }
            for s in sources
        ],
    }


@sources_router.post("/sources", status_code=201)
@limiter.limit("10/minute")
async def admin_create_source(
    request: Request,
    data: AdminSourceCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Add a new admin-managed proxy source. Validates by scraping first."""
    # Check duplicate
    existing = await session.execute(
        select(ProxySource).where(ProxySource.url == data.url)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Source URL already exists")

    # Quick validation: try scraping to see if source yields proxies
    from app.models import SourceConfig, SourceType
    from app.grabber import GitHubGrabber, WebGrabber

    try:
        source_config = SourceConfig(url=data.url, type=SourceType(data.type))
        if source_config.type in (SourceType.GENERIC_TEXT, SourceType.TOR_EXIT):
            grabber = WebGrabber()
        else:
            grabber = GitHubGrabber()

        proxies = await grabber.extract_proxies(source_config)
        if not proxies:
            raise HTTPException(
                status_code=422,
                detail="Source validated but no proxies found. Check the URL format.",
            )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid source: {e}")
    except Exception as e:
        logger.warning(f"Source validation scrape failed: {e}")
        # Allow creation even if scrape fails — background will retry

    source = await db_storage.create_admin_source(
        session=session,
        url=data.url,
        source_type=data.type,
        admin_user_id=current_user.id,
        name=data.name,
        description=data.description,
        enabled=data.enabled,
    )
    logger.info(f"Admin {current_user.email} created source #{source.id} — {data.url}")
    return {
        "message": "Admin source created",
        "source_id": source.id,
        "url": source.url,
        "type": source.type,
        "name": source.name,
    }


@sources_router.put("/sources/{source_id}")
@limiter.limit("30/minute")
async def admin_update_source(
    request: Request,
    source_id: int,
    data: AdminSourceUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Update an admin-managed proxy source."""
    source = await db_storage.update_admin_source(
        session=session,
        source_id=source_id,
        **data.model_dump(exclude_none=True),
    )
    if not source:
        raise HTTPException(status_code=404, detail="Admin source not found")
    logger.info(f"Admin {current_user.email} updated source #{source_id} — {source.url}")
    return {
        "message": "Source updated",
        "id": source.id,
        "url": source.url,
        "type": source.type,
        "name": source.name,
        "enabled": source.enabled,
    }


@sources_router.delete("/sources/{source_id}")
@limiter.limit("10/minute")
async def admin_delete_source(
    request: Request,
    source_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Delete an admin-managed proxy source."""
    deleted = await db_storage.delete_admin_source(session, source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Admin source not found")
    logger.info(f"Admin {current_user.email} deleted source #{source_id}")
    return {"message": "Source deleted", "source_id": source_id}


@sources_router.post("/sources/{source_id}/scrape")
@limiter.limit("10/minute")
async def admin_scrape_source(
    request: Request,
    source_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Scrape a single admin source immediately (test)."""
    from app.models import SourceConfig, SourceType
    from app.grabber import GitHubGrabber, WebGrabber

    result = await session.execute(
        select(ProxySource).where(ProxySource.id == source_id, ProxySource.is_admin_source.is_(True))
    )
    source_db = result.scalar_one_or_none()
    if not source_db:
        raise HTTPException(status_code=404, detail="Admin source not found")

    try:
        source_config = SourceConfig(url=source_db.url, type=SourceType(source_db.type))
        if source_config.type in (SourceType.GENERIC_TEXT, SourceType.TOR_EXIT):
            grabber = WebGrabber()
        else:
            grabber = GitHubGrabber()

        proxies = await grabber.extract_proxies(source_config)
        count = len(proxies)
        sample = [f"{p.ip}:{p.port}" for p in proxies[:5]] if proxies else []

        # Update source stats
        source_db.last_scraped = datetime.now(timezone.utc).replace(tzinfo=None)
        source_db.total_scraped = (source_db.total_scraped or 0) + count
        source_db.validated = count > 0

        if count > 0:
            # Re-enable if it was disabled
            source_db.enabled = True
            source_db.validation_error = None

        await session.commit()
        logger.info(f"Admin {current_user.email} scraped source #{source_id}: {count} proxies")

        return {
            "source_id": source_id,
            "url": source_db.url,
            "scraped": count,
            "sample": sample,
            "re_enabled": count > 0,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid source: {e}")
    except Exception as e:
        logger.error(f"Scrape failed for source #{source_id}: {e}")
        return {
            "source_id": source_id,
            "url": source_db.url,
            "error": str(e),
            "scraped": 0,
            "sample": [],
        }


@sources_router.post("/sources/{source_id}/revive")
@limiter.limit("10/minute")
async def admin_revive_source(
    request: Request,
    source_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Re-enable a disabled source and reset its error state."""
    result = await session.execute(
        select(ProxySource).where(ProxySource.id == source_id, ProxySource.is_admin_source.is_(True))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Admin source not found")

    source.enabled = True
    source.validation_error = None
    await session.commit()
    await session.refresh(source)
    logger.info(f"Admin {current_user.email} revived source #{source_id}")
    return {"message": "Source revived", "id": source.id, "enabled": source.enabled}


@sources_router.post("/sources/{source_id}/protect")
@limiter.limit("10/minute")
async def admin_protect_source(
    request: Request,
    source_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Mark a source as admin-protected (prevents user deletion)."""
    result = await session.execute(
        select(ProxySource).where(ProxySource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.is_admin_source = True
    await session.commit()
    await session.refresh(source)
    logger.info(f"Admin {current_user.email} protected source #{source_id}")
    return {
        "message": "Source protected",
        "id": source.id,
        "url": source.url,
        "is_admin_source": source.is_admin_source,
    }
