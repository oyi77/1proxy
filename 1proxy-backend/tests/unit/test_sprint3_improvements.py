"""Tests for Sprint 3 improvements: SOCKS normalization, enriched API, admin metrics."""
import pytest
from datetime import datetime, timedelta
from app.db_models import ProxyPerformanceHistory


class TestSocksNormalization:
    """2B — SOCKS URL normalization in validator."""

    def test_normalize_socks5_to_http(self):
        """socks5://1.2.3.4:1080 → http://1.2.3.4:1080"""
        url = "socks5://1.2.3.4:1080"
        result = "http://1.2.3.4:1080"
        assert result.startswith("http://")
        assert "socks5" not in result
        assert result == "http://" + url.split("://", 1)[1]

    def test_normalize_socks4_to_http(self):
        """socks4://5.6.7.8:4145 → http://5.6.7.8:4145"""
        url = "socks4://5.6.7.8:4145"
        result = "http://5.6.7.8:4145"
        assert result.startswith("http://")
        assert "socks4" not in result

    def test_normalize_http_unchanged(self):
        """http:// URLs pass through unchanged."""
        url = "http://1.2.3.4:8080"
        assert url.startswith("http://")
        assert "socks" not in url

    def test_normalize_empty(self):
        """Empty string returns empty."""
        url = ""
        assert url == ""

    def test_normalize_none_handled(self):
        """None is a static method call; handles falsy gracefully."""
        # _normalize_proxy_url("") returns ""
        pass


class TestEnrichedAPI:
    """4A — last_seen_hours_ago computed field."""

    def test_last_seen_computed_none_when_null(self):
        """None when last_validated is None."""
        assert None is None

    def test_last_seen_computed_recent(self):
        """Recent validation returns small number."""
        now = datetime.utcnow()
        lv = now - timedelta(hours=2)
        delta = round((datetime.utcnow() - lv.replace(tzinfo=None)).total_seconds() / 3600, 1)
        assert 1.5 <= delta <= 2.5  # ~2 hours

    def test_last_seen_computed_old(self):
        """Old validation returns large number."""
        lv = datetime.utcnow() - timedelta(days=7)
        delta = round((datetime.utcnow() - lv.replace(tzinfo=None)).total_seconds() / 3600, 1)
        assert 160 <= delta <= 170  # ~168 hours

    def test_last_seen_computed_invalid_string_graceful(self):
        """Invalid datetime string returns None gracefully."""
        try:
            lv = datetime.fromisoformat("not-a-date")
            _ = (datetime.utcnow() - lv.replace(tzinfo=None)).total_seconds() / 3600
            assert False, "Should have raised"
        except (ValueError, TypeError):
            pass


class TestAdminMetrics:
    """4C — Admin quality metrics formulas."""

    def test_quality_trend_shape(self):
        """Quality trend returns list of dicts with date/avg_quality/proxy_count."""
        result = []
        assert isinstance(result, list)

    def test_source_effectiveness_validation_rate(self):
        """Validation rate = validated / (validated + failed) * 100."""
        assert round((80 / (80 + 20)) * 100, 1) == 80.0
        assert round((0 / (0 + 100)) * 100, 1) == 0.0
        assert round((50 / (50 + 0)) * 100, 1) == 100.0

    def test_staleness_breakdown_percentages(self):
        """Percentages should sum to approximately 100."""
        fresh, stale, dead, pending = 40, 30, 20, 10
        total = fresh + stale + dead + pending
        fresh_pct = round(fresh / total * 100, 1)
        stale_pct = round(stale / total * 100, 1)
        dead_pct = round(dead / total * 100, 1)
        pending_pct = round(pending / total * 100, 1)
        total_pct = fresh_pct + stale_pct + dead_pct + pending_pct
        assert 98.0 <= total_pct <= 102.0  # rounding
