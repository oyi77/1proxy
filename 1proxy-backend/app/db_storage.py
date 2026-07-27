from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.db_models import User, ProxySource, Proxy, SourceTrustScore, ProxyPerformanceHistory
from app.validator import optimized_validator, get_default_config, ProxyValidationConfig

logger = logging.getLogger(__name__)


class DatabaseStorage:
    def __init__(self, enable_validation: bool = True):
        self.enable_validation = enable_validation

    async def create_admin_user(
        self, session: AsyncSession, email: str = "admin@1proxy.local"
    ) -> User:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                oauth_provider="local",
                oauth_id="admin",
                email=email,
                username="admin",
                role="admin",
                avatar_url=None,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user

    async def seed_admin_sources(self, session: AsyncSession, admin_user_id: int):
        from app.sources import SourceRegistry

        for source_config in SourceRegistry.SOURCES:
            result = await session.execute(
                select(ProxySource).where(ProxySource.url == str(source_config.url))
            )
            existing = result.scalar_one_or_none()

            if not existing:
                source = ProxySource(
                    user_id=admin_user_id,
                    url=str(source_config.url),
                    type=source_config.type.value
                    if hasattr(source_config.type, "value")
                    else str(source_config.type),
                    name=str(source_config.url).split("/")[-2],
                    enabled=source_config.enabled,
                    validated=True,
                    is_admin_source=True,
                    is_paid=False,
                )
                session.add(source)

        await session.commit()

    async def add_proxy(
        self, session: AsyncSession, proxy_data: dict, source_id: Optional[int] = None
    ) -> Optional[Proxy]:
        result = await session.execute(
            select(Proxy).where(Proxy.url == proxy_data["url"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.last_seen = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
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
            validation_result = await proxy_validator.validate_comprehensive(url, ip)

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
                    "last_validated": datetime.utcnow(),
                }
            )

        return await self.add_proxy(session, proxy_data, source_id)

    async def add_proxies(self, session: AsyncSession, proxies_data: List[dict]) -> int:
        """
        Efficiently add proxies using bulk insert with ON CONFLICT DO UPDATE.
        This avoids N queries for N proxies and instead uses a single bulk operation.
        """
        if not proxies_data:
            return 0

        now = datetime.utcnow()
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

                # Prepare data for bulk insert
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
            batch_size = 100
            total_inserted = 0

            for i in range(0, len(prepared_data), batch_size):
                batch = prepared_data[i : i + batch_size]

                for proxy_dict in batch:
                    try:
                        added_new = False
                        async with session.begin_nested():
                            # Avoid autoflush of previous pending objects during our lookup.
                            with session.no_autoflush:
                                result = await session.execute(
                                    select(Proxy).where(Proxy.url == proxy_dict["url"])
                                )
                                existing = result.scalar_one_or_none()

                            if existing:
                                existing.last_seen = now
                                existing.updated_at = now
                                # Give failed proxies another chance if seen again by scraper
                                if existing.validation_status == "failed":
                                    existing.validation_status = "pending"
                                    # We don't set is_working=True yet, keep it False until validated
                                await session.flush([existing])
                            else:
                                proxy = Proxy(**proxy_dict)
                                session.add(proxy)
                                await session.flush([proxy])
                                added_new = True

                        if added_new:
                            total_inserted += 1

                    except Exception as e:
                        logger.error(
                            f"Error inserting proxy {proxy_dict.get('url')}: {e}"
                        )
                        continue

                await session.commit()

            logger.info(
                f"Successfully processed {len(prepared_data)} proxies, inserted {total_inserted} new ones"
            )
            return len(prepared_data)

        except Exception as e:
            logger.error(f"Error in bulk insert: {e}")
            await session.rollback()
            return await self._add_proxies_fallback(session, prepared_data)

    async def _add_proxies_fallback(
        self, session: AsyncSession, proxies_data: List[dict]
    ) -> int:
        """Fallback method for adding proxies one by one if bulk insert fails."""
        added_count = 0
        now = datetime.utcnow()

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

    async def validate_and_update_proxies(
        self,
        session: AsyncSession,
        proxy_ids: Optional[List[int]] = None,
        limit: int = 20,  # Reduced from 50 for better SQLite performance
        config: Optional[ProxyValidationConfig] = None,
    ) -> dict:
        """Validate pending proxies and update their status - optimized version"""
        if proxy_ids:
            # If specific IDs provided (e.g. for revalidation), don't filter by pending status
            query = select(Proxy).where(Proxy.id.in_(proxy_ids))
        else:
            query = (
                select(Proxy).where(Proxy.validation_status == "pending").limit(limit)
            )

        result = await session.execute(query)
        proxies_to_validate = result.scalars().all()

        if not proxies_to_validate:
            return {"validated": 0, "failed": 0, "total": 0}

        proxy_tuples = [(p.url, p.ip) for p in proxies_to_validate if p.ip]

        if not proxy_tuples:
            return {"validated": 0, "failed": 0, "total": 0}

        # Use optimized validator with custom config if provided
        validator = optimized_validator
        if config:
            # Create a temporary validator with custom config
            from app.validator import OptimizedProxyValidator
            validator = OptimizedProxyValidator(config)
            await validator._ensure_session()

        validation_results = await validator.validate_batch(proxy_tuples)

        validated_count = 0
        failed_count = 0

        for proxy in proxies_to_validate:
            matching_result = next(
                (r for url, r in validation_results if url == proxy.url), None
            )

            if not matching_result:
                continue

            if matching_result.success:
                # We must use cast or ensure types for SQLAlchemy columns
                proxy.latency_ms = (
                    int(matching_result.latency_ms)
                    if matching_result.latency_ms is not None
                    else None
                )
                proxy.anonymity = (
                    str(matching_result.anonymity)
                    if matching_result.anonymity
                    else None
                )
                proxy.can_access_google = bool(matching_result.can_access_google)
                proxy.can_access_openai = bool(matching_result.can_access_openai)
                proxy.country_code = (
                    str(matching_result.country_code)
                    if matching_result.country_code
                    else None
                )
                proxy.country_name = (
                    str(matching_result.country_name)
                    if matching_result.country_name
                    else None
                )
                proxy.proxy_type = (
                    str(matching_result.proxy_type)
                    if matching_result.proxy_type
                    else None
                )
                # Update ISP/ORG if available
                if hasattr(matching_result, "isp") and matching_result.isp:
                    proxy.isp = str(matching_result.isp)
                if hasattr(matching_result, "org") and matching_result.org:
                    proxy.org = str(matching_result.org)
                proxy.quality_score = (
                    int(matching_result.quality_score)
                    if matching_result.quality_score is not None
                    else None
                )
                proxy.is_working = True
                proxy.validation_status = "validated"
                proxy.last_validated = datetime.utcnow()
                # Reliability penalty: a proxy that's failed before gets a score haircut
                if proxy.validation_failures and proxy.validation_failures > 0:
                    penalty = min(proxy.validation_failures * 5, 30)
                    proxy.quality_score = max(0, (proxy.quality_score or 0) - penalty)
                proxy.validation_failures = 0
                validated_count += 1
                # Record performance history
                session.add(ProxyPerformanceHistory(
                    proxy_id=proxy.id,
                    latency_ms=matching_result.latency_ms,
                    success=True,
                ))
            else:
                proxy.is_working = False
                proxy.validation_status = "failed"
                proxy.last_validated = datetime.utcnow()
                proxy.validation_failures = (proxy.validation_failures or 0) + 1
                failed_count += 1
                # Record performance history
                session.add(ProxyPerformanceHistory(
                    proxy_id=proxy.id,
                    latency_ms=None,
                    success=False,
                ))

        await session.commit()

        return {
            "validated": validated_count,
            "failed": failed_count,
            "total": len(proxies_to_validate),
        }

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
            cutoff = datetime.utcnow() - timedelta(hours=stale_cutoff_hours)
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

    async def get_sources(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        enabled_only: bool = False,
    ) -> List[ProxySource]:
        query = select(ProxySource)

        if user_id:
            query = query.where(ProxySource.user_id == user_id)
        if enabled_only:
            query = query.where(ProxySource.enabled.is_(True))

        result = await session.execute(query)
        return list(result.scalars().all())

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
        cutoff = datetime.utcnow() - timedelta(hours=stale_cutoff_hours)
        query = select(Proxy).where(
            Proxy.is_working.is_(True),
            Proxy.validation_status == "validated",
            Proxy.last_validated >= cutoff
        )

        if protocol:
            query = query.where(Proxy.protocol == protocol)
        if country_code:
            query = query.where(Proxy.country_code == country_code)
        if min_quality:
            query = query.where(Proxy.quality_score >= min_quality)
        if anonymity:
            query = query.where(Proxy.anonymity == anonymity)
        if max_latency:
            query = query.where(Proxy.latency_ms <= max_latency)

        query = query.order_by(func.random()).limit(1)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_stats(self, session: AsyncSession) -> dict:
        """
        Get proxy statistics efficiently using a single GROUP BY query
        instead of multiple separate queries.
        """
        # Apply TTL filter - only count visible (non-stale working) proxies
        cutoff = datetime.utcnow() - timedelta(hours=3)
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

    async def count_proxies(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(Proxy))
        return result.scalar() or 0

    async def count_sources(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(ProxySource))
        return result.scalar() or 0

    async def count_users(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(User))
        return result.scalar() or 0

    async def get_or_create_user(
        self,
        session: AsyncSession,
        oauth_provider: str,
        oauth_id: str,
        email: str,
        username: str,
        role: str = "user",
        avatar_url: Optional[str] = None,
    ) -> User:
        result = await session.execute(
            select(User).where(
                and_(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                oauth_provider=oauth_provider,
                oauth_id=oauth_id,
                email=email,
                username=username,
                role=role,
                avatar_url=avatar_url,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user

    async def create_notification(
        self,
        session: AsyncSession,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "info",
    ):
        from app.db_models import Notification

        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            severity=severity,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
        return notification

    async def get_notifications(
        self,
        session: AsyncSession,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
    ):
        from app.db_models import Notification

        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.read.is_(False))
        query = query.order_by(Notification.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def mark_notification_read(
        self, session: AsyncSession, user_id: int, notification_id: int
    ) -> bool:
        from app.db_models import Notification

        result = await session.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id, Notification.user_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.read = True
            await session.commit()
            return True
        return False

    async def mark_all_notifications_read(
        self, session: AsyncSession, user_id: int
    ) -> int:
        from app.db_models import Notification
        from sqlalchemy import update

        stmt = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.read.is_(False)))
            .values(read=True)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def purge_3strike_proxies(self, session: AsyncSession) -> int:
        """Delete all proxies where validation_failures >= 3"""
        stmt = delete(Proxy).where(Proxy.validation_failures >= 3)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def purge_unseen_proxies(self, session: AsyncSession, days: int = 14) -> int:
        """Delete proxies where last_seen < NOW() - INTERVAL 'days days'"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = delete(Proxy).where(Proxy.last_seen < cutoff)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def purge_stale_pending(self, session: AsyncSession, days: int = 7) -> int:
        """Delete pending (validation_status='pending') proxies where first_seen < NOW() - INTERVAL 'days days'"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = delete(Proxy).where(
            Proxy.validation_status == "pending",
            Proxy.first_seen < cutoff
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def enforce_db_cap(self, session: AsyncSession, soft_cap: int = 50000, hard_cap: int = 75000) -> int:
        """
        If total > soft_cap, delete lowest priority_tier + oldest first in batches of 5000.
        If total > hard_cap, more aggressively delete.
        """
        total = await self.count_proxies(session)
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

            total = await self.count_proxies(session)

        await session.commit()
        return deleted_count

    async def purge_dead_proxies(self, session: AsyncSession, hours: int = 6) -> int:
        """Hard-delete failed proxies not rechecked in N hours.
        Free proxies die in minutes — this keeps the DB clean of corpses."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
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
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        from sqlalchemy import update
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

    async def update_source_trust_scores(self, session: AsyncSession) -> dict:
        """Update SourceTrustScore for every source based on proxy validation rates.

        For each source with at least 10 proxies (minimum sample), compute trust_score
        as the ratio of validated to total (validated + failed) proxies. Sources
        without enough data get a neutral 50.0 score.

        Returns dict of {source_id: trust_score} and which sources were disabled.
        """
        from sqlalchemy import update as sa_update

        # Get all sources
        sources_result = await session.execute(select(ProxySource))
        sources = sources_result.scalars().all()
        results = {}
        disabled = []

        for source in sources:
            # Count validated, failed, and total proxies for this source
            total = await session.scalar(
                select(func.count(Proxy.id)).where(Proxy.source_id == source.id)
            )
            if not total or total < 10:
                # Not enough data to judge — keep neutral
                results[source.id] = {"trust_score": 50.0, "confidence": 0.0}
                continue

            validated = await session.scalar(
                select(func.count(Proxy.id)).where(
                    Proxy.source_id == source.id,
                    Proxy.validation_status == "validated",
                )
            )
            failed = await session.scalar(
                select(func.count(Proxy.id)).where(
                    Proxy.source_id == source.id,
                    Proxy.validation_status == "failed",
                )
            )
            denom = (validated or 0) + (failed or 0)
            if denom == 0:
                trust_score = 50.0  # neutral
            else:
                trust_score = round((validated or 0) / denom * 100, 1)

            confidence = min(total / 100, 1.0)  # scale: 0.1 at 10 proxies, 1.0 at 100+

            # Upsert trust score
            existing = await session.execute(
                select(SourceTrustScore).where(
                    SourceTrustScore.source_id == source.id
                )
            )
            trust_record = existing.scalar_one_or_none()
            if trust_record:
                trust_record.trust_score = trust_score
                trust_record.confidence = confidence
            else:
                session.add(
                    SourceTrustScore(
                        source_id=source.id,
                        trust_score=trust_score,
                        confidence=confidence,
                    )
                )

            results[source.id] = {"trust_score": trust_score, "confidence": confidence}

            # Auto-disable sources with trust < 10 and enough data (50+ proxies)
            if trust_score < 10.0 and total >= 50 and source.enabled:
                source.enabled = False
                disabled.append(source.id)
                logger.warning(
                    f"🔇 Auto-disabled source {source.id} ({source.url[:60]}): "
                    f"trust_score={trust_score}, total_proxies={total}"
                )

        await session.commit()
        return {"scores": results, "disabled": disabled}

    async def apply_source_trust_bonus(self, session: AsyncSession) -> int:
        """Apply quality_score bonus to proxies from high-trust sources.

        - Trust >= 90: +10 quality_score
        - Trust >= 70: +5 quality_score
        Returns number of proxies updated.
        """
        from sqlalchemy import update as sa_update
        from sqlalchemy import bindparam

        updated = 0
        # Get all trust scores
        scores_result = await session.execute(
            select(SourceTrustScore).where(SourceTrustScore.confidence > 0.2)
        )
        for score in scores_result.scalars().all():
            bonus = 0
            if score.trust_score >= 90:
                bonus = 10
            elif score.trust_score >= 70:
                bonus = 5
            if bonus > 0:
                stmt = (
                    sa_update(Proxy)
                    .where(
                        Proxy.source_id == score.source_id,
                        Proxy.quality_score.isnot(None),
                    )
                    .values(
                        quality_score=Proxy.quality_score + bonus
                    )
                )
                result = await session.execute(stmt)
                updated += result.rowcount

        await session.commit()
        return updated

    async def update_priority_tiers(self, session: AsyncSession) -> int:
        """
        Recalculate priority_tier for all proxies:
        - Tier 1: quality_score >= 80 AND anonymity='elite'
        - Tier 2: quality_score >= 60 AND anonymity IN ('elite', 'anonymous')
        - Tier 3: is_working=True (otherwise)
        - Tier 4: everything else (new, pending, etc.)
        """
        from sqlalchemy import update
        
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
                Proxy.priority_tier != 1  # Don't override tier 1
            )
            .values(priority_tier=2)
        )
        result2 = await session.execute(stmt2)
        
        # Tier 3: is_working=True (but not already tier 1 or 2)
        stmt3 = (
            update(Proxy)
            .where(
                Proxy.is_working.is_(True),
                Proxy.priority_tier.notin_([1, 2])
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


db_storage = DatabaseStorage()
