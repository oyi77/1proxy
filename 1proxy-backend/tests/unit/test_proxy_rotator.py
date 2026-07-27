"""
Tests for ProxyRotator - rotation strategies
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.proxy_rotator import (
    ProxyRotator,
    RotationStrategy,
    RotationSession,
)


class MockProxy:
    """Mock Proxy object for testing"""

    def __init__(
        self,
        id: int,
        ip: str,
        quality_score: int = 50,
        latency_ms: int = 100,
        protocol: str = "http",
    ):
        self.id = id
        self.ip = ip
        self.quality_score = quality_score
        self.latency_ms = latency_ms
        self.protocol = protocol
        self.is_working = True


class TestRotationSession:
    """Test RotationSession class"""

    def test_should_exclude_proxy_max_usage(self):
        session = RotationSession(session_id="test", max_usage_per_proxy=2)
        # Set use count via the correct dict
        session.proxy_use_count[1] = 2
        assert session.should_exclude_proxy(1, "1.2.3.4") is True

    def test_should_exclude_proxy_cooldown(self):
        session = RotationSession(session_id="test", cooldown_minutes=5)
        # Set last-used timestamp via the correct dict
        session.proxy_last_used[1] = datetime.now(timezone.utc).replace(tzinfo=None)
        assert session.should_exclude_proxy(1, "1.2.3.4") is True

    def test_should_not_exclude_after_cooldown(self):
        session = RotationSession(session_id="test", cooldown_minutes=5)
        # Last used 10 minutes ago → cooldown expired
        session.proxy_last_used[1] = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)
        assert session.should_exclude_proxy(1, "1.2.3.4") is False

    def test_should_exclude_proxy_ip(self):
        session = RotationSession(session_id="test")
        session.exclude_ips.add("1.2.3.4")
        assert session.should_exclude_proxy(1, "1.2.3.4") is True

    def test_mark_proxy_used_increments_count(self):
        session = RotationSession(session_id="test")
        session.mark_proxy_used(1, "1.2.3.4")
        assert session.proxy_use_count[1] == 1
        session.mark_proxy_used(1, "1.2.3.4")
        assert session.proxy_use_count[1] == 2

    def test_mark_proxy_used_records_timestamp(self):
        session = RotationSession(session_id="test")
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        session.mark_proxy_used(1, "1.2.3.4")
        assert 1 in session.proxy_last_used
        assert session.proxy_last_used[1] >= before

    def test_used_proxies_alias(self):
        """used_proxies property is an alias for proxy_use_count."""
        session = RotationSession(session_id="test")
        session.mark_proxy_used(1, "1.2.3.4")
        assert session.used_proxies[1] == 1


class TestProxyRotator:
    """Test ProxyRotator class"""

    @pytest.fixture
    def rotator(self):
        return ProxyRotator()

    @pytest.fixture
    def sample_proxies(self):
        return [
            MockProxy(1, "1.1.1.1", quality_score=80, latency_ms=50),
            MockProxy(2, "2.2.2.2", quality_score=60, latency_ms=100),
            MockProxy(3, "3.3.3.3", quality_score=40, latency_ms=200),
            MockProxy(4, "4.4.4.4", quality_score=90, latency_ms=30),
            MockProxy(5, "5.5.5.5", quality_score=30, latency_ms=500),
        ]

    def test_get_or_create_session(self, rotator):
        session = rotator.get_or_create_session("test_session", RotationStrategy.RANDOM)
        assert session.session_id == "test_session"
        assert session.strategy == RotationStrategy.RANDOM

    def test_get_or_create_session_returns_same(self, rotator):
        s1 = rotator.get_or_create_session("s", RotationStrategy.RANDOM)
        s2 = rotator.get_or_create_session("s", RotationStrategy.QUALITY)
        assert s1 is s2

    def test_strategy_random(self, rotator, sample_proxies):
        session = rotator.get_or_create_session("test", RotationStrategy.RANDOM)
        results = set()
        for _ in range(20):
            proxy = rotator.get_next_proxy(session, sample_proxies)
            if proxy:
                results.add(proxy.id)
        # Random should pick at least 2 different proxies in 20 tries
        assert len(results) >= 2

    def test_strategy_round_robin(self, rotator, sample_proxies):
        session = rotator.get_or_create_session("test", RotationStrategy.ROUND_ROBIN)
        proxy1 = rotator.get_next_proxy(session, sample_proxies)
        proxy2 = rotator.get_next_proxy(session, sample_proxies)
        proxy3 = rotator.get_next_proxy(session, sample_proxies)
        assert proxy1.id == 1
        assert proxy2.id == 2
        assert proxy3.id == 3

    def test_strategy_quality(self, rotator, sample_proxies):
        session = rotator.get_or_create_session("test", RotationStrategy.QUALITY)
        # Quality strategy sorts by quality desc → proxy 4 (quality=90) first
        proxy = rotator.get_next_proxy(session, sample_proxies)
        assert proxy.id == 4

    def test_strategy_quality_second_pick(self, rotator, sample_proxies):
        session = rotator.get_or_create_session("test", RotationStrategy.QUALITY)
        p1 = rotator.get_next_proxy(session, sample_proxies)
        p2 = rotator.get_next_proxy(session, sample_proxies)
        assert p1.id == 4  # quality=90
        assert p2.id == 1  # quality=80

    def test_strategy_least_used(self, rotator, sample_proxies):
        session = rotator.get_or_create_session("test", RotationStrategy.LEAST_USED)
        proxy1 = rotator.get_next_proxy(session, sample_proxies)
        session.mark_proxy_used(proxy1.id, proxy1.ip)
        # Next pick must be different (least used = 0 uses)
        proxy2 = rotator.get_next_proxy(session, sample_proxies)
        assert proxy2.id != proxy1.id

    def test_strategy_weighted(self, rotator, sample_proxies):
        session = rotator.get_or_create_session("test", RotationStrategy.WEIGHTED)
        # Run 50 times and collect results - top proxies should dominate
        results = {}
        for _ in range(50):
            proxy = rotator.get_next_proxy(session, sample_proxies)
            if proxy:
                results[proxy.id] = results.get(proxy.id, 0) + 1
        # Proxy 4 (quality=90, latency=30) has the highest weight: 90*1000/31≈2903
        # It should appear more often than proxy 5 (quality=30, latency=500)
        assert results.get(4, 0) > results.get(5, 0)

    def test_strategy_least_conn(self, rotator, sample_proxies):
        session = rotator.get_or_create_session("test", RotationStrategy.LEAST_CONN)
        proxy = rotator.get_next_proxy(session, sample_proxies)
        assert proxy is not None

    def test_strategy_adaptive(self, rotator, sample_proxies):
        session = rotator.get_or_create_session("test", RotationStrategy.ADAPTIVE)
        proxy = rotator.get_next_proxy(session, sample_proxies)
        assert proxy is not None
        # Adaptive should prefer high-quality low-latency proxy
        assert proxy.id in [1, 4]

    def test_empty_proxies(self, rotator):
        session = rotator.get_or_create_session("test", RotationStrategy.RANDOM)
        proxy = rotator.get_next_proxy(session, [])
        assert proxy is None

    def test_excluded_ips(self, rotator, sample_proxies):
        session = rotator.get_or_create_session("test", RotationStrategy.RANDOM)
        session.exclude_ips.add("1.1.1.1")
        for _ in range(20):
            proxy = rotator.get_next_proxy(session, sample_proxies)
            if proxy:
                assert proxy.ip != "1.1.1.1"

    def test_cooldown(self, rotator, sample_proxies):
        session = rotator.get_or_create_session(
            "test", RotationStrategy.RANDOM, cooldown_minutes=60
        )
        proxy = rotator.get_next_proxy(session, sample_proxies)
        assert proxy is not None
        session.mark_proxy_used(proxy.id, proxy.ip)
        # After marking, that proxy should be on cooldown
        for _ in range(20):
            p = rotator.get_next_proxy(session, sample_proxies)
            if p:
                assert p.id != proxy.id

    def test_max_usage(self, rotator, sample_proxies):
        session = rotator.get_or_create_session(
            "test", RotationStrategy.RANDOM, max_usage_per_proxy=1, cooldown_minutes=0
        )
        # Use each proxy once
        for proxy in sample_proxies:
            session.mark_proxy_used(proxy.id, proxy.ip)
        # All at max usage — no more available
        result = rotator.get_next_proxy(session, sample_proxies)
        assert result is None

    def test_all_strategies_return_proxy(self, rotator, sample_proxies):
        for strategy in RotationStrategy:
            session = rotator.get_or_create_session(
                f"test_{strategy}", strategy
            )
            proxy = rotator.get_next_proxy(session, sample_proxies)
            assert proxy is not None, f"Strategy {strategy} returned None unexpectedly"


class TestProxyRotatorEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def rotator(self):
        return ProxyRotator()

    def test_session_cleanup(self):
        rotator = ProxyRotator(session_timeout_minutes=0)
        rotator.get_or_create_session("old", RotationStrategy.RANDOM)
        rotator._cleanup_old_sessions()
        assert len(rotator.sessions) == 0

    def test_session_stats(self, rotator):
        session = rotator.get_or_create_session("test", RotationStrategy.RANDOM)
        session.mark_proxy_used(1, "1.1.1.1")
        session.mark_proxy_used(2, "2.2.2.2")
        stats = rotator.get_session_stats("test")
        assert stats is not None
        assert stats["total_proxies_used"] == 2

    def test_session_stats_missing(self, rotator):
        stats = rotator.get_session_stats("nonexistent")
        assert stats is None

    def test_reset_session(self, rotator):
        rotator.get_or_create_session("test", RotationStrategy.RANDOM)
        s = rotator.sessions["test"]
        s.mark_proxy_used(1, "1.1.1.1")
        rotator.reset_session("test")
        stats = rotator.get_session_stats("test")
        assert stats["total_proxies_used"] == 0

    def test_delete_session(self, rotator):
        rotator.get_or_create_session("test", RotationStrategy.RANDOM)
        rotator.delete_session("test")
        assert rotator.get_session_stats("test") is None

    def test_exclude_proxy_ip(self, rotator):
        rotator.get_or_create_session("test", RotationStrategy.RANDOM)
        rotator.exclude_proxy_ip("test", "9.9.9.9")
        assert "9.9.9.9" in rotator.sessions["test"].exclude_ips

    def test_exclude_proxy_ip_missing_session(self, rotator):
        # Should not raise
        rotator.exclude_proxy_ip("nonexistent", "9.9.9.9")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
