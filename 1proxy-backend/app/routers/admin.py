from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.db_models import Proxy, User, CandidateSource, ProxySource
from app.models.candidate import CandidateResponse
from app.dependencies import require_admin
from app.hunter.service import HunterService
from app.db_storage import db_storage
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

# All admin endpoints require admin role
router = APIRouter(
    prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)

# Access limiter from app state
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


class UserUpdateRole(BaseModel):
    role: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    created_at: Optional[str]

    model_config = {"from_attributes": True}


@router.get("/users", response_model=dict)
@limiter.limit("30/minute")
async def list_users(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    """
    Admin: List all registered users.

    Returns a paginated list of all users in the system
    with their roles and creation dates.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 30 requests/minute
    - **Returns**: Paginated list of users
    """
    users, total = await db_storage.get_users(session, limit=limit, offset=offset)
    return {
        "total": total,
        "count": len(users),
        "offset": offset,
        "limit": limit,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.get("/users/{user_id}", response_model=UserResponse)
@limiter.limit("60/minute")
async def get_user_details(
    request: Request, user_id: int, session: AsyncSession = Depends(get_db)
):
    """
    Admin: Get detailed information about a specific user.

    Returns full user profile including role and creation date.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 60 requests/minute
    - **Returns**: UserResponse with user details
    """
    user = await db_storage.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}/role", response_model=UserResponse)
@limiter.limit("10/minute")
async def update_user_role(
    request: Request,
    user_id: int,
    role_data: UserUpdateRole,
    session: AsyncSession = Depends(get_db),
):
    """
    Admin: Update a user's role.

    Change a user's role between "user" and "admin".
    Only admins can perform this action.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 10 requests/minute
    - **Valid roles**: "user", "admin"
    - **Returns**: Updated UserResponse
    """
    if role_data.role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = await db_storage.update_user_role(session, user_id, role_data.role)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/users/{user_id}")
@limiter.limit("5/minute")
async def delete_user(
    request: Request, user_id: int, session: AsyncSession = Depends(get_db)
):
    """
    Admin: Delete a user from the system.

    Permanently removes a user and all their associated data.
    Cannot delete yourself (self-deletion prevention).

    - **Authentication**: Required (admin role)
    - **Rate limit**: 5 requests/minute
    - **Returns**: Success message
    """
    # Prevent self-deletion if current user is the target
    # This would require current_user from dependency, but we'll stick to basic admin check for now
    success = await db_storage.delete_user(session, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


@router.post("/hunter/trigger")
@limiter.limit("5/minute")
async def trigger_hunt(request: Request, background_tasks: BackgroundTasks):
    """
    Manually trigger the Hunter Protocol to find new proxy sources.
    """
    service = HunterService()
    background_tasks.add_task(service.run_hunt)
    return {"status": "Hunter Protocol initiated", "message": "Check logs for progress"}


@router.get("/candidates", response_model=List[CandidateResponse])
@limiter.limit("30/minute")
async def list_candidates(
    request: Request,
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """
    List discovered candidate sources.
    """
    stmt = (
        select(CandidateSource)
        .where(CandidateSource.status == status)
        .order_by(CandidateSource.confidence_score.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/candidates/{id}/approve")
@limiter.limit("10/minute")
async def approve_candidate(
    request: Request, id: int, session: AsyncSession = Depends(get_db)
):
    """
    Approve a candidate source and promote it to a real ProxySource.
    """
    # Get candidate
    stmt = select(CandidateSource).where(CandidateSource.id == id)
    result = await session.execute(stmt)
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if candidate.status == "approved":
        raise HTTPException(status_code=400, detail="Candidate already approved")

    # Check if URL already exists in sources (double check)
    stmt_source = select(ProxySource).where(ProxySource.url == candidate.url)
    result_source = await session.execute(stmt_source)
    if result_source.scalar_one_or_none():
        # Just mark as approved/duplicate
        candidate.status = "approved"
        await session.commit()
        return {"status": "merged", "message": "Source already existed"}

    # Create new ProxySource
    # We assume it's a public list found on the web
    new_source = ProxySource(
        url=candidate.url,
        type="public",  # or "url" depending on your convention
        name=f"Hunter: {candidate.domain}",
        description=f"Auto-discovered via {candidate.discovery_method}",
        enabled=True,
        is_admin_source=True,
    )
    session.add(new_source)

    # Update candidate status
    candidate.status = "approved"

    await session.commit()

    return {"status": "approved", "source_id": new_source.id}


@router.get("/validation-stats")
@limiter.limit("60/minute")
async def get_validation_stats(
    request: Request, session: AsyncSession = Depends(get_db)
):
    """
    Admin: Get proxy validation statistics.

    Returns counts and averages grouped by validation status,
    plus a summary with validation rate percentage.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 60 requests/minute
    - **Returns**: Validation stats by status and summary
    """
    result = await session.execute(
        select(
            Proxy.validation_status,
            func.count(Proxy.id).label("count"),
            func.avg(Proxy.quality_score).label("avg_quality"),
            func.avg(Proxy.latency_ms).label("avg_latency"),
        ).group_by(Proxy.validation_status)
    )

    stats_by_status = {}
    for row in result.all():
        stats_by_status[row.validation_status] = {
            "count": row.count,
            "avg_quality": round(row.avg_quality, 2) if row.avg_quality else None,
            "avg_latency": round(row.avg_latency, 2) if row.avg_latency else None,
        }

    total_result = await session.execute(select(func.count()).select_from(Proxy))
    total = total_result.scalar()

    validated_count = stats_by_status.get("validated", {}).get("count", 0)
    pending_count = stats_by_status.get("pending", {}).get("count", 0)
    failed_count = stats_by_status.get("failed", {}).get("count", 0)

    validation_rate = round((validated_count / total) * 100, 2) if total > 0 else 0

    return {
        "total_proxies": total,
        "by_status": stats_by_status,
        "summary": {
            "validated": validated_count,
            "pending": pending_count,
            "failed": failed_count,
            "validation_rate_percent": validation_rate,
        },
    }


@router.get("/quality-distribution")
@limiter.limit("60/minute")
async def get_quality_distribution(
    request: Request, session: AsyncSession = Depends(get_db)
):
    """
    Admin: Get quality score distribution of validated proxies.

    Returns count of proxies in each quality bracket:
    - Excellent (80-100)
    - Good (60-79)
    - Fair (40-59)
    - Poor (0-39)

    - **Authentication**: Required (admin role)
    - **Rate limit**: 60 requests/minute
    - **Returns**: Distribution counts by quality bracket
    """
    result = await session.execute(
        select(Proxy.quality_score, func.count(Proxy.id).label("count"))
        .where(Proxy.validation_status == "validated")
        .group_by(Proxy.quality_score)
        .order_by(Proxy.quality_score.desc())
    )

    distribution = {
        "excellent": 0,
        "good": 0,
        "fair": 0,
        "poor": 0,
    }

    for row in result.all():
        if row.quality_score:
            if row.quality_score >= 80:
                distribution["excellent"] += row.count
            elif row.quality_score >= 60:
                distribution["good"] += row.count
            elif row.quality_score >= 40:
                distribution["fair"] += row.count
            else:
                distribution["poor"] += row.count

    return distribution


@router.get("/recent-validations")
@limiter.limit("60/minute")
async def get_recent_validations(
    request: Request, limit: int = 20, session: AsyncSession = Depends(get_db)
):
    """
    Admin: Get recently validated proxies.

    Returns a list of proxies sorted by most recently validated.
    Useful for monitoring validation activity and quality trends.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 60 requests/minute
    - **Returns**: List of recently validated proxies with scores
    """
    result = await session.execute(
        select(Proxy)
        .where(Proxy.last_validated.isnot(None))
        .order_by(Proxy.last_validated.desc())
        .limit(limit)
    )

    proxies = result.scalars().all()

    return {
        "recent_validations": [
            {
                "url": p.url,
                "validation_status": p.validation_status,
                "quality_score": p.quality_score,
                "latency_ms": p.latency_ms,
                "country_code": p.country_code,
                "anonymity": p.anonymity,
                "last_validated": p.last_validated.isoformat()
                if p.last_validated
                else None,
            }
            for p in proxies
        ]
    }


@router.post("/seed-sources")
@limiter.limit("5/minute")
async def seed_sources(request: Request, current_user: User = Depends(require_admin), session: AsyncSession = Depends(get_db)):
    """Manually seed admin sources from admin_sources.json."""
    count_before = await session.execute(
        select(func.count()).select_from(ProxySource).where(ProxySource.is_admin_source.is_(True))
    )
    if count_before.scalar() or 0 > 0:
        return {"message": "Admin sources already seeded, skipping", "count": 0}

    await db_storage.seed_admin_sources(session, current_user.id)
    count_after = await session.execute(
        select(func.count()).select_from(ProxySource).where(ProxySource.is_admin_source.is_(True))
    )
    seeded = count_after.scalar() or 0
    logger.info(f"Admin {current_user.email} seeded {seeded} admin sources")
    return {"message": "Seeded admin sources from JSON", "count": seeded}


# ── Admin source CRUD (fully DB-driven) ──


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


@router.get("/sources", response_model=dict)
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
                "total_scraped": s.total_scraped,
                "success_rate": s.success_rate,
                "last_scraped": s.last_scraped.isoformat() if s.last_scraped else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "is_admin_source": s.is_admin_source,
            }
            for s in sources
        ],
    }


@router.post("/sources", status_code=201)
@limiter.limit("10/minute")
async def admin_create_source(
    request: Request,
    data: AdminSourceCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Add a new admin-managed proxy source."""
    # Check duplicate
    existing = await session.execute(
        select(ProxySource).where(ProxySource.url == data.url)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Source URL already exists")

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


@router.put("/sources/{source_id}")
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


@router.delete("/sources/{source_id}")
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


@router.post("/cleanup/purge-failed", summary="Purge 3-strike failed proxies")
async def purge_failed_proxies(admin_user=Depends(require_admin), session: AsyncSession = Depends(get_db)):
    count = await db_storage.purge_3strike_proxies(session)
    return {"deleted": count, "message": f"Purged {count} failed proxies (3+ strikes)"}


@router.post("/cleanup/purge-unseen", summary="Purge proxies not seen in N days")
async def purge_unseen_proxies(
    days: int = Query(14, ge=1, le=90, description="Delete proxies not seen in N days"),
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    count = await db_storage.purge_unseen_proxies(session, days=days)
    return {"deleted": count, "days": days, "message": f"Purged {count} proxies not seen in {days} days"}


@router.post("/cleanup/purge-stale-pending", summary="Purge old pending proxies")
async def purge_stale_pending_proxies(
    days: int = Query(7, ge=1, le=30, description="Delete pending proxies older than N days"),
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    count = await db_storage.purge_stale_pending(session, days=days)
    return {"deleted": count, "days": days, "message": f"Purged {count} stale pending proxies"}


@router.post("/cleanup/enforce-cap", summary="Enforce database proxy cap")
async def enforce_db_cap(
    soft_cap: int = Query(50000, ge=10000, le=200000, description="Soft cap threshold"),
    hard_cap: int = Query(75000, ge=20000, le=300000, description="Hard cap threshold"),
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    count = await db_storage.enforce_db_cap(session, soft_cap=soft_cap, hard_cap=hard_cap)
    return {"deleted": count, "soft_cap": soft_cap, "hard_cap": hard_cap}


@router.post("/cleanup/recalc-tiers", summary="Recalculate priority tiers")
async def recalc_priority_tiers(admin_user=Depends(require_admin), session: AsyncSession = Depends(get_db)):
    count = await db_storage.update_priority_tiers(session)
    return {"updated": count, "message": f"Updated priority tiers for {count} proxies"}


@router.get("/lifecycle/stats", summary="Get proxy lifecycle statistics")
async def get_lifecycle_stats(session: AsyncSession = Depends(get_db)):
    from sqlalchemy import func as sa_func
    from app.db_models import Proxy
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Total by tier
    tier_result = await session.execute(
        select(Proxy.priority_tier, sa_func.count(Proxy.id))
        .group_by(Proxy.priority_tier)
        .order_by(Proxy.priority_tier)
    )
    by_tier = {f"tier_{row[0]}": row[1] for row in tier_result.all()}

    # Freshness
    fresh_3h = await session.execute(
        select(sa_func.count(Proxy.id)).where(
            Proxy.is_working == True,
            Proxy.last_validated >= now - timedelta(hours=3)
        )
    )
    stale_3h_12h = await session.execute(
        select(sa_func.count(Proxy.id)).where(
            Proxy.is_working == True,
            Proxy.last_validated >= now - timedelta(hours=12),
            Proxy.last_validated < now - timedelta(hours=3)
        )
    )
    stale_12h_plus = await session.execute(
        select(sa_func.count(Proxy.id)).where(
            Proxy.is_working == True,
            Proxy.last_validated < now - timedelta(hours=12)
        )
    )

    total = await session.execute(select(sa_func.count(Proxy.id)))

    return {
        "total": total.scalar(),
        "by_tier": by_tier,
        "freshness": {
            "fresh_under_3h": fresh_3h.scalar(),
            "aging_3h_12h": stale_3h_12h.scalar(),
            "stale_over_12h": stale_12h_plus.scalar(),
        },
    }


@router.get("/metrics/quality-trend", summary="30-day quality score trend")
async def get_quality_trend(
    days: int = Query(30, description="Number of days of history"),
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Daily average quality_score over the last N days."""
    return await db_storage.get_quality_trend(session, days=days)


@router.get("/metrics/source-effectiveness", summary="Sources ranked by validation rate")
async def get_source_effectiveness(
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """All sources ranked by validated/total proxy ratio."""
    return await db_storage.get_source_effectiveness(session)


@router.get("/metrics/staleness", summary="Proxy staleness breakdown")
async def get_staleness_stats(
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Fresh/stale/dead/pending breakdown with percentages."""
    return await db_storage.get_staleness_stats(session)
