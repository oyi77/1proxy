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

    class Config:
        from_attributes = True


@router.get("/users", response_model=dict)
@limiter.limit("30/minute")
async def list_users(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
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
async def seed_sources(request: Request, session: AsyncSession = Depends(get_db)):
    """
    Manually seed admin sources. Use if sources are empty.
    """
    from app.sources import SourceRegistry

    admin_user = await session.execute(
        select(User).where(User.role == "admin").limit(1)
    )
    admin = admin_user.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=400, detail="No admin user found")

    count = 0
    for source_config in SourceRegistry.SOURCES:
        existing = await session.execute(
            select(ProxySource).where(ProxySource.url == str(source_config.url))
        )
        if not existing.scalar_one_or_none():
            source = ProxySource(
                user_id=admin.id,
                url=str(source_config.url),
                type=source_config.type.value if hasattr(source_config.type, "value") else str(source_config.type),
                name=str(source_config.url).split("/")[-2],
                enabled=source_config.enabled,
                validated=True,
                is_admin_source=True,
                is_paid=False,
            )
            session.add(source)
            count += 1

    await session.commit()
    return {"message": f"Seeded {count} sources"}
