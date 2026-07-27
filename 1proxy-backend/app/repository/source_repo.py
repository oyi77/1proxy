from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, case
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import logging

from app.db_models import ProxySource, Proxy, SourceTrustScore

logger = logging.getLogger(__name__)


class SourceRepository:
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

    async def count_sources(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(ProxySource))
        return result.scalar() or 0

    async def seed_admin_sources(self, session: AsyncSession, admin_user_id: int, force: bool = False):
        """Seed admin sources from admin_sources.json if table is empty (or force=True)."""
        import json, os

        if not force:
            # Quick check — skip if admin sources already exist
            existing_result = await session.execute(
                select(func.count()).select_from(ProxySource).where(ProxySource.is_admin_source.is_(True))
            )
            already = existing_result.scalar() or 0
            if already > 0:
                logger.info("Admin sources already seeded, skipping")
                return

        json_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "admin_sources.json"
        )
        if not os.path.exists(json_path):
            logger.warning(f"⚠️  admin_sources.json not found at {json_path}")
            return

        with open(json_path) as f:
            sources_data = json.load(f)

        count = 0
        for entry in sources_data:
            result = await session.execute(
                select(ProxySource).where(ProxySource.url == entry["url"])
            )
            if result.scalar_one_or_none():
                continue

            source = ProxySource(
                user_id=admin_user_id,
                url=entry["url"],
                type=entry["type"],
                name=entry.get("name") or entry["url"].split("/")[-2],
                enabled=entry.get("enabled", True),
                validated=True,
                is_admin_source=True,
                is_paid=False,
            )
            session.add(source)
            count += 1

        if count:
            await session.commit()
            logger.info(f"✅ Seeded {count} admin sources from JSON")

    async def get_admin_sources(
        self,
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[ProxySource], int]:
        """Get paginated list of admin (is_admin_source) sources."""
        total_result = await session.execute(
            select(func.count()).select_from(ProxySource).where(ProxySource.is_admin_source.is_(True))
        )
        total = total_result.scalar() or 0

        result = await session.execute(
            select(ProxySource)
            .where(ProxySource.is_admin_source.is_(True))
            .order_by(ProxySource.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def create_admin_source(
        self,
        session: AsyncSession,
        url: str,
        source_type: str,
        admin_user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        enabled: bool = True,
    ) -> ProxySource:
        """Create a new admin-managed source."""
        source = ProxySource(
            user_id=admin_user_id,
            url=url,
            type=source_type,
            name=name or url.split("/")[-2],
            description=description,
            enabled=enabled,
            validated=False,
            is_admin_source=True,
            is_paid=False,
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)
        return source

    async def update_admin_source(
        self,
        session: AsyncSession,
        source_id: int,
        **kwargs,
    ) -> Optional[ProxySource]:
        """Update an admin source. Only allow safe fields."""
        result = await session.execute(
            select(ProxySource).where(
                ProxySource.id == source_id,
                ProxySource.is_admin_source.is_(True),
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            return None

        allowed = {"name", "description", "enabled", "type", "url"}
        for key, value in kwargs.items():
            if key in allowed and value is not None:
                setattr(source, key, value)

        await session.commit()
        await session.refresh(source)
        return source

    async def delete_admin_source(
        self, session: AsyncSession, source_id: int
    ) -> bool:
        """Delete an admin source."""
        result = await session.execute(
            select(ProxySource).where(
                ProxySource.id == source_id,
                ProxySource.is_admin_source.is_(True),
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            return False

        await session.delete(source)
        await session.commit()
        return True

    async def update_source_trust_scores(self, session: AsyncSession) -> dict:
        """Update SourceTrustScore for every source based on proxy validation rates.

        For each source with at least 10 proxies (minimum sample), compute trust_score
        as the ratio of validated to total (validated + failed) proxies. Sources
        without enough data get a neutral 50.0 score.

        Returns dict of {source_id: trust_score} and which sources were disabled.
        """

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

    async def get_source_effectiveness(self, session: AsyncSession) -> List[dict]:
        """Sources ranked by validation rate."""
        rows = await session.execute(
            select(
                ProxySource.id,
                ProxySource.url,
                func.count(Proxy.id).label("total"),
                func.sum(
                    case((Proxy.validation_status == "validated", 1), else_=0)
                ).label("validated_count"),
                func.sum(
                    case((Proxy.validation_status == "failed", 1), else_=0)
                ).label("failed_count"),
            )
            .join(ProxySource, Proxy.source_id == ProxySource.id, isouter=True)
            .group_by(ProxySource.id, ProxySource.url)
            .order_by(func.count(Proxy.id).desc())
        )
        results = []
        for row in rows:
            total = row.total or 0
            validated = row.validated_count or 0
            failed = row.failed_count or 0
            validation_rate = round((validated / (validated + failed)) * 100, 1) if (validated + failed) > 0 else 0
            results.append({
                "source_id": row.id,
                "url": row.url[:80] if row.url else "unknown",
                "total_proxies": total,
                "validated": validated,
                "failed": failed,
                "validation_rate": validation_rate,
            })
        return results
