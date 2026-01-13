import pytest
from abc import ABC
from app.grabber.base import BaseGrabber
from app.models.source import SourceConfig, SourceType
from app.models.proxy import Proxy


class ConcreteGrabber(BaseGrabber):
    async def fetch_content(self, source: SourceConfig) -> str:
        return "192.168.1.1:8080\n10.0.0.1:3128"


class TestBaseGrabber:
    def test_base_grabber_is_abstract(self):
        with pytest.raises(TypeError):
            BaseGrabber()

    @pytest.mark.asyncio
    async def test_extract_proxies_abstract_method(self):
        grabber = ConcreteGrabber()
        source = SourceConfig(
            url="http://example.com/list.txt", type=SourceType.GENERIC_TEXT
        )

        assert hasattr(grabber, "extract_proxies")

        result = await grabber.extract_proxies(source)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_parse_content_http_proxies(self):
        grabber = ConcreteGrabber()
        content = "192.168.1.1:8080\n10.0.0.1:3128"

        proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)

        assert len(proxies) == 2
        assert all(isinstance(p, Proxy) for p in proxies)
        assert proxies[0].ip == "192.168.1.1"
        assert proxies[0].port == 8080

    @pytest.mark.asyncio
    async def test_parse_content_mixed_protocols(self):
        grabber = ConcreteGrabber()
        content = """
        192.168.1.1:8080
        vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDN9
        vless://uuid@10.0.0.1:443?type=tcp
        """

        proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)

        assert len(proxies) >= 2

    @pytest.mark.asyncio
    async def test_retry_logic(self):
        grabber = ConcreteGrabber()

        assert hasattr(grabber, "max_retries")
        assert hasattr(grabber, "retry_delay")
