"""
Proxy Rotation Manager

Manages automated proxy rotation with multiple strategies:
- round_robin: Cycles through proxies in order
- random: Picks random proxies
- quality: Prioritizes highest quality first
- least_used: Picks least recently used proxies
- weighted: Weighted selection by quality + latency
- least_conn: Picks proxy with fewest uses (approximated by usage count)
- adaptive: ML-inspired scoring combining quality, latency, and usage history
"""

import random
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db_models import Proxy
import logging

logger = logging.getLogger(__name__)


class RotationStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    QUALITY = "quality"
    LEAST_USED = "least_used"
    WEIGHTED = "weighted"     # Weighted by quality + latency
    LEAST_CONN = "least_conn" # Least active connections (by use count)
    ADAPTIVE = "adaptive"     # Scoring: quality × latency_factor × reliability


@dataclass
class RotationSession:
    """Tracks a rotation session with state."""

    session_id: str
    user_id: Optional[str] = None
    strategy: RotationStrategy = RotationStrategy.RANDOM
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)
    proxy_index: int = 0
    # proxy_id -> use count
    proxy_use_count: Dict[int, int] = field(default_factory=dict)
    # proxy_id -> last used timestamp (for cooldown)
    proxy_last_used: Dict[int, datetime] = field(default_factory=dict)
    exclude_ips: Set[str] = field(default_factory=set)
    max_usage_per_proxy: int = 5  # max uses per proxy per session
    cooldown_minutes: int = 5     # minutes before reusing a proxy

    # Legacy alias so existing callers that read used_proxies[id] still work
    @property
    def used_proxies(self) -> Dict[int, int]:
        return self.proxy_use_count

    def should_exclude_proxy(self, proxy_id: int, proxy_ip: str) -> bool:
        """Return True if this proxy should be skipped."""
        if proxy_ip in self.exclude_ips:
            return True

        # Usage cap
        if self.proxy_use_count.get(proxy_id, 0) >= self.max_usage_per_proxy:
            return True

        # Cooldown
        last = self.proxy_last_used.get(proxy_id)
        if last is not None:
            if datetime.now(timezone.utc).replace(tzinfo=None) - last < timedelta(minutes=self.cooldown_minutes):
                return True

        return False

    def mark_proxy_used(self, proxy_id: int, proxy_ip: Optional[str] = None) -> None:
        """Record that a proxy was used."""
        self.proxy_use_count[proxy_id] = self.proxy_use_count.get(proxy_id, 0) + 1
        self.proxy_last_used[proxy_id] = datetime.now(timezone.utc).replace(tzinfo=None)
        self.last_used = datetime.now(timezone.utc).replace(tzinfo=None)


class ProxyRotator:
    """
    Manages multiple rotation sessions with different strategies.
    State is kept in-memory for performance.
    """

    def __init__(self, session_timeout_minutes: int = 60):
        self.sessions: Dict[str, RotationSession] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.proxy_cache: Dict[str, List[Proxy]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.cache_timestamps: Dict[str, datetime] = {}

    def _cleanup_old_sessions(self) -> None:
        """Remove expired rotation sessions."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expired = [
            sid
            for sid, s in self.sessions.items()
            if now - s.last_used > self.session_timeout
        ]
        for sid in expired:
            del self.sessions[sid]
            logger.debug(f"Cleaned up expired rotation session: {sid}")
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
        """Get existing session or create a new one."""
        self._cleanup_old_sessions()

        if session_id not in self.sessions:
            self.sessions[session_id] = RotationSession(
                session_id=session_id,
                user_id=user_id,
                strategy=strategy,
                max_usage_per_proxy=max_usage_per_proxy,
                cooldown_minutes=cooldown_minutes,
            )
            logger.info(f"Created rotation session: {session_id} (strategy: {strategy})")

        return self.sessions[session_id]

    def _get_cache_key(
        self,
        protocol: Optional[str],
        country_code: Optional[str],
        min_quality: Optional[int],
        anonymity: Optional[str],
        max_latency: Optional[int],
    ) -> str:
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
        """Get proxies matching criteria, with optional caching."""
        cache_key = self._get_cache_key(
            protocol, country_code, min_quality, anonymity, max_latency
        )

        if use_cache and cache_key in self.proxy_cache:
            cache_time = self.cache_timestamps.get(cache_key)
            if cache_time and datetime.now(timezone.utc).replace(tzinfo=None) - cache_time < self.cache_ttl:
                logger.debug(f"Cache hit for rotation: {cache_key}")
                return self.proxy_cache[cache_key]

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
        proxies = list(result.scalars().all())

        self.proxy_cache[cache_key] = proxies
        self.cache_timestamps[cache_key] = datetime.now(timezone.utc).replace(tzinfo=None)
        logger.debug(f"Loaded {len(proxies)} proxies for rotation (key: {cache_key})")
        return proxies

    def get_next_proxy(
        self,
        rotation_session: RotationSession,
        proxies: List[Proxy],
    ) -> Optional[Proxy]:
        """Get next proxy based on rotation strategy."""
        if not proxies:
            return None

        available = [
            p for p in proxies
            if not rotation_session.should_exclude_proxy(p.id, p.ip)
        ]

        strategy = rotation_session.strategy

        if strategy == RotationStrategy.RANDOM:
            return random.choice(available) if available else None

        elif strategy == RotationStrategy.ROUND_ROBIN:
            if not available:
                return None
            proxy = available[rotation_session.proxy_index % len(available)]
            rotation_session.proxy_index += 1
            return proxy

        elif strategy == RotationStrategy.QUALITY:
            if not available:
                return None
            # Sort by quality descending each call so the best is always first
            sorted_by_quality = sorted(available, key=lambda p: p.quality_score or 0, reverse=True)
            proxy = sorted_by_quality[rotation_session.proxy_index % len(sorted_by_quality)]
            rotation_session.proxy_index += 1
            return proxy

        elif strategy == RotationStrategy.LEAST_USED:
            if not available:
                return None
            available.sort(key=lambda p: rotation_session.proxy_use_count.get(p.id, 0))
            return available[0]

        elif strategy == RotationStrategy.LEAST_CONN:
            if not available:
                return None
            available.sort(key=lambda p: rotation_session.proxy_use_count.get(p.id, 0))
            return available[0]

        elif strategy == RotationStrategy.ADAPTIVE:
            if not available:
                return None
            scores = []
            for p in available:
                quality = p.quality_score or 50
                latency = p.latency_ms or 500
                latency_factor = 1000.0 / (latency + 100)
                usage = rotation_session.proxy_use_count.get(p.id, 0)
                reliability = 0.95 ** usage  # decay with repeated use
                scores.append((p, quality * latency_factor * reliability))
            scores.sort(key=lambda x: x[1], reverse=True)
            return scores[0][0]

        elif strategy == RotationStrategy.WEIGHTED:
            if not available:
                return None
            weights = [
                (p.quality_score or 1) * (1000.0 / ((p.latency_ms or 1000) + 1))
                for p in available
            ]
            total = sum(weights)
            if total == 0:
                return random.choice(available)
            normalized = [w / total for w in weights]
            r = random.random()
            cumulative = 0.0
            for p, w in zip(available, normalized):
                cumulative += w
                if r <= cumulative:
                    return p
            return available[-1]

        return None

    def exclude_proxy_ip(self, session_id: str, ip: str) -> None:
        """Add IP to exclusion list for a session."""
        if session_id in self.sessions:
            self.sessions[session_id].exclude_ips.add(ip)
            logger.debug(f"Added IP {ip} to exclusion list for session {session_id}")

    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get statistics for a rotation session."""
        if session_id not in self.sessions:
            return None
        s = self.sessions[session_id]
        return {
            "session_id": s.session_id,
            "strategy": s.strategy,
            "created_at": s.created_at.isoformat(),
            "last_used": s.last_used.isoformat(),
            "total_proxies_used": len(s.proxy_use_count),
            "unique_proxies_used": len(s.proxy_use_count),
            "excluded_ips_count": len(s.exclude_ips),
            "proxy_index": s.proxy_index,
        }

    def reset_session(self, session_id: str) -> None:
        """Reset a rotation session."""
        if session_id in self.sessions:
            s = self.sessions[session_id]
            s.proxy_use_count.clear()
            s.proxy_last_used.clear()
            s.exclude_ips.clear()
            s.proxy_index = 0
            logger.info(f"Reset rotation session: {session_id}")

    def delete_session(self, session_id: str) -> None:
        """Delete a rotation session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted rotation session: {session_id}")


# Global rotator instance
proxy_rotator = ProxyRotator()
