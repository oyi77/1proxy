from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import logging
import random

from app.db_models import Proxy, ProxyPerformanceHistory

logger = logging.getLogger(__name__)


class ProxyRepository:
    def __init__(self, enable_validation: bool = True):
        self.enable_validation = enable_validation

    async def add_proxy(
        self, session: AsyncSession, proxy_data: dict, source_id: Optional[int] = None
    ) -> Optional[Proxy]:
        result = await session.execute(
            select(Proxy).where(Proxy.url == proxy_data["url"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
            existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            if source_id and not existing.source_id:
                existing.source_id = source_id
            await session.commit()
            return existing

        proxy = Proxy(
            source_id=source_id,
            url=proxy_data["url"],
            protocol=proxy_data.get("protocol", "http"),
            ip=proxy_data.get("ip"),
            port=proxy_data.get("port"),
            is_working=True,
        )
        session.add(proxy)
        await session.commit()
        await session.refresh(proxy)
        return proxy

    async def add_proxy_with_validation(
        self, session: AsyncSession, proxy_data: dict, source_id: Optional[int] = None
    ) -> Optional[Proxy]:
        """Add proxy with comprehensive validation"""
        url = proxy_data.get("url")
        ip = proxy_data.get("ip")

        if not url or not ip:
            return None

        if self.enable_validation:
            from app.validator import optimized_validator

            validation_result = await optimized_validator.validate_comprehensive(url, ip)

            if not validation_result.success:
                return None

            proxy_data.update(
                {
                    "latency_ms": validation_result.latency_ms,
                    "anonymity": validation_result.anonymity,
                    "can_access_google": validation_result.can_access_google,
                    "can_access_openai": validation_result.can_access_openai,
                    "country_code": validation_result.country_code,
                    "country_name": validation_result.country_name,
                    "proxy_type": validation_result.proxy_type,
                    "quality_score": validation_result.quality_score,
                    "is_working": True,
                    "validation_status": "validated",
                    "last_validated": datetime.now(timezone.utc).replace(tzinfo=None),
                }
            )

        return await self.add_proxy(session, proxy_data, source_id)

    async def add_proxies(self, session: AsyncSession, proxies_data: List[dict]) -> int:
        """
        Efficiently add proxies using bulk insert with ON CONFLICT DO UPDATE.
        Uses executemany for maximum throughput.
        """
        if not proxies_data:
            return 0

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        prepared_data = []

        for proxy_data in proxies_data:
            try:
                # Extract or construct URL
                url = proxy_data.get("url")
                if not url:
                    ip = proxy_data.get("ip")
                    port = proxy_data.get("port")
                    protocol = proxy_data.get("protocol", "http")
                    if ip and port:
                        url = f"{protocol}://{ip}:{port}"
                    else:
                        continue

                prepared_data.append(
                    {
                        "url": url,
                        "protocol": proxy_data.get("protocol", "http"),
                        "ip": proxy_data.get("ip"),
                        "port": proxy_data.get("port"),
                        "country_code": proxy_data.get("country_code"),
                        "country_name": proxy_data.get("country_name"),
                        "city": proxy_data.get("city"),
                        "latency_ms": proxy_data.get("latency_ms"),
                        "speed_mbps": proxy_data.get("speed_mbps"),
                        "anonymity": proxy_data.get("anonymity"),
                        "proxy_type": proxy_data.get("proxy_type"),
                        "quality_score": proxy_data.get("quality_score"),
                        "source_id": proxy_data.get("source_id"),
                        "is_working": True,
                        "validation_status": proxy_data.get(
                            "validation_status", "pending"
                        ),
                        "last_validated": proxy_data.get("last_validated"),
                        "can_access_google": proxy_data.get("can_access_google"),
                        "can_access_openai": proxy_data.get("can_access_openai"),
                        "first_seen": now,
                        "last_seen": now,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
            except Exception as e:
                logger.error(f"Error preparing proxy data: {e}")
                continue

        if not prepared_data:
            return 0

        try:
            total = len(prepared_data)
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            stmt = sqlite_insert(Proxy).values(prepared_data[0])
            # Build ON CONFLICT DO UPDATE SET for all columns except url
            pk_cols = ["url"]
            update_cols = {c.name: c for c in stmt.excluded if c.name not in pk_cols}
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["url"],
                set_=update_cols,
            )

            # Batch executemany for max throughput
            batch_size = 500

            for i in range(0, total, batch_size):
                batch = prepared_data[i:i + batch_size]
                await session.execute(
                    sqlite_insert(Proxy).on_conflict_do_update(
                        index_elements=["url"],
                        set_={
                            "last_seen": now,
                            "updated_at": now,
                            "is_working": True,
                            "validation_status": "pending",
                            "latency_ms": upsert_stmt.excluded.latency_ms,
                            "quality_score": upsert_stmt.excluded.quality_score,
                            "country_code": upsert_stmt.excluded.country_code,
                            "country_name": upsert_stmt.excluded.country_name,
                            "city": upsert_stmt.excluded.city,
                            "anonymity": upsert_stmt.excluded.anonymity,
                            "proxy_type": upsert_stmt.excluded.proxy_type,
                            "speed_mbps": upsert_stmt.excluded.speed_mbps,
                            "can_access_google": upsert_stmt.excluded.can_access_google,
                            "can_access_openai": upsert_stmt.excluded.can_access_openai,
                            "source_id": upsert_stmt.excluded.source_id,
                        }
                    ),
                    batch,
                )

            await session.commit()
            logger.info(
                f"Bulk upserted {total} proxies in {total // batch_size + 1} batches"
            )
            return total

        except Exception as e:
            logger.error(f"Error in bulk upsert: {e}")
            await session.rollback()
            # Fallback handles individual rows; report total attempted
            await self._add_proxies_fallback(session, prepared_data)
            return total

    async def _add_proxies_fallback(
        self, session: AsyncSession, proxies_data: List[dict]
    ) -> int:
        """Fallback method for adding proxies one by one if bulk insert fails."""
        added_count = 0
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        for proxy_data in proxies_data:
            try:
                url = proxy_data.get("url")
                if not url:
                    continue

                added_new = False
                async with session.begin_nested():
                    # Avoid autoflush of previous pending objects during our lookup.
                    with session.no_autoflush:
                        result = await session.execute(
                            select(Proxy).where(Proxy.url == url)
                        )
                        existing = result.scalar_one_or_none()

                    if existing:
                        existing.last_seen = now
                        existing.updated_at = now
                        # Give failed proxies another chance if seen again by scraper
                        if existing.validation_status == "failed":
                            existing.validation_status = "pending"
                        await session.flush([existing])
                    else:
                        proxy = Proxy(**proxy_data)
                        session.add(proxy)
                        await session.flush([proxy])
                        added_new = True

                if added_new:
                    added_count += 1

            except Exception as e:
                logger.error(f"Error in fallback insert for proxy: {e}")
                continue

        await session.commit()
        return added_count

    async def get_proxies(
        self,
        session: AsyncSession,
        protocol: Optional[str] = None,
        country_code: Optional[str] = None,
        anonymity: Optional[str] = None,
        min_quality: Optional[int] = None,
        is_working: bool = True,
        validation_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "quality_score",
        stale_cutoff_hours: int = 3,
    ) -> tuple[List[Proxy], int]:
        # Use selectinload to prevent N+1 query problem when accessing proxy.source
        conditions = [Proxy.is_working == is_working]

        # If validation_status is provided, filter by it; otherwise return all statuses
        if validation_status:
            conditions.append(Proxy.validation_status == validation_status)

        # Add TTL filter - only show proxies validated within stale_cutoff_hours
        # Include proxies with NULL last_validated (never validated but working)
        if is_working:
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=stale_cutoff_hours)
            conditions.append(
                or_(
                    Proxy.last_validated >= cutoff,
                    Proxy.last_validated.is_(None)
                )
            )

        query = (
            select(Proxy).options(selectinload(Proxy.source)).where(and_(*conditions))
        )

        if protocol:
            query = query.where(Proxy.protocol == protocol)
        if country_code:
            query = query.where(Proxy.country_code == country_code)
        if anonymity:
            query = query.where(Proxy.anonymity == anonymity)
        if min_quality:
            query = query.where(Proxy.quality_score >= min_quality)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar()

        if order_by == "latency_ms":
            query = query.order_by(Proxy.latency_ms.asc().nulls_last())
        elif order_by == "quality_score":
            query = query.order_by(Proxy.quality_score.desc().nulls_last(), Proxy.last_validated.desc().nulls_last())
        elif order_by == "created_at":
            query = query.order_by(Proxy.created_at.desc())

        query = query.limit(limit).offset(offset)
        result = await session.execute(query)
        proxies = result.scalars().all()

        return list(proxies), total

    async def get_random_proxy(
        self,
        session: AsyncSession,
        protocol: Optional[str] = None,
        country_code: Optional[str] = None,
        min_quality: Optional[int] = None,
        anonymity: Optional[str] = None,
        max_latency: Optional[int] = None,
        stale_cutoff_hours: int = 3,
    ) -> Optional[Proxy]:
        # Apply TTL filter to ensure fresh proxies
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=stale_cutoff_hours)
        conditions = [
            Proxy.is_working.is_(True),
            Proxy.validation_status == "validated",
            Proxy.last_validated >= cutoff
        ]

        if protocol:
            conditions.append(Proxy.protocol == protocol)
        if country_code:
            conditions.append(Proxy.country_code == country_code)
        if min_quality:
            conditions.append(Proxy.quality_score >= min_quality)
        if anonymity:
            conditions.append(Proxy.anonymity == anonymity)
        if max_latency:
            conditions.append(Proxy.latency_ms <= max_latency)

        # Optimized random: COUNT + random OFFSET instead of ORDER BY random()
        # ORDER BY random() requires a full sort — O(n log n)
        # OFFSET on indexed column — O(1) average
        count_result = await session.execute(
            select(func.count()).select_from(Proxy).where(*conditions)
        )
        total = count_result.scalar() or 0
        if total == 0:
            return None

        offset = random.randint(0, total - 1)
        query = (
            select(Proxy)
            .where(*conditions)
            .order_by(Proxy.id)
            .limit(1)
            .offset(offset)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def count_proxies(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(Proxy))
        return result.scalar() or 0
