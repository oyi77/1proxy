from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, insert
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from typing import List, Optional
from datetime import datetime
import logging

from app.db_models import User, ProxySource, Proxy
from app.validator import proxy_validator

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
                        "is_working": True,
                        "validation_status": proxy_data.get(
                            "validation_status", "pending"
                        ),
                        "last_validated": proxy_data.get("last_validated"),
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
            # Use SQLite's INSERT OR REPLACE for upsert behavior
            # On conflict (duplicate URL), update last_seen and updated_at
            stmt = sqlite_insert(Proxy).values(prepared_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["url"],
                set_={
                    "last_seen": now,
                    "updated_at": now,
                },
            )

            await session.execute(stmt)
            await session.commit()

            logger.info(
                f"Successfully bulk inserted/updated {len(prepared_data)} proxies"
            )
            return len(prepared_data)

        except Exception as e:
            logger.error(f"Error in bulk insert: {e}")
            await session.rollback()
            # Fallback to individual inserts if bulk fails
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

                # Check if exists
                result = await session.execute(select(Proxy).where(Proxy.url == url))
                existing = result.scalar_one_or_none()

                if existing:
                    existing.last_seen = now
                    existing.updated_at = now
                else:
                    proxy = Proxy(**proxy_data)
                    session.add(proxy)
                    added_count += 1

            except Exception as e:
                logger.error(f"Error in fallback insert for proxy: {e}")
                continue

        await session.commit()
        return added_count

    async def validate_and_update_proxies(
        self, session: AsyncSession, proxy_ids: List[int] = None, limit: int = 50
    ) -> dict:
        """Validate pending proxies and update their status"""
        if proxy_ids:
            query = select(Proxy).where(
                Proxy.id.in_(proxy_ids), Proxy.validation_status == "pending"
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

        validation_results = await proxy_validator.validate_batch(proxy_tuples)

        validated_count = 0
        failed_count = 0

        for proxy in proxies_to_validate:
            matching_result = next(
                (r for url, r in validation_results if url == proxy.url), None
            )

            if not matching_result:
                continue

            if matching_result.success:
                proxy.latency_ms = matching_result.latency_ms
                proxy.anonymity = matching_result.anonymity
                proxy.can_access_google = matching_result.can_access_google
                proxy.country_code = matching_result.country_code
                proxy.country_name = matching_result.country_name
                proxy.proxy_type = matching_result.proxy_type
                proxy.quality_score = matching_result.quality_score
                proxy.is_working = True
                proxy.validation_status = "validated"
                proxy.last_validated = datetime.utcnow()
                proxy.validation_failures = 0
                validated_count += 1
            else:
                proxy.is_working = False
                proxy.validation_status = "failed"
                proxy.validation_failures = (proxy.validation_failures or 0) + 1
                failed_count += 1

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
        validation_status: str = "validated",
        limit: int = 100,
        offset: int = 0,
        order_by: str = "quality_score",
    ) -> tuple[List[Proxy], int]:
        # Use selectinload to prevent N+1 query problem when accessing proxy.source
        query = (
            select(Proxy)
            .options(selectinload(Proxy.source))
            .where(
                Proxy.is_working == is_working,
                Proxy.validation_status == validation_status,
            )
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
            query = query.order_by(Proxy.quality_score.desc().nulls_last())
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
            query = query.where(ProxySource.enabled == True)

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
    ) -> Optional[Proxy]:
        query = select(Proxy).where(
            Proxy.is_working == True, Proxy.validation_status == "validated"
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
        # Single query with GROUP BY for protocol counts
        result = await session.execute(
            select(Proxy.protocol, func.count(Proxy.id).label("count"))
            .where(Proxy.validation_status == "validated")
            .group_by(Proxy.protocol)
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


db_storage = DatabaseStorage()
