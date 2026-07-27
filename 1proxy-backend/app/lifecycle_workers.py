import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func, delete
from app.database import AsyncSessionLocal
from app.db_storage import db_storage
from app.db_models import Proxy

logger = logging.getLogger(__name__)

TIER_VALIDATION_INTERVALS = {
    1: timedelta(hours=2),
    2: timedelta(hours=6),
    3: timedelta(hours=12),
}

async def revalidation_worker(batch_size=20, interval_seconds=60):
    """Revalidate proxies based on priority tier.
    Tier 1 (elite): revalidate if older than 2 hours
    Tier 2 (good): revalidate if older than 6 hours
    Tier 3 (standard): revalidate if older than 12 hours
    Tier 4 (new): handled by existing background_validation_worker
    """
    logger.info("🔄 Revalidation worker started")
    await asyncio.sleep(10)  # Initial wait

    while True:
        try:
            async with AsyncSessionLocal() as session:
                # Query proxies that need revalidation based on tier
                cutoff_conditions = or_(
                    # Proxies with NULL last_validated are always stale
                    Proxy.last_validated.is_(None),
                    and_(
                        Proxy.priority_tier == 1,
                        Proxy.last_validated < datetime.utcnow() - TIER_VALIDATION_INTERVALS[1]
                    ),
                    and_(
                        Proxy.priority_tier == 2,
                        Proxy.last_validated < datetime.utcnow() - TIER_VALIDATION_INTERVALS[2]
                    ),
                    and_(
                        Proxy.priority_tier == 3,
                        Proxy.last_validated < datetime.utcnow() - TIER_VALIDATION_INTERVALS[3]
                    ),
                )

                query = (
                    select(Proxy)
                    .where(
                        Proxy.is_working == True,
                        Proxy.validation_status.in_(["validated", "pending"]),
                        Proxy.priority_tier.in_([1, 2, 3]),
                        cutoff_conditions
                    )
                    .order_by(Proxy.priority_tier.asc(), Proxy.last_validated.asc().nulls_first())
                    .limit(batch_size)
                )

                result = await session.execute(query)
                proxies_to_revalidate = result.scalars().all()

                if proxies_to_revalidate:
                    proxy_ids = [p.id for p in proxies_to_revalidate]
                    validation_result = await db_storage.validate_and_update_proxies(
                        session, proxy_ids=proxy_ids
                    )
                    
                    logger.info(
                        f"✅ Revalidated {validation_result['validated']} proxies (tier {proxies_to_revalidate[0].priority_tier}), "
                        f"❌ {validation_result['failed']} failed (batch size: {len(proxy_ids)})"
                    )
                else:
                    logger.debug("No proxies need revalidation at this time")

            await asyncio.sleep(interval_seconds)

        except Exception as e:
            logger.error(f"⚠️  Revalidation worker error: {e}")
            await asyncio.sleep(300)  # 5 minute retry delay


async def cleanup_worker(interval_minutes=30):
    """Periodic cleanup: 3-strike death, unseen purge, stale pending, DB cap"""
    logger.info("🧹 Cleanup worker started")
    await asyncio.sleep(10)  # Initial wait

    while True:
        try:
            async with AsyncSessionLocal() as session:
                # 1. Purge 3-strike failures
                purge_3strike_result = await db_storage.purge_3strike_proxies(session)
                logger.info(f"🗑️  Purged {purge_3strike_result} proxies with 3+ validation failures")

                # 2. Purge unseen proxies (not seen in 14 days)
                purge_unseen_result = await db_storage.purge_unseen_proxies(session, days=14)
                logger.info(f"🗑️  Purged {purge_unseen_result} proxies unseen for 14+ days")

                # 3. Purge stale pending proxies (pending for 7+ days)
                purge_stale_result = await db_storage.purge_stale_pending(session, days=7)
                logger.info(f"🗑️  Purged {purge_stale_result} stale pending proxies")

                # 4. Enforce database cap if needed
                from sqlalchemy import select, func as sa_func
                count_result = await session.execute(select(sa_func.count()).select_from(Proxy))
                total_count = count_result.scalar()
                if total_count > 50000:  # Soft cap
                    enforce_result = await db_storage.enforce_db_cap(
                        session, soft_cap=50000, hard_cap=75000
                    )
                    logger.info(f"📊 Enforced DB cap: {enforce_result}")
                else:
                    logger.debug(f"📊 Current proxy count: {total_count} (under soft cap)")

                # 5. Aggressive stale purge: delete failed proxies not rechecked in 6h
                purge_dead = await db_storage.purge_dead_proxies(session, hours=6)
                if purge_dead:
                    logger.info(f"🗑️  Purged {purge_dead} dead proxies (failed + not rechecked in 6h)")

                # 6. Soft-stale: mark working-but-stale proxies as non-working
                soft_stale = await db_storage.soft_stale_proxies(session, hours=24)
                if soft_stale:
                    logger.info(f"💤 Soft-marked {soft_stale} stale proxies (not revalidated in 24h)")

            await asyncio.sleep(interval_minutes * 60)

        except Exception as e:
            logger.error(f"⚠️  Cleanup worker error: {e}")
            await asyncio.sleep(300)  # 5 minute retry delay


async def priority_tier_worker(interval_hours=6):
    """Recalculate proxy priority tiers based on quality and anonymity"""
    logger.info("📊 Priority tier worker started")
    await asyncio.sleep(10)  # Initial wait

    while True:
        try:
            async with AsyncSessionLocal() as session:
                update_result = await db_storage.update_priority_tiers(session)
                logger.info(f"📊 Updated priority tiers for {update_result} proxies")

            await asyncio.sleep(interval_hours * 3600)

        except Exception as e:
            logger.error(f"⚠️  Priority tier worker error: {e}")
            await asyncio.sleep(300)  # 5 minute retry delay