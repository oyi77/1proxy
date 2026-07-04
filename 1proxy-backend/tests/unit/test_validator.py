import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from app.validator import ProxyValidator, ValidationResult


class TestProxyValidator:
    """Comprehensive test suite for ProxyValidator"""

    @pytest.fixture
    def validator(self):
        return ProxyValidator(timeout=5, max_concurrent=10)

    # ==================== FORMAT VALIDATION ====================

    @pytest.mark.asyncio
    async def test_validate_format_valid_http(self, validator):
        """Test format validation for valid HTTP proxy"""
        assert await validator.validate_format("http://192.168.1.1:8080")
        assert await validator.validate_format("192.168.1.1:8080")

    @pytest.mark.asyncio
    async def test_validate_format_valid_https(self, validator):
        """Test format validation for valid HTTPS proxy"""
        assert await validator.validate_format("https://10.0.0.1:3128")

    @pytest.mark.asyncio
    async def test_validate_format_valid_socks4(self, validator):
        """Test format validation for valid SOCKS4 proxy"""
        assert await validator.validate_format("socks4://127.0.0.1:1080")

    @pytest.mark.asyncio
    async def test_validate_format_valid_socks5(self, validator):
        """Test format validation for valid SOCKS5 proxy"""
        assert await validator.validate_format("socks5://172.16.0.1:9050")

    @pytest.mark.asyncio
    async def test_validate_format_invalid_ip(self, validator):
        """Test format validation rejects invalid IP"""
        assert not await validator.validate_format("999.999.999.999:8080")
        assert not await validator.validate_format("192.168.1:8080")
        assert not await validator.validate_format("192.168.1.256:8080")

    @pytest.mark.asyncio
    async def test_validate_format_invalid_port(self, validator):
        """Test format validation rejects invalid port"""
        assert not await validator.validate_format("192.168.1.1:99999")
        assert not await validator.validate_format("192.168.1.1:")
        assert not await validator.validate_format("192.168.1.1")

    @pytest.mark.asyncio
    async def test_validate_format_edge_cases(self, validator):
        """Test format validation edge cases"""
        assert not await validator.validate_format("")
        assert not await validator.validate_format("not-a-proxy")
        assert not await validator.validate_format("http://")
        assert not await validator.validate_format("://192.168.1.1:8080")

    # ==================== CONNECTIVITY VALIDATION ====================

    @pytest.mark.asyncio
    async def test_validate_connectivity_success(self, validator):
        """Test successful proxy connectivity validation"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__.return_value = mock_resp
        mock_resp.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            is_valid, latency, error = await validator.validate_connectivity(
                "http://192.168.1.1:8080"
            )

        assert is_valid is True
        assert latency is not None
        assert latency >= 0
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_connectivity_timeout(self, validator):
        """Test proxy connectivity timeout"""
        mock_session = MagicMock()
        mock_session.get.side_effect = TimeoutError()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            is_valid, latency, error = await validator.validate_connectivity(
                "http://192.168.1.1:8080"
            )

        assert is_valid is False
        assert latency is None
        assert "timeout" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_connectivity_proxy_error(self, validator):
        """Test proxy connection error"""
        mock_session = MagicMock()
        mock_session.get.side_effect = aiohttp.ClientProxyConnectionError(
            MagicMock(), MagicMock()
        )
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            is_valid, latency, error = await validator.validate_connectivity(
                "http://192.168.1.1:8080"
            )

        assert is_valid is False
        assert latency is None
        assert "connection failed" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_connectivity_http_error(self, validator):
        """Test HTTP error status codes"""
        test_cases = [
            (403, "HTTP 403"),
            (404, "HTTP 404"),
            (500, "HTTP 500"),
            (502, "HTTP 502"),
        ]

        for status_code, expected_error in test_cases:
            mock_resp = AsyncMock()
            mock_resp.status = status_code
            mock_resp.__aenter__.return_value = mock_resp
            mock_resp.__aexit__.return_value = None

            mock_session = MagicMock()
            mock_session.get.return_value.__aenter__.return_value = mock_resp
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None

            with patch("aiohttp.ClientSession", return_value=mock_session):
                is_valid, latency, error = await validator.validate_connectivity(
                    "http://192.168.1.1:8080"
                )

            assert is_valid is False, f"Status {status_code} should fail validation"
            assert latency is None
            assert expected_error in error

    # ==================== ANONYMITY CHECK ====================

    @pytest.mark.asyncio
    async def test_check_anonymity_elite(self, validator):
        """Test elite proxy anonymity detection"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {"headers": {}}
        mock_resp.__aenter__.return_value = mock_resp
        mock_resp.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            anonymity = await validator.check_anonymity("http://192.168.1.1:8080")

        assert anonymity == "elite"

    @pytest.mark.asyncio
    async def test_check_anonymity_transparent(self, validator):
        """Test transparent proxy detection"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {
            "headers": {"X-Forwarded-For": "1.2.3.4", "Via": "proxy"}
        }
        mock_resp.__aenter__.return_value = mock_resp
        mock_resp.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            anonymity = await validator.check_anonymity("http://192.168.1.1:8080")

        assert anonymity == "transparent"

    @pytest.mark.asyncio
    async def test_check_anonymity_anonymous(self, validator):
        """Test anonymous proxy detection"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {"headers": {"Proxy-Connection": "keep-alive"}}
        mock_resp.__aenter__.return_value = mock_resp
        mock_resp.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            anonymity = await validator.check_anonymity("http://192.168.1.1:8080")

        assert anonymity == "anonymous"

    @pytest.mark.asyncio
    async def test_check_anonymity_error(self, validator):
        """Test anonymity check handles errors gracefully"""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Network error")
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            anonymity = await validator.check_anonymity("http://192.168.1.1:8080")

        assert anonymity is None

    # ==================== GOOGLE ACCESS TEST ====================

    @pytest.mark.asyncio
    async def test_google_access_success(self, validator):
        """Test successful Google access through proxy"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__.return_value = mock_resp
        mock_resp.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            can_access = await validator.test_google_access("http://192.168.1.1:8080")

        assert can_access is True

    @pytest.mark.asyncio
    async def test_google_access_failure(self, validator):
        """Test failed Google access through proxy"""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection failed")
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            can_access = await validator.test_google_access("http://192.168.1.1:8080")

        assert can_access is False

    # ==================== GEO INFO ====================

    @pytest.mark.asyncio
    async def test_get_geo_info_success(self, validator):
        """Test successful geo info retrieval"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {
            "country_code": "US",
            "country_name": "United States",
            "region": "California",
            "city": "San Francisco",
        }
        mock_resp.__aenter__.return_value = mock_resp
        mock_resp.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            geo_info = await validator.get_geo_info("8.8.8.8")

        assert geo_info["country_code"] == "US"
        assert geo_info["country_name"] == "United States"
        assert geo_info["state"] == "California"
        assert geo_info["city"] == "San Francisco"

    @pytest.mark.asyncio
    async def test_get_geo_info_error(self, validator):
        """Test geo info retrieval error handling"""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("API error")
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            geo_info = await validator.get_geo_info("8.8.8.8")

        assert geo_info["country_code"] is None
        assert geo_info["country_name"] is None

    # ==================== PROXY TYPE DETECTION ====================

    @pytest.mark.asyncio
    async def test_detect_proxy_type_datacenter(self, validator):
        """Test datacenter proxy detection"""
        test_cases = [
            {"org": "Amazon AWS"},
            {"org": "Google Cloud"},
            {"org": "Microsoft Azure"},
            {"org": "DigitalOcean LLC"},
            {"org": "Linode Hosting"},
            {"org": "OVH Datacenter"},
        ]

        for data in test_cases:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = data
            mock_resp.__aenter__.return_value = mock_resp
            mock_resp.__aexit__.return_value = None

            mock_session = MagicMock()
            mock_session.get.return_value.__aenter__.return_value = mock_resp
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None

            with patch("aiohttp.ClientSession", return_value=mock_session):
                result = await validator.detect_proxy_type("1.2.3.4")

            assert result["proxy_type"] == "datacenter", (
                f"Should detect datacenter for {data['org']}"
            )
            assert result["org"] == data["org"]

    @pytest.mark.asyncio
    async def test_detect_proxy_type_residential(self, validator):
        """Test residential proxy detection"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {"org": "Comcast Cable"}
        mock_resp.__aenter__.return_value = mock_resp
        mock_resp.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await validator.detect_proxy_type("1.2.3.4")

        assert result["proxy_type"] == "residential"

    @pytest.mark.asyncio
    async def test_detect_proxy_type_error(self, validator):
        """Test proxy type detection error handling"""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("API error")
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await validator.detect_proxy_type("1.2.3.4")

        assert result["proxy_type"] == "unknown"

    # ==================== QUALITY SCORE CALCULATION ====================

    @pytest.mark.asyncio
    async def test_calculate_quality_score_perfect(self, validator):
        """Test quality score for perfect proxy"""
        score = await validator.calculate_quality_score(
            latency_ms=50,
            anonymity="elite",
            can_access_google=True,
            can_access_openai=True,
            proxy_type="residential",
        )
        # 40 (latency) + 30 (elite) + 10 (google) + 10 (openai) + 15 (residential) = 105 -> capped at 100
        assert score == 100

    @pytest.mark.asyncio
    async def test_calculate_quality_score_good(self, validator):
        """Test quality score for good proxy"""
        score = await validator.calculate_quality_score(
            latency_ms=300,
            anonymity="anonymous",
            can_access_google=True,
            can_access_openai=True,
            proxy_type="datacenter",
        )
        # 30 (latency) + 20 (anonymous) + 10 (google) + 10 (openai) + 5 (datacenter) = 75
        assert score == 75

    @pytest.mark.asyncio
    async def test_calculate_quality_score_poor(self, validator):
        """Test quality score for poor proxy"""
        score = await validator.calculate_quality_score(
            latency_ms=1500,
            anonymity="transparent",
            can_access_google=False,
            can_access_openai=False,
            proxy_type="unknown",
        )
        # 10 (latency) + 5 (transparent) + 0 + 0 + 0 = 15
        assert score == 15

    @pytest.mark.asyncio
    async def test_calculate_quality_score_minimal(self, validator):
        """Test quality score with minimal data"""
        score = await validator.calculate_quality_score(
            latency_ms=None, anonymity=None, can_access_google=None, can_access_openai=None, proxy_type=None
        )
        assert score == 0

    @pytest.mark.asyncio
    async def test_calculate_quality_score_caps_at_100(self, validator):
        """Test quality score never exceeds 100"""
        score = await validator.calculate_quality_score(
            latency_ms=10,
            anonymity="elite",
            can_access_google=True,
            can_access_openai=True,
            proxy_type="residential",
        )
        assert score <= 100

    # ==================== COMPREHENSIVE VALIDATION ====================

    @pytest.mark.asyncio
    async def test_validate_comprehensive_success(self, validator):
        """Test comprehensive validation with all checks"""
        # Mock connectivity check
        with patch.object(
            validator,
            "validate_connectivity",
            return_value=(True, 150, None),
        ):
            # Mock other checks
            with patch.object(validator, "check_anonymity", return_value="elite"):
                with patch.object(validator, "test_google_access", return_value=True):
                    with patch.object(
                        validator,
                        "get_geo_info",
                        return_value={
                            "country_code": "US",
                            "country_name": "United States",
                            "state": "CA",
                            "city": "SF",
                        },
                    ):
                        with patch.object(
                            validator,
                            "detect_proxy_type",
                            return_value={
                                "proxy_type": "datacenter",
                                "isp": "Amazon",
                                "org": "AWS",
                            },
                        ):
                            result = await validator.validate_comprehensive(
                                "http://1.2.3.4:8080", "1.2.3.4"
                            )

        assert result.success is True
        assert result.latency_ms == 150
        assert result.anonymity == "elite"
        assert result.can_access_google is True
        assert result.country_code == "US"
        assert result.proxy_type == "datacenter"

    @pytest.mark.asyncio
    async def test_validate_comprehensive_connectivity_failure(self, validator):
        """Test comprehensive validation when connectivity fails"""
        with patch.object(
            validator,
            "validate_connectivity",
            return_value=(False, None, "Connection timeout"),
        ):
            result = await validator.validate_comprehensive(
                "http://1.2.3.4:8080", "1.2.3.4"
            )

        assert result.success is False
        assert result.error_message == "Connection timeout"
        assert result.latency_ms is None

    # ==================== BATCH VALIDATION ====================

    @pytest.mark.asyncio
    async def test_validate_batch_success(self, validator):
        """Test batch validation of multiple proxies"""
        proxies = [
            ("http://1.2.3.4:8080", "1.2.3.4"),
            ("http://5.6.7.8:3128", "5.6.7.8"),
        ]

        mock_result = ValidationResult(success=True, latency_ms=100, anonymity="elite")

        with patch.object(
            validator, "validate_comprehensive", return_value=mock_result
        ):
            results = await validator.validate_batch(proxies)

        assert len(results) == 2
        assert all(result[1].success for result in results)

    @pytest.mark.asyncio
    async def test_validate_batch_mixed_results(self, validator):
        """Test batch validation with mixed success/failure"""

        async def mock_validate(proxy_url, ip):
            if "1.2.3.4" in proxy_url:
                return ValidationResult(success=True, latency_ms=100)
            else:
                return ValidationResult(success=False, error_message="Failed")

        proxies = [
            ("http://1.2.3.4:8080", "1.2.3.4"),
            ("http://9.9.9.9:8080", "9.9.9.9"),
        ]

        with patch.object(
            validator, "validate_comprehensive", side_effect=mock_validate
        ):
            results = await validator.validate_batch(proxies)

        assert len(results) == 2
        assert results[0][1].success is True
        assert results[1][1].success is False

    @pytest.mark.asyncio
    async def test_validate_batch_exception_handling(self, validator):
        """Test batch validation handles exceptions gracefully"""
        proxies = [
            ("http://1.2.3.4:8080", "1.2.3.4"),
        ]

        with patch.object(
            validator, "validate_comprehensive", side_effect=Exception("Test error")
        ):
            results = await validator.validate_batch(proxies)

        assert len(results) == 1
        assert results[0][1].success is False
        assert "Test error" in results[0][1].error_message
