import pytest
from app.grabber.github_grabber import GitHubGrabber
from app.grabber.patterns import ProxyPatterns
from app.models.source import SourceType


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_content(self):
        grabber = GitHubGrabber()
        proxies = await grabber.parse_content("", SourceType.GENERIC_TEXT)

        assert proxies == []

    @pytest.mark.asyncio
    async def test_whitespace_only(self):
        grabber = GitHubGrabber()
        content = "   \n\n\t\t\n   "
        proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)

        assert proxies == []

    @pytest.mark.asyncio
    async def test_invalid_ip_format(self):
        grabber = GitHubGrabber()
        content = "999.999.999.999:8080\n256.1.1.1:3128"
        proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)

        assert len(proxies) == 0

    @pytest.mark.asyncio
    async def test_valid_port_range(self):
        grabber = GitHubGrabber()
        content = "192.168.1.1:80\n192.168.1.2:443\n192.168.1.3:65535"
        proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)

        assert all(1 <= p.port <= 65535 for p in proxies)

    @pytest.mark.asyncio
    async def test_duplicate_proxies(self):
        grabber = GitHubGrabber()
        content = """
        192.168.1.1:8080
        192.168.1.1:8080
        192.168.1.1:8080
        """
        proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)

        assert len(proxies) >= 1

    @pytest.mark.asyncio
    async def test_mixed_line_endings(self):
        grabber = GitHubGrabber()
        content = "192.168.1.1:8080\r\n10.0.0.1:3128\n172.16.0.1:9999\r"
        proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)

        assert len(proxies) >= 2

    @pytest.mark.asyncio
    async def test_comments_and_noise(self):
        grabber = GitHubGrabber()
        content = """
        # This is a comment
        192.168.1.1:8080
        // Another comment
        10.0.0.1:3128
        """
        proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)

        assert len(proxies) == 2

    def test_ip_validation(self):
        assert ProxyPatterns.is_valid_ip("192.168.1.1") is True
        assert ProxyPatterns.is_valid_ip("255.255.255.255") is True
        assert ProxyPatterns.is_valid_ip("0.0.0.0") is True
        assert ProxyPatterns.is_valid_ip("256.1.1.1") is False
        assert ProxyPatterns.is_valid_ip("192.168.1") is False
        assert ProxyPatterns.is_valid_ip("not.an.ip.address") is False

    def test_port_validation(self):
        assert ProxyPatterns.is_valid_port(1) is True
        assert ProxyPatterns.is_valid_port(80) is True
        assert ProxyPatterns.is_valid_port(443) is True
        assert ProxyPatterns.is_valid_port(65535) is True
        assert ProxyPatterns.is_valid_port(0) is False
        assert ProxyPatterns.is_valid_port(65536) is False
        assert ProxyPatterns.is_valid_port(-1) is False
