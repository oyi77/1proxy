from abc import ABC, abstractmethod
from typing import List
import asyncio
from app.models.proxy import Proxy
from app.models.source import SourceConfig, SourceType
from app.grabber.patterns import ProxyPatterns
from app.grabber.parsers import VMessParser, VLESSParser, TrojanParser, SSParser
from app.utils.base64_decoder import SubscriptionDecoder


class BaseGrabber(ABC):
    def __init__(
        self, max_retries: int = 3, retry_delay: float = 1.0, timeout: int = 30
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    @abstractmethod
    async def fetch_content(self, source: SourceConfig) -> str:
        pass

    async def extract_proxies(self, source: SourceConfig) -> List[Proxy]:
        content = await self.fetch_content(source)

        if source.selector:
            proxies = await self._try_exact_selector(content, source)
            if proxies:
                return proxies

        proxies = await self.parse_content(content, source.type)

        return proxies

    async def _try_exact_selector(
        self, content: str, source: SourceConfig
    ) -> List[Proxy]:
        return []

    async def parse_content(self, content: str, source_type: SourceType) -> List[Proxy]:
        proxies = []

        if source_type == SourceType.SUBSCRIPTION_BASE64:
            try:
                content = SubscriptionDecoder.decode(content)
            except ValueError:
                pass

        http_matches = ProxyPatterns.extract_http_proxies(content)
        for ip, port in http_matches:
            proxies.append(
                Proxy(ip=ip, port=int(port), protocol="http", source=str(source_type))
            )

        vmess_urls = ProxyPatterns.extract_vmess_urls(content)
        for url in vmess_urls:
            try:
                proxy = VMessParser.parse(url)
                proxies.append(proxy)
            except ValueError:
                continue

        vless_urls = ProxyPatterns.extract_vless_urls(content)
        for url in vless_urls:
            try:
                proxy = VLESSParser.parse(url)
                proxies.append(proxy)
            except ValueError:
                continue

        trojan_urls = ProxyPatterns.extract_trojan_urls(content)
        for url in trojan_urls:
            try:
                proxy = TrojanParser.parse(url)
                proxies.append(proxy)
            except ValueError:
                continue

        ss_urls = ProxyPatterns.extract_ss_urls(content)
        for url in ss_urls:
            try:
                proxy = SSParser.parse(url)
                proxies.append(proxy)
            except ValueError:
                continue

        return proxies
