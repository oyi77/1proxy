from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

import logging

from app.db_models import User, ProxySource, Proxy
from app.repository import ProxyRepository, SourceRepository, UserRepository, NotificationRepository, StatsRepository, ValidationRepository
from app.validator import ProxyValidationConfig

logger = logging.getLogger(__name__)


class DatabaseStorage:
    def __init__(self, enable_validation: bool = True):
        self.enable_validation = enable_validation
        self._proxy_repo = ProxyRepository(enable_validation=enable_validation)
        self._source_repo = SourceRepository()
        self._user_repo = UserRepository()
        self._notification_repo = NotificationRepository()
        self._stats_repo = StatsRepository()
        self._validation_repo = ValidationRepository()

    # ─────────────────────────────────────────
    # Proxy methods
    # ─────────────────────────────────────────

    async def add_proxy(
        self, session: AsyncSession, proxy_data: dict, source_id: Optional[int] = None
    ) -> Optional[Proxy]:
        """Add a single proxy to the database."""
        return await self._proxy_repo.add_proxy(session, proxy_data, source_id)

    async def add_proxy_with_validation(
        self, session: AsyncSession, proxy_data: dict, source_id: Optional[int] = None
    ) -> Optional[Proxy]:
        """Add proxy with comprehensive validation"""
        return await self._proxy_repo.add_proxy_with_validation(session, proxy_data, source_id)

    async def add_proxies(self, session: AsyncSession, proxies_data: List[dict]) -> int:
        """
        Efficiently add proxies using bulk insert with ON CONFLICT DO UPDATE.
        This avoids N queries for N proxies and instead uses a single bulk operation.
        """
        return await self._proxy_repo.add_proxies(session, proxies_data)

    async def _add_proxies_fallback(
        self, session: AsyncSession, proxies_data: List[dict]
    ) -> int:
        """Fallback method for adding proxies one by one if bulk insert fails."""
        return await self._proxy_repo._add_proxies_fallback(session, proxies_data)

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
        """Get proxies with filtering, pagination and sorting."""
        return await self._proxy_repo.get_proxies(
            session, protocol, country_code, anonymity, min_quality,
            is_working, validation_status, limit, offset, order_by, stale_cutoff_hours,
        )

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
        """Get a random working proxy matching filters."""
        return await self._proxy_repo.get_random_proxy(
            session, protocol, country_code, min_quality, anonymity, max_latency, stale_cutoff_hours,
        )

    async def count_proxies(self, session: AsyncSession) -> int:
        """Count total proxies in the database."""
        return await self._proxy_repo.count_proxies(session)

    # ─────────────────────────────────────────
    # Source methods
    # ─────────────────────────────────────────

    async def get_sources(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        enabled_only: bool = False,
    ) -> List[ProxySource]:
        """Get proxy sources with optional filtering."""
        return await self._source_repo.get_sources(session, user_id, enabled_only)

    async def count_sources(self, session: AsyncSession) -> int:
        """Count total proxy sources in the database."""
        return await self._source_repo.count_sources(session)

    async def seed_admin_sources(self, session: AsyncSession, admin_user_id: int, force: bool = False):
        """Seed admin sources from admin_sources.json if table is empty (or force=True)."""
        return await self._source_repo.seed_admin_sources(session, admin_user_id, force=force)

    async def get_admin_sources(
        self,
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[ProxySource], int]:
        """Get paginated list of admin (is_admin_source) sources."""
        return await self._source_repo.get_admin_sources(session, limit, offset)

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
        return await self._source_repo.create_admin_source(
            session, url, source_type, admin_user_id, name, description, enabled,
        )

    async def update_admin_source(
        self,
        session: AsyncSession,
        source_id: int,
        **kwargs,
    ) -> Optional[ProxySource]:
        """Update an admin source. Only allow safe fields."""
        return await self._source_repo.update_admin_source(session, source_id, **kwargs)

    async def delete_admin_source(
        self, session: AsyncSession, source_id: int
    ) -> bool:
        """Delete an admin source."""
        return await self._source_repo.delete_admin_source(session, source_id)

    async def update_source_trust_scores(self, session: AsyncSession) -> dict:
        """Update SourceTrustScore for every source based on proxy validation rates."""
        return await self._source_repo.update_source_trust_scores(session)

    async def apply_source_trust_bonus(self, session: AsyncSession) -> int:
        """Apply quality_score bonus to proxies from high-trust sources."""
        return await self._source_repo.apply_source_trust_bonus(session)

    async def get_source_effectiveness(self, session: AsyncSession) -> List[dict]:
        """Sources ranked by validation rate."""
        return await self._source_repo.get_source_effectiveness(session)

    # ─────────────────────────────────────────
    # User methods
    # ─────────────────────────────────────────

    async def create_admin_user(
        self, session: AsyncSession, email: str = "admin@1proxy.local"
    ) -> User:
        """Create default admin user if not exists."""
        return await self._user_repo.create_admin_user(session, email)

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
        """Get existing user or create a new one from OAuth data."""
        return await self._user_repo.get_or_create_user(
            session, oauth_provider, oauth_id, email, username, role, avatar_url,
        )

    async def count_users(self, session: AsyncSession) -> int:
        """Count total users in the database."""
        return await self._user_repo.count_users(session)

    # ─────────────────────────────────────────
    # Notification methods
    # ─────────────────────────────────────────

    async def create_notification(
        self,
        session: AsyncSession,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "info",
    ):
        """Create a new notification for a user."""
        return await self._notification_repo.create_notification(
            session, user_id, notification_type, title, message, severity,
        )

    async def get_notifications(
        self,
        session: AsyncSession,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
    ):
        """Get notifications for a user."""
        return await self._notification_repo.get_notifications(
            session, user_id, unread_only, limit,
        )

    async def mark_notification_read(
        self, session: AsyncSession, user_id: int, notification_id: int
    ) -> bool:
        """Mark a single notification as read."""
        return await self._notification_repo.mark_notification_read(
            session, user_id, notification_id,
        )

    async def mark_all_notifications_read(
        self, session: AsyncSession, user_id: int
    ) -> int:
        """Mark all unread notifications as read."""
        return await self._notification_repo.mark_all_notifications_read(
            session, user_id,
        )

    # ─────────────────────────────────────────
    # Stats / Lifecycle methods
    # ─────────────────────────────────────────

    async def get_stats(self, session: AsyncSession) -> dict:
        """
        Get proxy statistics efficiently using a single GROUP BY query
        instead of multiple separate queries.
        """
        return await self._stats_repo.get_stats(session)

    async def get_quality_trend(self, session: AsyncSession, days: int = 30) -> List[dict]:
        """Daily avg quality_score over the last N days."""
        return await self._stats_repo.get_quality_trend(session, days)

    async def get_staleness_stats(self, session: AsyncSession) -> dict:
        """Proxy staleness breakdown."""
        return await self._stats_repo.get_staleness_stats(session)

    async def enforce_db_cap(self, session: AsyncSession, soft_cap: int = 50000, hard_cap: int = 75000) -> int:
        """
        If total > soft_cap, delete lowest priority_tier + oldest first in batches of 5000.
        If total > hard_cap, more aggressively delete.
        """
        return await self._stats_repo.enforce_db_cap(session, soft_cap, hard_cap)

    async def purge_dead_proxies(self, session: AsyncSession, hours: int = 6) -> int:
        """Hard-delete failed proxies not rechecked in N hours.
        Free proxies die in minutes — this keeps the DB clean of corpses."""
        return await self._stats_repo.purge_dead_proxies(session, hours)

    async def soft_stale_proxies(self, session: AsyncSession, hours: int = 24) -> int:
        """Mark proxies as not-working if they haven't been revalidated in N hours.
        They'll be re-tested by the next revalidation cycle and revived if alive."""
        return await self._stats_repo.soft_stale_proxies(session, hours)

    async def update_priority_tiers(self, session: AsyncSession) -> int:
        """
        Recalculate priority_tier for all proxies:
        - Tier 1: quality_score >= 80 AND anonymity='elite'
        - Tier 2: quality_score >= 60 AND anonymity IN ('elite', 'anonymous')
        - Tier 3: is_working=True (otherwise)
        - Tier 4: everything else (new, pending, etc.)
        """
        return await self._stats_repo.update_priority_tiers(session)

    # ─────────────────────────────────────────
    # Validation methods
    # ─────────────────────────────────────────

    async def validate_and_update_proxies(
        self,
        session: AsyncSession,
        proxy_ids: Optional[List[int]] = None,
        limit: int = 20,
        config: Optional["ProxyValidationConfig"] = None,
        cooldown_minutes: int = 5,
    ) -> dict:
        """Validate pending proxies and update their status - optimized version"""
        return await self._validation_repo.validate_and_update_proxies(
            session, proxy_ids, limit, config, cooldown_minutes,
        )

    async def purge_3strike_proxies(self, session: AsyncSession) -> int:
        """Delete all proxies where validation_failures >= 3"""
        return await self._validation_repo.purge_3strike_proxies(session)

    async def purge_unseen_proxies(self, session: AsyncSession, days: int = 14) -> int:
        """Delete proxies where last_seen < NOW() - INTERVAL 'days days'"""
        return await self._validation_repo.purge_unseen_proxies(session, days)

    async def purge_stale_pending(self, session: AsyncSession, days: int = 7) -> int:
        """Delete pending (validation_status='pending') proxies where first_seen < NOW() - INTERVAL 'days days'"""
        return await self._validation_repo.purge_stale_pending(session, days)


db_storage = DatabaseStorage()
