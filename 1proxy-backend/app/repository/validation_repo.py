from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import logging

from app.db_models import Proxy, ProxyPerformanceHistory

logger = logging.getLogger(__name__)


class ValidationRepository:
    def __init__(self, enable_validation: bool = True):
        self.enable_validation = enable_validation

    async def validate_and_update_proxies(
        self,
        session: AsyncSession,
        proxy_ids: Optional[List[int]] = None,
        limit: int = 20,  # Reduced from 50 for better SQLite performance
        config: Optional["ProxyValidationConfig"] = None,
        cooldown_minutes: int = 5,  # Skip proxies validated within this window
    ) -> dict:
        """Validate pending proxies and update their status - optimized version"""
        if proxy_ids:
            # If specific IDs provided (e.g. for revalidation), don't filter by pending status
            # But respect cooldown: skip proxies validated within the last N minutes
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=cooldown_minutes)
            query = select(Proxy).where(
                Proxy.id.in_(proxy_ids),
                or_(
                    Proxy.last_validated.is_(None),
                    Proxy.last_validated < cutoff,
                )
            )
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

        # Skip actual validation when disabled (e.g., in tests)
        if not self.enable_validation:
            for proxy in proxies_to_validate:
                proxy.validation_status = "validated"
                proxy.is_working = True
            await session.commit()
            return {"validated": len(proxies_to_validate), "failed": 0, "total": len(proxies_to_validate)}

        # Use optimized validator with custom config if provided
        from app.validator import optimized_validator, ProxyValidationConfig

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
                proxy.last_validated = datetime.now(timezone.utc).replace(tzinfo=None)
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
                proxy.last_validated = datetime.now(timezone.utc).replace(tzinfo=None)
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

    async def purge_3strike_proxies(self, session: AsyncSession) -> int:
        """Delete all proxies where validation_failures >= 3"""
        stmt = delete(Proxy).where(Proxy.validation_failures >= 3)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def purge_unseen_proxies(self, session: AsyncSession, days: int = 14) -> int:
        """Delete proxies where last_seen < NOW() - INTERVAL 'days days'"""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        stmt = delete(Proxy).where(Proxy.last_seen < cutoff)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def purge_stale_pending(self, session: AsyncSession, days: int = 7) -> int:
        """Delete pending (validation_status='pending') proxies where first_seen < NOW() - INTERVAL 'days days'"""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        stmt = delete(Proxy).where(
            Proxy.validation_status == "pending",
            Proxy.first_seen < cutoff
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount
