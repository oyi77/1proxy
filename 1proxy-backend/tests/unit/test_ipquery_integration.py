import pytest
from unittest.mock import AsyncMock, MagicMock
from app.validator import OptimizedProxyValidator, ValidationResult
from app.validation_config import ValidationConfig


IPQUERY_RESPONSE = {
    "ip": "1.2.3.4",
    "isp": {"asn": "AS1234", "org": "Test ISP", "isp": "Test ISP"},
    "location": {"country": "United States", "country_code": "US",
                  "city": "New York", "state": "NY"},
    "risk": {"is_vpn": False, "is_proxy": False, "is_tor": False,
             "is_datacenter": True, "is_mobile": False, "risk_score": 15},
}


class TestGetIpIntelCached:
    """ipquery.io call parsing and fallback"""

    def _make_validator(self):
        config = ValidationConfig()
        v = OptimizedProxyValidator(config=config)
        v.session = MagicMock()
        v.session.close = AsyncMock()
        v.semaphore = AsyncMock()
        v._geo_cache.get = AsyncMock(return_value=None)
        v._geo_cache.set = AsyncMock()
        return v

    def _mock_response(self, status: int, json_data: dict = None,
                       exc: Exception = None):
        if exc:
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(side_effect=exc)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            return mock_cm
        mock_resp = MagicMock()
        mock_resp.status = status
        mock_resp.json = AsyncMock(return_value=json_data)
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        return mock_cm

    @pytest.mark.asyncio
    async def test_successful_lookup(self):
        """complete ipq data → all fields populated"""
        v = self._make_validator()
        v.session.get = MagicMock(
            return_value=self._mock_response(200, IPQUERY_RESPONSE)
        )
        result = await v.get_ip_intel_cached("1.2.3.4")

        assert result["country_code"] == "US"
        assert result["country_name"] == "United States"
        assert result["city"] == "New York"
        assert result["state"] == "NY"
        assert result["asn"] == "AS1234"
        assert result["isp"] == "Test ISP"
        assert result["org"] == "Test ISP"
        assert result["proxy_type"] == "datacenter"
        assert result["is_datacenter"] is True
        assert result["is_proxy"] is False
        assert result["is_vpn"] is False
        assert result["is_tor"] is False
        assert result["is_mobile"] is False
        assert result["risk_score"] == 15

    @pytest.mark.asyncio
    async def test_datacenter(self):
        v = self._make_validator()
        risk = {"is_vpn": False, "is_proxy": False, "is_tor": False,
                "is_datacenter": True, "is_mobile": False, "risk_score": 10}
        v.session.get = MagicMock(
            return_value=self._mock_response(200, {**IPQUERY_RESPONSE, "risk": risk})
        )
        r = await v.get_ip_intel_cached("1.2.3.4")
        assert r["proxy_type"] == "datacenter"

    @pytest.mark.asyncio
    async def test_proxy(self):
        v = self._make_validator()
        risk = {"is_vpn": False, "is_proxy": True, "is_tor": False,
                "is_datacenter": False, "is_mobile": False, "risk_score": 60}
        v.session.get = MagicMock(
            return_value=self._mock_response(200, {**IPQUERY_RESPONSE, "risk": risk})
        )
        r = await v.get_ip_intel_cached("1.2.3.4")
        assert r["proxy_type"] == "proxy"

    @pytest.mark.asyncio
    async def test_vpn(self):
        v = self._make_validator()
        risk = {"is_vpn": True, "is_proxy": False, "is_tor": False,
                "is_datacenter": False, "is_mobile": False, "risk_score": 50}
        v.session.get = MagicMock(
            return_value=self._mock_response(200, {**IPQUERY_RESPONSE, "risk": risk})
        )
        r = await v.get_ip_intel_cached("1.2.3.4")
        assert r["proxy_type"] == "proxy"

    @pytest.mark.asyncio
    async def test_tor(self):
        v = self._make_validator()
        risk = {"is_vpn": False, "is_proxy": False, "is_tor": True,
                "is_datacenter": False, "is_mobile": False, "risk_score": 80}
        v.session.get = MagicMock(
            return_value=self._mock_response(200, {**IPQUERY_RESPONSE, "risk": risk})
        )
        r = await v.get_ip_intel_cached("1.2.3.4")
        assert r["proxy_type"] == "tor"

    @pytest.mark.asyncio
    async def test_residential(self):
        v = self._make_validator()
        risk = {"is_vpn": False, "is_proxy": False, "is_tor": False,
                "is_datacenter": False, "is_mobile": False, "risk_score": 0}
        v.session.get = MagicMock(
            return_value=self._mock_response(200, {**IPQUERY_RESPONSE, "risk": risk})
        )
        r = await v.get_ip_intel_cached("1.2.3.4")
        assert r["proxy_type"] == "residential"

    @pytest.mark.asyncio
    async def test_api_down(self):
        v = self._make_validator()
        v.session.get = MagicMock(
            return_value=self._mock_response(500)
        )
        r = await v.get_ip_intel_cached("1.2.3.4")
        assert r["proxy_type"] == "unknown"
        assert r["country_code"] is None
        assert r["risk_score"] is None

    @pytest.mark.asyncio
    async def test_network_error(self):
        v = self._make_validator()
        v.session.get = MagicMock(
            return_value=self._mock_response(200, exc=Exception("conn refused"))
        )
        r = await v.get_ip_intel_cached("1.2.3.4")
        assert r["proxy_type"] == "unknown"

    @pytest.mark.asyncio
    async def test_cache_used(self):
        v = self._make_validator()
        cached = {"proxy_type": "datacenter", "risk_score": 10}
        v._geo_cache.get = AsyncMock(return_value=cached)
        result = await v.get_ip_intel_cached("1.2.3.4")
        assert result == cached
        v.session.get.assert_not_called()


class TestRiskPenaltyInPhase2:
    """Quality score penalty from ipq risk data"""

    @pytest.fixture
    def validator(self):
        config = ValidationConfig()
        v = OptimizedProxyValidator(config=config)
        v.session = MagicMock()
        v.session.close = AsyncMock()
        # Bypass the quality gate: min_quality_for_comprehensive = 30
        # Pass phase1 with quality_score >= 30
        return v

    def _mock_phase2(self, validator, ipq_result: dict):
        validator.get_ip_intel_cached = AsyncMock(return_value=ipq_result)
        validator.get_geo_info_cached = AsyncMock()
        validator.detect_proxy_type_cached = AsyncMock()
        validator.check_anonymity_fast = AsyncMock(return_value="elite")
        validator.test_google_access_fast = AsyncMock(return_value=True)
        validator.test_openai_access_fast = AsyncMock(return_value=True)
        validator.check_ssl_validity_fast = AsyncMock(return_value=True)
        validator.check_dns_leak_fast = AsyncMock(return_value=False)
        validator.check_blacklist_fast = AsyncMock(return_value=False)

    @pytest.mark.asyncio
    async def test_high_risk_reduces_quality(self, validator):
        phase1 = ValidationResult(success=True, latency_ms=50, quality_score=40)
        self._mock_phase2(validator, {
            "country_code": "US", "country_name": "United States",
            "state": None, "city": None, "asn": "AS1234",
            "isp": None, "org": None,
            "proxy_type": "residential",
            "is_proxy": False, "is_vpn": False, "is_tor": False,
            "is_datacenter": False, "is_mobile": False,
            "risk_score": 85,
        })
        result = await validator.validate_phase2(
            "http://1.2.3.4:8080", "1.2.3.4", phase1
        )
        # Full = 40(latency) + 25(elite) + 10(google) + 10(openai) + 10(residential) + 10(ssl)
        #       = 105 → clamped 100
        # Penalty: (85-50)//5 = 7, so 100 - 7 = 93
        assert result.quality_score == 93

    @pytest.mark.asyncio
    async def test_low_risk_no_penalty(self, validator):
        phase1 = ValidationResult(success=True, latency_ms=50, quality_score=40)
        self._mock_phase2(validator, {
            "country_code": "US", "country_name": "United States",
            "state": None, "city": None, "asn": "AS1234",
            "isp": None, "org": None,
            "proxy_type": "residential",
            "is_proxy": False, "is_vpn": False, "is_tor": False,
            "is_datacenter": False, "is_mobile": False,
            "risk_score": 30,
        })
        result = await validator.validate_phase2(
            "http://1.2.3.4:8080", "1.2.3.4", phase1
        )
        # 100 - 0 (risk <= 50) = 100
        assert result.quality_score == 100

    @pytest.mark.asyncio
    async def test_proxy_penalty(self, validator):
        phase1 = ValidationResult(success=True, latency_ms=50, quality_score=40)
        self._mock_phase2(validator, {
            "country_code": "US", "country_name": "United States",
            "state": None, "city": None, "asn": "AS1234",
            "isp": None, "org": None,
            "proxy_type": "proxy",
            "is_proxy": True, "is_vpn": False, "is_tor": False,
            "is_datacenter": False, "is_mobile": False,
            "risk_score": 30,
        })
        result = await validator.validate_phase2(
            "http://1.2.3.4:8080", "1.2.3.4", phase1
        )
        # proxy_type="proxy" → 0 (type scoring: resi=10, dc=5, proxy=0)
        # Score = 40(latency) + 25(elite) + 10(google) + 10(openai) + 0(type) + 10(ssl) = 95
        # is_proxy=True → -5 = 90
        assert result.quality_score == 90


class TestFallbackBehavior:
    """Fallback when ipquery returns unknown proxy_type"""

    @pytest.fixture
    def validator(self):
        config = ValidationConfig()
        v = OptimizedProxyValidator(config=config)
        v.session = MagicMock()
        v.session.close = AsyncMock()
        return v

    @pytest.mark.asyncio
    async def test_fallback_on_unknown(self):
        """ipquery unknown → fallback to old geo/proxy-type services"""
        config = ValidationConfig()
        v = OptimizedProxyValidator(config=config)
        v.session = MagicMock()
        v.session.close = AsyncMock()

        v.get_ip_intel_cached = AsyncMock(return_value={
            "country_code": None, "country_name": None,
            "state": None, "city": None, "asn": None,
            "isp": None, "org": None,
            "proxy_type": "unknown",
            "is_proxy": None, "is_vpn": None, "is_tor": None,
            "is_datacenter": None, "is_mobile": None,
            "risk_score": None,
        })
        v.get_geo_info_cached = AsyncMock(
            return_value={"country_code": "JP"}
        )
        v.detect_proxy_type_cached = AsyncMock(
            return_value={"proxy_type": "residential"}
        )
        v.check_anonymity_fast = AsyncMock(return_value="anonymous")
        v.test_google_access_fast = AsyncMock(return_value=True)
        v.test_openai_access_fast = AsyncMock(return_value=True)
        v.check_ssl_validity_fast = AsyncMock(return_value=True)
        v.check_dns_leak_fast = AsyncMock(return_value=False)
        v.check_blacklist_fast = AsyncMock(return_value=False)

        phase1 = ValidationResult(success=True, latency_ms=50, quality_score=40)
        result = await v.validate_phase2(
            "http://5.6.7.8:3128", "5.6.7.8", phase1
        )

        assert result.country_code == "JP"
        assert result.proxy_type == "residential"

    @pytest.mark.asyncio
    async def test_no_fallback_when_ipquery_succeeds(self):
        """ipquery has data → old services NOT called"""
        config = ValidationConfig()
        v = OptimizedProxyValidator(config=config)
        v.session = MagicMock()
        v.session.close = AsyncMock()

        v.get_ip_intel_cached = AsyncMock(return_value={
            "country_code": "DE", "country_name": "Germany",
            "state": None, "city": "Berlin", "asn": "AS5678",
            "isp": "Test ISP", "org": "Test ISP",
            "proxy_type": "datacenter",
            "is_proxy": False, "is_vpn": False, "is_tor": False,
            "is_datacenter": True, "is_mobile": False,
            "risk_score": 10,
        })
        old_geo = AsyncMock()
        old_type = AsyncMock()
        v.get_geo_info_cached = old_geo
        v.detect_proxy_type_cached = old_type
        v.check_anonymity_fast = AsyncMock(return_value="elite")
        v.test_google_access_fast = AsyncMock(return_value=True)
        v.test_openai_access_fast = AsyncMock(return_value=True)
        v.check_ssl_validity_fast = AsyncMock(return_value=True)
        v.check_dns_leak_fast = AsyncMock(return_value=False)
        v.check_blacklist_fast = AsyncMock(return_value=False)

        phase1 = ValidationResult(success=True, latency_ms=50, quality_score=40)
        result = await v.validate_phase2(
            "http://9.9.9.9:80", "9.9.9.9", phase1
        )

        assert result.country_code == "DE"
        assert result.proxy_type == "datacenter"
        old_geo.assert_not_called()
        old_type.assert_not_called()
