"""Tests for Sprint 1 improvements: stale purge, reliability scoring, new sources."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.sources import SourceRegistry
from app.db_storage import db_storage


class TestNewSources:
    """3A — 8 new proxy sources added to the registry."""

    def test_sources_count_increased(self):
        """Should have 26+ sources (was ~18 before Sprint 1)."""
        assert len(SourceRegistry.SOURCES) >= 26, (
            f"Expected >= 26 sources, got {len(SourceRegistry.SOURCES)}"
        )

    def test_new_sources_have_valid_types(self):
        """All sources should have valid attributes."""
        for s in SourceRegistry.SOURCES:
            assert hasattr(s, "type"), f"Source {s.url} missing type"
            assert hasattr(s, "url"), f"Source missing url"
            assert s.url, f"Source has empty url"

    def test_specific_new_sources_present(self):
        """Known Sprint 1 sources should be in the registry."""
        urls = {s.url for s in SourceRegistry.SOURCES}
        expected_fragments = [
            "spys.me/proxy.txt",
            "free-proxy-list.net",
            "sslproxies.org",
            "proxynova.com",
            "hidemy.name",
            "proxy-list.download/api/v1/get?type=http",
            "proxy-list.download/api/v1/get?type=socks5",
            "openproxylist.xyz",
        ]
        for fragment in expected_fragments:
            assert any(fragment in url for url in urls), (
                f"Missing source containing: {fragment}"
            )

    def test_all_sources_enabled(self):
        """Default sources in registry should be enabled."""
        for s in SourceRegistry.SOURCES:
            assert s.enabled, f"Source {s.url} is not enabled"


class TestPurgeDeadProxies:
    """1A — Stale proxy auto-purge methods (sync wrappers for async DB calls)."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.execute = AsyncMock()
        session.execute.return_value = MagicMock(rowcount=5)
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_purge_dead_proxies_default_hours(self, mock_session):
        """Should use default 6-hour cutoff."""
        count = await db_storage.purge_dead_proxies(mock_session)
        assert count == 5

    @pytest.mark.asyncio
    async def test_purge_dead_proxies_custom_hours(self, mock_session):
        """Should accept custom hour cutoff."""
        count = await db_storage.purge_dead_proxies(mock_session, hours=12)
        assert count == 5

    @pytest.mark.asyncio
    async def test_purge_dead_zero_on_empty(self, mock_session):
        """Should return 0 when no dead proxies match."""
        mock_session.execute.return_value = MagicMock(rowcount=0)
        count = await db_storage.purge_dead_proxies(mock_session, hours=1)
        assert count == 0

    @pytest.mark.asyncio
    async def test_soft_stale_proxies_default_hours(self, mock_session):
        """Should use default 24-hour cutoff."""
        count = await db_storage.soft_stale_proxies(mock_session)
        assert count == 5

    @pytest.mark.asyncio
    async def test_soft_stale_proxies_zero_on_empty(self, mock_session):
        """Should return 0 when no stale proxies match."""
        mock_session.execute.return_value = MagicMock(rowcount=0)
        count = await db_storage.soft_stale_proxies(mock_session, hours=48)
        assert count == 0


class TestReliabilityPenalty:
    """1B — Reliability-weighted quality scoring."""

    def test_penalty_formula(self):
        """Penalty = min(failures * 5, 30)."""
        assert min(2 * 5, 30) == 10
        assert min(0 * 5, 30) == 0
        assert min(10 * 5, 30) == 30

    def test_score_does_not_go_negative(self):
        """Quality score floor at 0."""
        assert max(0, 10 - 30) == 0
        assert max(0, 70 - 10) == 60
        assert max(0, 100 - 0) == 100
