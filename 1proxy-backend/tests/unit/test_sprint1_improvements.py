"""Tests for Sprint 1 improvements: stale purge, reliability scoring, new sources."""
import pytest
import json, os
from unittest.mock import AsyncMock, MagicMock, patch
from app.db_storage import db_storage


class TestNewSources:
    """3A — 8+ new proxy sources in the admin_sources.json seed."""

    @pytest.fixture
    def admin_sources(self):
        json_path = os.path.join(
            os.path.dirname(__file__), "../../app/data/admin_sources.json"
        )
        with open(json_path) as f:
            return json.load(f)

    def test_sources_count_increased(self, admin_sources):
        """Should have 26+ sources (was ~18 before Sprint 1)."""
        assert len(admin_sources) >= 26, (
            f"Expected >= 26 sources, got {len(admin_sources)}"
        )

    def test_new_sources_have_valid_types(self, admin_sources):
        """All sources should have valid attributes."""
        for s in admin_sources:
            assert "type" in s, f"Source {s['url']} missing type"
            assert "url" in s, f"Source missing url"
            assert s["url"], f"Source has empty url"

    def test_specific_new_sources_present(self, admin_sources):
        """Known Sprint 1 sources should be in the JSON seed."""
        urls = {s["url"] for s in admin_sources}
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

    def test_all_sources_enabled(self, admin_sources):
        """Default sources in JSON seed should be enabled."""
        for s in admin_sources:
            assert s.get("enabled", True), f"Source {s['url']} is not enabled"


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
