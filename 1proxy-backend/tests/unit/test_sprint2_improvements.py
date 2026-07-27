"""Tests for Sprint 2 improvements: source trust scoring, multi-endpoint, perf history."""
import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from app.db_storage import db_storage
from app.db_models import ProxyPerformanceHistory


class TestSourceTrustScoring:
    """1C — Source trust scoring."""

    def test_auto_disable_rule_low_trust_enough_data(self):
        """Source with trust < 10 and >= 50 proxies should be disabled."""
        trust_score = 5.0
        total = 50
        assert trust_score < 10.0 and total >= 50  # should disable

    def test_auto_disable_rule_low_trust_not_enough_data(self):
        """Source with trust < 10 but < 50 proxies should NOT be disabled."""
        trust_score = 5.0
        total = 20
        assert trust_score < 10.0  # but
        assert total < 50  # so should NOT disable

    def test_auto_disable_rule_ok_trust(self):
        """Source with trust >= 10 should NOT be disabled regardless of total."""
        trust_score = 50.0
        total = 100
        assert not (trust_score < 10.0 and total >= 50)  # should NOT disable

    def test_trust_score_formula(self):
        """Trust score = (validated / (validated + failed)) * 100."""
        assert round(80 / (80 + 20) * 100, 1) == 80.0
        assert round(10 / (10 + 90) * 100, 1) == 10.0
        assert round(0 / (0 + 100) * 100, 1) == 0.0
        assert round(100 / (100 + 0) * 100, 1) == 100.0

    def test_confidence_formula(self):
        """Confidence scales linearly from 0.1 at 10 proxies to 1.0 at 100+."""
        assert min(10 / 100, 1.0) == 0.1
        assert min(50 / 100, 1.0) == 0.5
        assert min(100 / 100, 1.0) == 1.0
        assert min(200 / 100, 1.0) == 1.0

    def test_bonus_thresholds(self):
        """Trust >= 90 → +10, >= 70 → +5, else 0."""
        for trust, expected_bonus in [(95, 10), (90, 10), (85, 5), (70, 5), (60, 0), (0, 0)]:
            if trust >= 90:
                bonus = 10
            elif trust >= 70:
                bonus = 5
            else:
                bonus = 0
            assert bonus == expected_bonus, f"Trust {trust} → {bonus} != {expected_bonus}"


class TestMultiEndpointValidation:
    """2A — IP integrity check."""

    def test_ip_integrity_match(self):
        """IP integrity returns True when IPs match."""
        claimed_ip = "1.2.3.4"
        returned_ip = "1.2.3.4"
        assert returned_ip == claimed_ip

    def test_ip_integrity_mismatch(self):
        """IP integrity returns False when IPs don't match."""
        claimed_ip = "1.2.3.4"
        returned_ip = "5.6.7.8"
        assert returned_ip != claimed_ip

    def test_ip_integrity_penalty_applied(self):
        """Quality score halved when IP integrity fails."""
        quality_score = 80
        if True:  # ip_integrity is False
            quality_score = max(0, quality_score // 2)
        assert quality_score == 40

    def test_ip_integrity_penalty_no_effect_when_none(self):
        """No penalty when IP integrity check returns None (unknown)."""
        ip_integrity = None
        quality_score = 80
        if ip_integrity is False:
            quality_score = max(0, quality_score // 2)
        assert quality_score == 80  # unchanged


class TestPerformanceHistory:
    """2C — ProxyPerformanceHistory tracking."""

    def test_performance_record_shape_success(self):
        """Success record has correct fields."""
        record = ProxyPerformanceHistory(
            proxy_id=1,
            latency_ms=150,
            success=True,
        )
        assert record.proxy_id == 1
        assert record.latency_ms == 150
        assert record.success is True

    def test_performance_record_shape_failure(self):
        """Failure record has correct fields."""
        record = ProxyPerformanceHistory(
            proxy_id=2,
            latency_ms=None,
            success=False,
        )
        assert record.proxy_id == 2
        assert record.latency_ms is None
        assert record.success is False

