"""Admin stats/metrics endpoints — validation stats, quality distribution, lifecycle stats, trends."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.db_models import Proxy
from app.dependencies import require_admin
from app.db_storage import db_storage
from datetime import datetime, timedelta, timezone
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

stats_router = APIRouter()


@stats_router.get("/validation-stats")
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


@stats_router.get("/quality-distribution")
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


@stats_router.get("/recent-validations")
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


@stats_router.get("/lifecycle/stats", summary="Get proxy lifecycle statistics")
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
            Proxy.last_validated >= now - timedelta(hours=3),
        )
    )
    stale_3h_12h = await session.execute(
        select(sa_func.count(Proxy.id)).where(
            Proxy.is_working == True,
            Proxy.last_validated >= now - timedelta(hours=12),
            Proxy.last_validated < now - timedelta(hours=3),
        )
    )
    stale_12h_plus = await session.execute(
        select(sa_func.count(Proxy.id)).where(
            Proxy.is_working == True,
            Proxy.last_validated < now - timedelta(hours=12),
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


@stats_router.get("/metrics/quality-trend", summary="30-day quality score trend")
async def get_quality_trend(
    days: int = Query(30, description="Number of days of history"),
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Daily average quality_score over the last N days."""
    return await db_storage.get_quality_trend(session, days=days)


@stats_router.get("/metrics/source-effectiveness", summary="Sources ranked by validation rate")
async def get_source_effectiveness(
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """All sources ranked by validated/total proxy ratio."""
    return await db_storage.get_source_effectiveness(session)


@stats_router.get("/metrics/staleness", summary="Proxy staleness breakdown")
async def get_staleness_stats(
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Fresh/stale/dead/pending breakdown with percentages."""
    return await db_storage.get_staleness_stats(session)


@stats_router.get("/workers/health", summary="Background worker health status")
async def get_worker_health(
    request: Request,
    admin_user=Depends(require_admin),
):
    """Returns heartbeat status of all registered background workers."""
    from app.worker_heartbeat import worker_heartbeats

    return {"workers": worker_heartbeats}
