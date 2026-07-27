from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from typing import List
from datetime import datetime, timedelta, timezone
import logging

from app.db_models import Proxy

logger = logging.getLogger(__name__)


class StatsRepository:
    async def get_stats(self, session: AsyncSession) -> dict:
        """
        Get proxy statistics efficiently using a single GROUP BY query
        instead of multiple separate queries.
        """
        # Apply TTL filter - only count visible (non-stale working) proxies
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3)
        # Single query with GROUP BY for protocol counts
        result = await session.execute(
            select(Proxy.protocol, func.count(Proxy.id).label("count")).
            where(Proxy.is_working.is_(True), Proxy.last_validated >= cutoff).
            group_by(Proxy.protocol)
        )

        by_protocol = {}
        total = 0

        for row in result:
            protocol = row.protocol if row.protocol else "unknown"
            count = row.count
            by_protocol[protocol] = count
            total += count

        # Ensure all expected protocols are present (even if 0)
        expected_protocols = [
            "http",
            "https",
            "vmess",
            "vless",
            "trojan",
            "shadowsocks",
        ]
        for protocol in expected_protocols:
            if protocol not in by_protocol:
                by_protocol[protocol] = 0

        return {"total_proxies": total, "by_protocol": by_protocol}

    async def get_quality_trend(self, session: AsyncSession, days: int = 30) -> List[dict]:
        """Daily avg quality_score over the last N days."""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        rows = await session.execute(
            select(
                func.date(Proxy.last_validated).label("date"),
                func.avg(Proxy.quality_score).label("avg_quality"),
                func.count(Proxy.id).label("proxy_count"),
            )
            .where(
                Proxy.last_validated >= cutoff,
                Proxy.quality_score.isnot(None),
                Proxy.validation_status == "validated",
            )
            .group_by(func.date(Proxy.last_validated))
            .order_by(func.date(Proxy.last_validated))
        )
        return [
            {
                "date": str(row.date),
                "avg_quality": round(float(row.avg_quality), 1) if row.avg_quality else 0,
                "proxy_count": row.proxy_count,
            }
            for row in rows
        ]

    async def get_staleness_stats(self, session: AsyncSession) -> dict:
        """Proxy staleness breakdown."""
        total = await session.scalar(select(func.count(Proxy.id)))
        if not total:
            total = 0

        # Fresh: validated within 6h
        fresh_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)
        fresh = await session.scalar(
            select(func.count(Proxy.id)).where(
                Proxy.is_working == True,
                Proxy.last_validated >= fresh_cutoff,
            )
        ) or 0

        # Stale: validated > 6h ago but still marked working
        stale = await session.scalar(
            select(func.count(Proxy.id)).where(
                Proxy.is_working == True,
                Proxy.last_validated < fresh_cutoff,
            )
        ) or 0

        # Dead: explicitly failed
        dead = await session.scalar(
            select(func.count(Proxy.id)).where(
                Proxy.is_working == False,
            )
        ) or 0

        # Pending: never validated
        pending = await session.scalar(
            select(func.count(Proxy.id)).where(
                Proxy.validation_status == "pending",
            )
        ) or 0

        return {
            "total": total,
            "fresh": fresh,
            "stale": stale,
            "dead": dead,
            "pending": pending,
            "fresh_pct": round(fresh / total * 100, 1) if total else 0,
            "stale_pct": round(stale / total * 100, 1) if total else 0,
            "dead_pct": round(dead / total * 100, 1) if total else 0,
        }

    async def enforce_db_cap(self, session: AsyncSession, soft_cap: int = 50000, hard_cap: int = 75000) -> int:
        """
        If total > soft_cap, delete lowest priority_tier + oldest first in batches of 5000.
        If total > hard_cap, more aggressively delete.
        """
        total = await session.scalar(select(func.count(Proxy.id)))
        deleted_count = 0

        if total <= soft_cap:
            return 0

        # Determine batch size based on how far over cap we are
        batch_size = 5000 if total <= hard_cap else 10000

        while total > soft_cap:
            subquery = (
                select(Proxy.id)
                .where(Proxy.is_working.is_(False))
                .order_by(Proxy.priority_tier.desc(), Proxy.created_at.asc())
                .limit(batch_size)
            )

            stmt = delete(Proxy).where(Proxy.id.in_(subquery))
            result = await session.execute(stmt)
            batch_deleted = result.rowcount
            deleted_count += batch_deleted

            if batch_deleted == 0:
                break

            total = await session.scalar(select(func.count(Proxy.id)))

        await session.commit()
        return deleted_count

    async def purge_dead_proxies(self, session: AsyncSession, hours: int = 6) -> int:
        """Hard-delete failed proxies not rechecked in N hours.
        Free proxies die in minutes — this keeps the DB clean of corpses."""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        stmt = delete(Proxy).where(
            Proxy.is_working == False,
            Proxy.last_validated < cutoff,
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def soft_stale_proxies(self, session: AsyncSession, hours: int = 24) -> int:
        """Mark proxies as not-working if they haven't been revalidated in N hours.
        They'll be re-tested by the next revalidation cycle and revived if alive."""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        stmt = (
            update(Proxy)
            .where(
                Proxy.is_working == True,
                Proxy.last_validated < cutoff,
                Proxy.validation_status == "validated",
            )
            .values(is_working=False)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def update_priority_tiers(self, session: AsyncSession) -> int:
        """
        Recalculate priority_tier for all proxies:
        - Tier 1: quality_score >= 80 AND anonymity='elite'
        - Tier 2: quality_score >= 60 AND anonymity IN ('elite', 'anonymous')
        - Tier 3: is_working=True (otherwise)
        - Tier 4: everything else (new, pending, etc.)
        """
        # Tier 1: quality_score >= 80 AND anonymity='elite'
        stmt1 = (
            update(Proxy)
            .where(Proxy.quality_score >= 80, Proxy.anonymity == "elite")
            .values(priority_tier=1)
        )
        result1 = await session.execute(stmt1)

        # Tier 2: quality_score >= 60 AND anonymity IN ('elite', 'anonymous')
        stmt2 = (
            update(Proxy)
            .where(
                Proxy.quality_score >= 60,
                Proxy.anonymity.in_(["elite", "anonymous"]),
                Proxy.priority_tier != 1,  # Don't override tier 1
            )
            .values(priority_tier=2)
        )
        result2 = await session.execute(stmt2)

        # Tier 3: is_working=True (but not already tier 1 or 2)
        stmt3 = (
            update(Proxy)
            .where(
                Proxy.is_working.is_(True),
                Proxy.priority_tier.notin_([1, 2]),
            )
            .values(priority_tier=3)
        )
        result3 = await session.execute(stmt3)

        # Tier 4: everything else (new, pending, etc.)
        stmt4 = (
            update(Proxy)
            .where(Proxy.priority_tier.notin_([1, 2, 3]))
            .values(priority_tier=4)
        )
        result4 = await session.execute(stmt4)

        await session.commit()
        return result1.rowcount + result2.rowcount + result3.rowcount + result4.rowcount
