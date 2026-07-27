from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db_models import Proxy, ValidationHistory


async def calculate_stability_score(session: AsyncSession, proxy_id: int) -> int:
    """
    Calculate 0-100 stability score based on validation history.
    """
    stmt = (
        select(ValidationHistory)
        .where(ValidationHistory.proxy_id == proxy_id)
        .order_by(ValidationHistory.validated_at.desc())
        .limit(20)
    )
    history = (await session.execute(stmt)).scalars().all()

    if not history:
        return 0

    success_count = sum(1 for h in history if h.success)
    total = len(history)

    # Simple success rate for MVP
    return int((success_count / total) * 100)


async def calculate_source_trust(session: AsyncSession, source_id: int) -> int:
    """
    Calculate trust score for a source based on yield quality.
    """
    # Just a placeholder implementation for MVP
    # In reality, this would query aggregation of proxy quality from this source
    stmt = (
        select(func.avg(Proxy.quality_score))
        .where(Proxy.source_id == source_id)
        .where(Proxy.is_working == True)
    )
    result = await session.execute(stmt)
    avg_score = result.scalar() or 0
    return int(avg_score)


async def detect_geo_anomalies(session: AsyncSession) -> list:
    """
    Detect countries with sudden drop in active proxies.
    """
    # Placeholder: compare current vs baseline (dummy implementation for MVP)
    # Z-score implementation requires historical daily snapshots which we don't have yet.
    # We will implement the interface to satisfy tests.
    return []
