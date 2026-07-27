"""Tests for OptimizedProxyValidator scoring and phase1 methods."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Optional
from app.validator import OptimizedProxyValidator, ValidationResult
from app.validation_config import ValidationConfig


class TestCalculateQualityScore:
    """Core scoring algorithm — determines 0-100 proxy quality."""

    @pytest.fixture
    def v(self):
        config = ValidationConfig()
        return OptimizedProxyValidator(config=config)

    # --- Latency scoring ---
    @pytest.mark.parametrize("latency,expected_min", [
        (50,  40),    # <80 → 40
        (100, 35),    # <150 → 35
        (200, 25),    # <300 → 25
        (400, 18),    # <600 → 18
        (800, 10),    # <1200 → 10
        (2000, 5),    # <3000 → 5
        (5000, 0),    # >= 3000 → 0
        (None, 0),    # None → 0
    ])
    @pytest.mark.asyncio
    async def test_latency_scoring(self, v, latency, expected_min):
        score = await v.calculate_quality_score(
            latency_ms=latency,
            anonymity=None,
            can_access_google=False,
            can_access_openai=False,
            proxy_type="unknown",
            ssl_valid=False,
            is_blacklisted=False,
            dns_leak=False,
        )
        assert score >= expected_min, f"latency={latency}: expected ≥{expected_min}, got {score}"

    # --- Anonymity scoring (0-25) ---
    @pytest.mark.parametrize("anonymity,base", [
        ("elite",      25),
        ("anonymous",  15),
        ("transparent", 5),
        (None,         0),
    ])
    @pytest.mark.asyncio
    async def test_anonymity_scoring(self, v, anonymity, base):
        score = await v.calculate_quality_score(
            latency_ms=50,
            anonymity=anonymity,
            can_access_google=False,
            can_access_openai=False,
            proxy_type="unknown",
            ssl_valid=False,
            is_blacklisted=False,
            dns_leak=False,
        )
        # 40(latency) + anonymity + 0(no google) + 0(no openai) + 0(unknown type) + 0(no ssl)
        assert score == 40 + base

    # --- Access check scoring (0-20) ---
    @pytest.mark.parametrize("google,openai,add", [
        (True,  True,  20),
        (True,  False, 10),
        (False, True,  10),
        (False, False, 0),
        (None,  False, 0),
        (False, None,  0),
    ])
    @pytest.mark.asyncio
    async def test_access_scoring(self, v, google, openai, add):
        score = await v.calculate_quality_score(
            latency_ms=50,
            anonymity=None,
            can_access_google=google,
            can_access_openai=openai,
            proxy_type="unknown",
            ssl_valid=False,
            is_blacklisted=False,
            dns_leak=False,
        )
        assert score == 40 + add

    # --- Proxy type bonus (0-10) ---
    @pytest.mark.parametrize("proxy_type,add", [
        ("residential", 10),
        ("datacenter",   5),
        ("proxy",        0),
        ("tor",          0),
        ("unknown",      0),
    ])
    @pytest.mark.asyncio
    async def test_proxy_type_scoring(self, v, proxy_type, add):
        score = await v.calculate_quality_score(
            latency_ms=50,
            anonymity=None,
            can_access_google=False,
            can_access_openai=False,
            proxy_type=proxy_type,
            ssl_valid=False,
            is_blacklisted=False,
            dns_leak=False,
        )
        assert score == 40 + add

    # --- SSL bonus (0-10) ---
    @pytest.mark.asyncio
    async def test_ssl_bonus(self, v):
        score_no_ssl = await v.calculate_quality_score(
            latency_ms=50, anonymity=None,
            can_access_google=False, can_access_openai=False,
            proxy_type="unknown", ssl_valid=False,
            is_blacklisted=False, dns_leak=False,
        )
        score_ssl = await v.calculate_quality_score(
            latency_ms=50, anonymity=None,
            can_access_google=False, can_access_openai=False,
            proxy_type="unknown", ssl_valid=True,
            is_blacklisted=False, dns_leak=False,
        )
        assert score_ssl == score_no_ssl + 10

    # --- Penalties: blacklist (-30), dns_leak (-15) ---
    @pytest.mark.parametrize("blacklisted,dns_leak,penalty", [
        (True,  False, -30),
        (False, True,  -15),
        (True,  True,  -45),
    ])
    @pytest.mark.asyncio
    async def test_penalties(self, v, blacklisted, dns_leak, penalty):
        score = await v.calculate_quality_score(
            latency_ms=50, anonymity=None,
            can_access_google=False, can_access_openai=False,
            proxy_type="unknown", ssl_valid=False,
            is_blacklisted=blacklisted, dns_leak=dns_leak,
        )
        # 40(latency) + penalty, clamped to 0-100
        assert score == max(0, 40 + penalty)

    # --- Clamping (0-100) ---
    @pytest.mark.asyncio
    async def test_clamp_min(self, v):
        score = await v.calculate_quality_score(
            latency_ms=5000, anonymity=None,
            can_access_google=False, can_access_openai=False,
            proxy_type="unknown", ssl_valid=False,
            is_blacklisted=True, dns_leak=True,  # -45
        )
        assert score == 0

    @pytest.mark.asyncio
    async def test_clamp_max(self, v):
        score = await v.calculate_quality_score(
            latency_ms=50, anonymity="elite",
            can_access_google=True, can_access_openai=True,
            proxy_type="residential", ssl_valid=True,
            is_blacklisted=False, dns_leak=False,
        )
        # 40 + 25 + 10 + 10 + 10 + 10 = 105 → clamped 100
        assert score == 100


class TestCheckAnonymity:
    """Anonymity detection from httpbin.org/headers."""

    @pytest.fixture
    def v(self):
        config = ValidationConfig()
        v = OptimizedProxyValidator(config=config)
        v.session = MagicMock()
        v.session.close = AsyncMock()
        v.semaphore = AsyncMock()
        return v

    def _mock_response(self, status: int, headers: Optional[dict] = None):
        """Create an aiohttp-like context manager that returns a mock response."""
        mock_resp = MagicMock()
        mock_resp.status = status
        async def json():
            return {"headers": headers or {}}
        mock_resp.json = json
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        return mock_cm

    @pytest.mark.asyncio
    async def test_elite(self, v):
        """No Via/X-Forwarded-For headers → elite."""
        v.session.get = MagicMock(
            return_value=self._mock_response(200, {"Accept": "text/html"})
        )
        result = await v.check_anonymity_fast("http://1.2.3.4:8080")
        assert result == "elite"

    @pytest.mark.asyncio
    async def test_anonymous_via(self, v):
        """Via header → anonymous (not transparent)."""
        v.session.get = MagicMock(
            return_value=self._mock_response(200, {"Via": "1.1 proxy"})
        )
        result = await v.check_anonymity_fast("http://1.2.3.4:8080")
        assert result == "anonymous"

    @pytest.mark.asyncio
    async def test_transparent_x_forwarded(self, v):
        """X-Forwarded-For present → transparent."""
        v.session.get = MagicMock(
            return_value=self._mock_response(200, {"X-Forwarded-For": "9.9.9.9"})
        )
        result = await v.check_anonymity_fast("http://1.2.3.4:8080")
        assert result == "transparent"

    @pytest.mark.asyncio
    async def test_transparent_forwarded(self, v):
        """Forwarded header → transparent."""
        v.session.get = MagicMock(
            return_value=self._mock_response(200, {"Forwarded": "for=1.2.3.4"})
        )
        result = await v.check_anonymity_fast("http://1.2.3.4:8080")
        assert result == "transparent"

    @pytest.mark.asyncio
    async def test_anonymity_non_200(self, v):
        """Non-200 response → None."""
        v.session.get = MagicMock(
            return_value=self._mock_response(500)
        )
        result = await v.check_anonymity_fast("http://1.2.3.4:8080")
        assert result is None

    @pytest.mark.asyncio
    async def test_anonymity_exception(self, v):
        """Connection error → None."""
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=Exception("conn error"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        v.session.get = MagicMock(return_value=mock_cm)
        result = await v.check_anonymity_fast("http://1.2.3.4:8080")
        assert result is None


class TestValidatePhase1:
    """Fast connectivity + basic quality estimation."""

    @pytest.fixture
    def v(self):
        config = ValidationConfig()
        v = OptimizedProxyValidator(config=config)
        v.session = MagicMock()
        v.session.close = AsyncMock()
        v.semaphore = AsyncMock()
        v._validation_cache = MagicMock()
        v._validation_cache.get = AsyncMock(return_value=None)
        v._validation_cache.set = AsyncMock()
        v._stats = MagicMock()
        return v

    @pytest.mark.asyncio
    async def test_cached_result(self, v):
        """Phase 1 cache hit returns immediately."""
        cached = ValidationResult(success=True, latency_ms=50, quality_score=40)
        v._validation_cache.get = AsyncMock(return_value=cached)
        result = await v.validate_phase1("http://1.2.3.4:8080", "1.2.3.4")
        assert result.quality_score == 40

    @pytest.mark.asyncio
    async def test_connectivity_failure(self, v):
        """Connection fail → success=False."""
        v.validate_connectivity_fast = AsyncMock(return_value=(False, None, "Timeout"))
        result = await v.validate_phase1("http://1.2.3.4:8080", "1.2.3.4")
        assert result.success is False
        assert "Timeout" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_slow_latency_fail(self, v):
        """Latency above fast_fail threshold → fail."""
        v.validate_connectivity_fast = AsyncMock(return_value=(True, 9999, None))
        result = await v.validate_phase1("http://1.2.3.4:8080", "1.2.3.4")
        assert result.success is False
        assert "Latency too high" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_good_latency_high_score(self, v):
        """Fast proxy → high quick_score."""
        v.validate_connectivity_fast = AsyncMock(return_value=(True, 50, None))
        result = await v.validate_phase1("http://1.2.3.4:8080", "1.2.3.4")
        assert result.success is True
        assert result.quality_score == 40

    @pytest.mark.asyncio
    async def test_medium_latency(self, v):
        """Medium proxy → medium quick_score."""
        v.validate_connectivity_fast = AsyncMock(return_value=(True, 200, None))
        result = await v.validate_phase1("http://1.2.3.4:8080", "1.2.3.4")
        assert result.success is True
        assert result.quality_score == 25
