from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.db_models import Proxy

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/validation-stats")
async def get_validation_stats(session: AsyncSession = Depends(get_db)):
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
async def get_quality_distribution(session: AsyncSession = Depends(get_db)):
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
async def get_recent_validations(
    limit: int = 20, session: AsyncSession = Depends(get_db)
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
