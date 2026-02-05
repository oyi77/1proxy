"""
Proxy Rotation Manager

Manages automated proxy rotation with multiple strategies:
- round_robin: Cycles through proxies in order
- random: Picks random proxies
- quality: Prioritizes highest quality
- least_used: Picks least recently used proxies
"""

import time
import random
import asyncio
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db_models import Proxy
import logging

logger = logging.getLogger(__name__)


class RotationStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    QUALITY = "quality"
    LEAST_USED = "least_used"


@dataclass
class RotationSession:
    """Tracks a rotation session with state"""

    session_id: str
    user_id: Optional[str] = None
    strategy: RotationStrategy = RotationStrategy.RANDOM
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)
    proxy_index: int = 0
    used_proxies: Dict[int, datetime] = field(
        default_factory=dict
    )  # proxy_id -> last_used
    exclude_ips: Set[str] = field(default_factory=set)
    max_usage_per_proxy: int = 5  # Max times a proxy can be used in this session
    cooldown_minutes: int = 5  # Minimum minutes before reusing a proxy

    def should_exclude_proxy(self, proxy_id: int, proxy_ip: str) -> bool:
        """Check if proxy should be excluded from rotation"""
        # Check IP exclusion
        if proxy_ip in self.exclude_ips:
            return True

        # Check usage count
        if self.used_proxies.get(proxy_id, 0) >= self.max_usage_per_proxy:
            return True

        # Check cooldown
        if proxy_id in self.used_proxies:
            last_used = self.used_proxies[proxy_id]
            if datetime.utcnow() - last_used < timedelta(minutes=self.cooldown_minutes):
                return True

        return False

    def mark_proxy_used(self, proxy_id: int, proxy_ip: Optional[str] = None):
        """Mark a proxy as used in this rotation session"""
        self.used_proxies[proxy_id] = self.used_proxies.get(proxy_id, 0) + 1
        self.last_used = datetime.utcnow()


class ProxyRotator:
    """
    Manages multiple rotation sessions with different strategies.
    State is kept in-memory for performance.
    """

    def __init__(self, session_timeout_minutes: int = 60):
        self.sessions: Dict[str, RotationSession] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.proxy_cache: Dict[str, List[Proxy]] = {}  # Cache for filter combinations
        self.cache_ttl = timedelta(minutes=5)
        self.cache_timestamps: Dict[str, datetime] = {}

    def _cleanup_old_sessions(self):
        """Remove expired rotation sessions"""
        now = datetime.utcnow()
        expired = [
            session_id
            for session_id, session in self.sessions.items()
            if now - session.last_used > self.session_timeout
        ]
        for session_id in expired:
            del self.sessions[session_id]
            logger.debug(f"Cleaned up expired rotation session: {session_id}")

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired rotation sessions")

    def get_or_create_session(
        self,
        session_id: str,
        strategy: RotationStrategy = RotationStrategy.RANDOM,
        user_id: Optional[str] = None,
        max_usage_per_proxy: int = 5,
        cooldown_minutes: int = 5,
    ) -> RotationSession:
        """Get existing session or create new one"""
        self._cleanup_old_sessions()

        if session_id not in self.sessions:
            self.sessions[session_id] = RotationSession(
                session_id=session_id,
                user_id=user_id,
                strategy=strategy,
                max_usage_per_proxy=max_usage_per_proxy,
                cooldown_minutes=cooldown_minutes,
            )
            logger.info(
                f"Created new rotation session: {session_id} (strategy: {strategy})"
            )

        return self.sessions[session_id]

    def _get_cache_key(
        self,
        protocol: Optional[str],
        country_code: Optional[str],
        min_quality: Optional[int],
        anonymity: Optional[str],
        max_latency: Optional[int],
    ) -> str:
        """Generate cache key for proxy query"""
        return f"{protocol}:{country_code}:{min_quality}:{anonymity}:{max_latency}"

    async def get_proxies_for_rotation(
        self,
        session: AsyncSession,
        protocol: Optional[str] = None,
        country_code: Optional[str] = None,
        min_quality: Optional[int] = None,
        anonymity: Optional[str] = None,
        max_latency: Optional[int] = None,
        use_cache: bool = True,
    ) -> List[Proxy]:
        """Get proxies matching criteria, with optional caching"""
        cache_key = self._get_cache_key(
            protocol, country_code, min_quality, anonymity, max_latency
        )

        # Check cache
        if use_cache and cache_key in self.proxy_cache:
            cache_time = self.cache_timestamps.get(cache_key)
            if cache_time and datetime.utcnow() - cache_time < self.cache_ttl:
                logger.debug(f"Cache hit for rotation: {cache_key}")
                return self.proxy_cache[cache_key]

        # Build query
        query = select(Proxy).where(Proxy.is_working == True)

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

        query = query.order_by(Proxy.quality_score.desc())

        result = await session.execute(query)
        proxies = result.scalars().all()

        # Update cache
        self.proxy_cache[cache_key] = list(proxies)
        self.cache_timestamps[cache_key] = datetime.utcnow()

        logger.debug(f"Loaded {len(proxies)} proxies for rotation (key: {cache_key})")
        return proxies

    def get_next_proxy(
        self,
        rotation_session: RotationSession,
        proxies: List[Proxy],
    ) -> Optional[Proxy]:
        """Get next proxy based on rotation strategy"""
        if not proxies:
            return None

        strategy = rotation_session.strategy

        if strategy == RotationStrategy.RANDOM:
            # Random selection with exclusion
            available = [
                p
                for p in proxies
                if not rotation_session.should_exclude_proxy(p.id, p.ip)
            ]
            if not available:
                return None
            return random.choice(available)

        elif strategy == RotationStrategy.ROUND_ROBIN:
            # Round-robin through available proxies
            # Filter out excluded proxies first
            available = [
                p
                for p in proxies
                if not rotation_session.should_exclude_proxy(p.id, p.ip)
            ]
            if not available:
                return None

            # Get next index
            idx = rotation_session.proxy_index % len(available)
            proxy = available[idx]
            rotation_session.proxy_index += 1
            return proxy

        elif strategy == RotationStrategy.QUALITY:
            # Highest quality first, then round-robin within same quality tier
            available = [
                p
                for p in proxies
                if not rotation_session.should_exclude_proxy(p.id, p.ip)
            ]
            if not available:
                return None

            # Sort by quality (already sorted)
            idx = rotation_session.proxy_index % len(available)
            proxy = available[idx]
            rotation_session.proxy_index += 1
            return proxy

        elif strategy == RotationStrategy.LEAST_USED:
            # Select proxies used least frequently in this session
            available_proxies = [
                p
                for p in proxies
                if not rotation_session.should_exclude_proxy(p.id, p.ip)
            ]
            if not available_proxies:
                return None

            # Sort by usage count
            available_proxies.sort(
                key=lambda p: rotation_session.used_proxies.get(p.id, 0)
            )
            return available_proxies[0]

        return None

    def exclude_proxy_ip(self, session_id: str, ip: str):
        """Add IP to exclusion list for a session"""
        if session_id in self.sessions:
            self.sessions[session_id].exclude_ips.add(ip)
            logger.debug(f"Added IP {ip} to exclusion list for session {session_id}")

    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get statistics for a rotation session"""
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]
        return {
            "session_id": session.session_id,
            "strategy": session.strategy,
            "created_at": session.created_at.isoformat(),
            "last_used": session.last_used.isoformat(),
            "total_proxies_used": len(session.used_proxies),
            "unique_proxies_used": len(session.used_proxies),
            "excluded_ips_count": len(session.exclude_ips),
            "proxy_index": session.proxy_index,
        }

    def reset_session(self, session_id: str):
        """Reset a rotation session"""
        if session_id in self.sessions:
            self.sessions[session_id].used_proxies.clear()
            self.sessions[session_id].exclude_ips.clear()
            self.sessions[session_id].proxy_index = 0
            logger.info(f"Reset rotation session: {session_id}")

    def delete_session(self, session_id: str):
        """Delete a rotation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted rotation session: {session_id}")


# Global rotator instance
proxy_rotator = ProxyRotator()
