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
import heapq
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db_models import Proxy, ProxyPerformanceHistory
import logging

logger = logging.getLogger(__name__)

# Default config for rotation
REGION_STICKY_TTL = timedelta(minutes=15)  # How long to prefer same region
FAILURE_DECAY_THRESHOLD = 3  # N failures → penalty weight
FAILURE_DECAY_PENALTY = 0.5  # Weight multiplier after threshold
MAX_SESSIONS_PER_USER = 50  # Hard limit to prevent abuse


class RotationStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    QUALITY = "quality"
    LEAST_USED = "least_used"
    WEIGHTED = "weighted"     # Weighted by quality + latency
    LEAST_CONN = "least_conn" # Least active connections (by use count)
    ADAPTIVE = "adaptive"     # Scoring: quality × latency_factor × reliability
    REGION_STICKY = "region_sticky"  # Prefer same country as first proxy chosen


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
    # proxy_id -> failure count (health tracking)
    proxy_failure_count: Dict[int, int] = field(default_factory=dict)
    # proxy_id -> last used timestamp (for cooldown)
    proxy_last_used: Dict[int, datetime] = field(default_factory=dict)
    # proxy_id -> last measured latency (real-time update)
    proxy_latency_cache: Dict[int, int] = field(default_factory=dict)
    exclude_ips: Set[str] = field(default_factory=set)
    max_usage_per_proxy: int = 5  # max uses per proxy per session
    cooldown_minutes: int = 5     # minutes before reusing a proxy
    # Region stickiness
    sticky_region: Optional[str] = None  # Preferred country_code
    sticky_region_set_at: Optional[datetime] = None  # When region was set

    # --- Pre-filtered available pool (performance optimization) ---
    _avail_pool: List[Proxy] = field(default_factory=list, repr=False)
    _avail_dirty: bool = field(default=True, repr=False)  # True = rebuild needed

    # Legacy alias so existing callers that read used_proxies[id] still work
    @property
    def used_proxies(self) -> Dict[int, int]:
        return self.proxy_use_count

    def invalidate_avail(self) -> None:
        """Mark available pool as dirty — next get_next_proxy rebuilds it."""
        self._avail_dirty = True

    def _ensure_avail(self, proxies: List[Proxy]) -> None:
        """Rebuild available pool if dirty. O(n) once, then O(1) per rotation."""
        if not self._avail_dirty and self._avail_pool:
            return
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self._avail_pool = [
            p for p in proxies
            if p.ip not in self.exclude_ips
            and self.proxy_use_count.get(p.id, 0) < self.max_usage_per_proxy
            and (
                p.id not in self.proxy_last_used
                or (now - self.proxy_last_used[p.id]).total_seconds() >= self.cooldown_minutes * 60
            )
        ]
        self._avail_dirty = False
        logger.debug(f"Rebuilt avail pool: {len(self._avail_pool)}/{len(proxies)} proxies")

    def _avail_len(self) -> int:
        """Number of currently available proxies."""
        return len(self._avail_pool) if not self._avail_dirty else 0

    def should_exclude_proxy(self, proxy_id: int, proxy_ip: str) -> bool:
        """Return True if this proxy should be skipped."""
        if proxy_ip in self.exclude_ips:
            return True
        if self.proxy_use_count.get(proxy_id, 0) >= self.max_usage_per_proxy:
            return True
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
        # Mark pool dirty if this proxy hit the usage cap (won't be available next time)
        if self.proxy_use_count[proxy_id] >= self.max_usage_per_proxy:
            self._avail_dirty = True

    def report_failure(self, proxy_id: int) -> None:
        """Record a failure for a proxy, reducing its selection weight."""
        self.proxy_failure_count[proxy_id] = self.proxy_failure_count.get(proxy_id, 0) + 1
        logger.debug(f"Reported failure for proxy {proxy_id} "
                      f"(total: {self.proxy_failure_count[proxy_id]})")

    def get_effective_weight(self, proxy_id: int, base_weight: float) -> float:
        """Calculate effective weight factoring in failures."""
        failures = self.proxy_failure_count.get(proxy_id, 0)
        if failures >= FAILURE_DECAY_THRESHOLD:
            return base_weight * FAILURE_DECAY_PENALTY
        return base_weight


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
        # Heap of (last_used_timestamp, session_id) for O(log n) cleanup
        self._session_heap: List[tuple] = []

    def _cleanup_old_sessions(self) -> None:
        """Remove expired rotation sessions using heap for O(log n) eviction."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Push current sessions onto heap lazily
        for sid, s in self.sessions.items():
            heapq.heappush(self._session_heap, (s.last_used, sid))

        # Pop expired sessions from heap
        while self._session_heap:
            last_used, sid = self._session_heap[0]
            if now - last_used > self.session_timeout:
                heapq.heappop(self._session_heap)
                if sid in self.sessions:
                    del self.sessions[sid]
                    logger.debug(f"Cleaned up expired rotation session: {sid}")
            else:
                break

        if self._session_heap:
            logger.debug(
                f"Session heap: {len(self.sessions)} active, {len(self._session_heap)} queued"
            )

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

        # Enforce max sessions per user
        if user_id:
            user_sessions = sum(
                1 for s in self.sessions.values() if s.user_id == user_id
            )
            if user_sessions >= MAX_SESSIONS_PER_USER:
                # Evict oldest session for this user
                oldest_id = min(
                    (sid for sid, s in self.sessions.items() if s.user_id == user_id),
                    key=lambda sid: self.sessions[sid].created_at,
                    default=None,
                )
                if oldest_id:
                    self.delete_session(oldest_id)
                    logger.warning(f"Evicted oldest session {oldest_id} for user {user_id}")

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

    def invalidate_cache(self, cache_key: Optional[str] = None) -> None:
        """
        Invalidate rotation cache. If cache_key is None, clear ALL caches.
        Call this when proxies are added/updated/deleted.
        """
        if cache_key:
            self.proxy_cache.pop(cache_key, None)
            self.cache_timestamps.pop(cache_key, None)
            logger.debug(f"Invalidated rotation cache: {cache_key}")
        else:
            self.proxy_cache.clear()
            self.cache_timestamps.clear()
            logger.debug("Invalidated ALL rotation caches")

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
        """Get next proxy based on rotation strategy.
        
        Uses pre-filtered available pool for O(1) average-case lookup.
        Pool is rebuilt O(n) only when dirty (new session, usage cap hit, exclusion).
        """
        if not proxies:
            return None

        strategy = rotation_session.strategy

        # ── Strategies that can use the pre-filtered pool ──
        if strategy in (RotationStrategy.RANDOM, RotationStrategy.ROUND_ROBIN,
                        RotationStrategy.QUALITY, RotationStrategy.LEAST_USED,
                        RotationStrategy.LEAST_CONN):
            rotation_session._ensure_avail(proxies)
            avail = rotation_session._avail_pool
            if not avail:
                return None

            if strategy == RotationStrategy.RANDOM:
                # Pop from random position (O(1) average)
                idx = random.randrange(len(avail))
                return avail.pop(idx)

            elif strategy == RotationStrategy.ROUND_ROBIN:
                # Cycle through pool without removing (avail stays intact)
                # Pool rebuilt only when dirty (usage cap hit)
                proxy = avail[rotation_session.proxy_index % len(avail)]
                rotation_session.proxy_index += 1
                return proxy

            elif strategy == RotationStrategy.QUALITY:
                # Sort avail pool descending by quality (in-place, once)
                if rotation_session.proxy_index == 0:
                    rotation_session._avail_pool.sort(key=lambda p: p.quality_score or 0, reverse=True)
                if rotation_session._avail_pool:
                    proxy = rotation_session._avail_pool.pop(0)
                    rotation_session.proxy_index += 1
                    return proxy
                return None

            elif strategy == RotationStrategy.WEIGHTED:
                if not avail:
                    return None
                weights = []
                for p in avail:
                    base = (p.quality_score or 1) * (1000.0 / ((p.latency_ms or 1000) + 1))
                    effective = rotation_session.get_effective_weight(p.id, base)
                    weights.append(effective)
                total = sum(weights)
                if total == 0:
                    return avail.pop(random.randrange(len(avail)))
                normalized = [w / total for w in weights]
                r = random.random()
                cumulative = 0.0
                for i, (p, w) in enumerate(zip(avail, normalized)):
                    cumulative += w
                    if r <= cumulative:
                        return avail.pop(i)
                return avail.pop(-1)

            elif strategy in (RotationStrategy.LEAST_USED, RotationStrategy.LEAST_CONN):
                avail.sort(key=lambda p: rotation_session.proxy_use_count.get(p.id, 0))
                proxy = avail.pop(0)
                return proxy

        # ── REGION_STICKY ──
        if strategy == RotationStrategy.REGION_STICKY:
            rotation_session._ensure_avail(proxies)
            avail = rotation_session._avail_pool
            if not avail:
                return None

            if rotation_session.sticky_region:
                region_proxies = [p for p in avail
                                  if getattr(p, 'country_code', None) == rotation_session.sticky_region]
                if region_proxies:
                    return region_proxies.pop(random.randrange(len(region_proxies)))

            # Pick new sticky region
            chosen = random.choice(avail)
            rotation_session.sticky_region = getattr(chosen, 'country_code', None)
            rotation_session.sticky_region_set_at = datetime.now(timezone.utc).replace(tzinfo=None)
            return chosen

        # ── ADAPTIVE & WEIGHTED ──
        elif strategy in (RotationStrategy.ADAPTIVE, RotationStrategy.WEIGHTED):
            rotation_session._ensure_avail(proxies)
            avail = rotation_session._avail_pool
            if not avail:
                return None

            if strategy == RotationStrategy.WEIGHTED:
                weights = []
                for p in avail:
                    base = (p.quality_score or 1) * (1000.0 / ((p.latency_ms or 1000) + 1))
                    effective = rotation_session.get_effective_weight(p.id, base)
                    weights.append(effective)
                total = sum(weights)
                if total == 0:
                    return random.choice(avail)
                normalized = [w / total for w in weights]
                r = random.random()
                cumulative = 0.0
                for p, w in zip(avail, normalized):
                    cumulative += w
                    if r <= cumulative:
                        return p
                return avail[-1]

            # ADAPTIVE
            scores = []
            for p in avail:
                quality = p.quality_score or 50
                latency = p.latency_ms or 500
                latency_factor = 1000.0 / (latency + 100)
                usage = rotation_session.proxy_use_count.get(p.id, 0)
                failures = rotation_session.proxy_failure_count.get(p.id, 0)
                reliability = 0.95 ** usage
                failure_penalty = 1.0 if failures < FAILURE_DECAY_THRESHOLD else FAILURE_DECAY_PENALTY
                cached_latency = rotation_session.proxy_latency_cache.get(p.id)
                if cached_latency:
                    latency_factor = 1000.0 / (cached_latency + 100)
                scores.append((p, quality * latency_factor * reliability * failure_penalty))
            scores.sort(key=lambda x: x[1], reverse=True)
            return scores[0][0] if scores else None

        return None

    def report_proxy_failure(self, session_id: str, proxy_id: int, proxy_ip: Optional[str] = None) -> None:
        """
        Report a proxy failure for a session.
        This reduces the proxy's selection weight and optionally excludes it.
        """
        if session_id in self.sessions:
            self.sessions[session_id].report_failure(proxy_id)
            # After N failures, auto-exclude
            failures = self.sessions[session_id].proxy_failure_count.get(proxy_id, 0)
            if failures >= FAILURE_DECAY_THRESHOLD * 2 and proxy_ip:
                self.exclude_proxy_ip(session_id, proxy_ip)
                logger.info(f"Auto-excluded proxy {proxy_ip} after {failures} failures")

    def update_proxy_latency(self, session_id: str, proxy_id: int, latency_ms: int) -> None:
        """Update cached latency for a proxy (real-time adjustment)."""
        if session_id in self.sessions:
            self.sessions[session_id].proxy_latency_cache[proxy_id] = latency_ms

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
            "strategy": s.strategy.value,
            "created_at": s.created_at.isoformat(),
            "last_used": s.last_used.isoformat(),
            "total_proxies_used": len(s.proxy_use_count),
            "unique_proxies_used": len(s.proxy_use_count),
            "excluded_ips_count": len(s.exclude_ips),
            "proxy_index": s.proxy_index,
            "total_failures": sum(s.proxy_failure_count.values()),
            "sticky_region": s.sticky_region,
            "cache_size": len(self.proxy_cache),
        }

    def reset_session(self, session_id: str) -> None:
        """Reset a rotation session."""
        if session_id in self.sessions:
            s = self.sessions[session_id]
            s.proxy_use_count.clear()
            s.proxy_last_used.clear()
            s.proxy_failure_count.clear()
            s.proxy_latency_cache.clear()
            s.exclude_ips.clear()
            s.proxy_index = 0
            s.sticky_region = None
            s.sticky_region_set_at = None
            logger.info(f"Reset rotation session: {session_id}")

    def delete_session(self, session_id: str) -> None:
        """Delete a rotation session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted rotation session: {session_id}")


# Global rotator instance
proxy_rotator = ProxyRotator()
