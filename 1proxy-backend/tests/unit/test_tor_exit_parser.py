import pytest
from app.grabber.parsers import TorExitParser
from app.models.proxy import Proxy


class TestTorExitParser:
    """Test Tor exit node JSON parsing."""

    def test_parse_valid_response(self):
        """Should extract SOCKS5 proxies from Onionoo JSON."""
        json_data = """
        {
            "relays": [
                {
                    "or_addresses": ["1.2.3.4:443", "5.6.7.8:9090"]
                },
                {
                    "or_addresses": ["9.10.11.12:80", "[::1]:443", "bad"]
                }
            ]
        }
        """
        proxies = TorExitParser.parse(json_data)
        assert len(proxies) == 3
        assert all(isinstance(p, Proxy) for p in proxies)
        assert all(p.protocol == "socks5" for p in proxies)
        assert proxies[0].ip == "1.2.3.4"
        assert proxies[0].port == 443
        assert proxies[1].ip == "5.6.7.8"
        assert proxies[1].port == 9090
        assert proxies[2].ip == "9.10.11.12"
        assert proxies[2].port == 80

    def test_parse_empty_response(self):
        """Should return empty list for no relays."""
        assert TorExitParser.parse('{"relays": []}') == []

    def test_parse_invalid_json(self):
        """Should return empty list for garbage."""
        assert TorExitParser.parse("not json") == []

    def test_parse_missing_relays_key(self):
        """Should handle missing relays field."""
        assert TorExitParser.parse('{}') == []

    def test_parse_skips_ipv6(self):
        """Should skip IPv6 addresses."""
        json_data = """
        {
            "relays": [
                {
                    "or_addresses": ["[::1]:443", "1.2.3.4:8080"]
                }
            ]
        }
        """
        proxies = TorExitParser.parse(json_data)
        assert len(proxies) == 1
        assert proxies[0].ip == "1.2.3.4"

    def test_parse_skips_invalid_ports(self):
        """Should skip entries with invalid ports."""
        json_data = """
        {
            "relays": [
                {
                    "or_addresses": ["1.2.3.4:99999", "5.6.7.8:-1"]
                }
            ]
        }
        """
        proxies = TorExitParser.parse(json_data)
        assert len(proxies) == 0

    def test_parse_skips_invalid_ips(self):
        """Should skip entries with invalid IPs."""
        json_data = """
        {
            "relays": [
                {
                    "or_addresses": ["999.999.999.999:80"]
                }
            ]
        }
        """
        proxies = TorExitParser.parse(json_data)
        assert len(proxies) == 0

    @pytest.mark.asyncio
    async def test_tor_exit_in_parse_content(self):
        """End-to-end: BaseGrabber.parse_content routes TOR_EXIT correctly."""
        from app.grabber.base import BaseGrabber
        from app.models.source import SourceType

        class TestGrabber(BaseGrabber):
            async def fetch_content(self, source):
                return source.url

        grabber = TestGrabber()
        json_data = """
        {
            "relays": [
                {"or_addresses": ["1.2.3.4:443"]}
            ]
        }
        """
        proxies = await grabber.parse_content(json_data, SourceType.TOR_EXIT)
        assert len(proxies) == 1
        assert proxies[0].protocol == "socks5"
        assert proxies[0].source == "tor_exit"
