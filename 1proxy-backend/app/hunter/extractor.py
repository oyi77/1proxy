import re
import logging
from typing import List
from bs4 import BeautifulSoup

from app.models.proxy import Proxy
from app.grabber.patterns import ProxyPatterns
from app.grabber.parsers import VMessParser, VLESSParser, TrojanParser, SSParser
from app.utils.base64_decoder import SubscriptionDecoder

logger = logging.getLogger(__name__)


class UniversalExtractor:
    """
    Extracts proxies from any text content (HTML, Base64, Raw).
    """

    @classmethod
    def extract_proxies(
        cls, content: str, source_url: str = "discovered"
    ) -> List[Proxy]:
        """
        Main entry point. Tries to decode and parse proxies from string content.
        """
        proxies: List[Proxy] = []

        # 1. Clean HTML if present
        if cls._is_html(content):
            content = cls._strip_html(content)

        # 2. Try Base64 Decoding (Optimistic)
        decoded_content = cls._try_decode(content)

        # 3. Parse content (both raw and decoded)
        # We parse both because sometimes valid text is mixed with base64
        proxies.extend(cls._parse_text(content, source_url))
        if decoded_content != content:
            proxies.extend(cls._parse_text(decoded_content, source_url))

        # Deduplicate by URL/IP:Port
        unique_proxies = {f"{p.ip}:{p.port}": p for p in proxies}
        return list(unique_proxies.values())

    @classmethod
    def _is_html(cls, text: str) -> bool:
        return bool(re.search(r"<!DOCTYPE html>|<html", text, re.IGNORECASE))

    @classmethod
    def _strip_html(cls, html: str) -> str:
        try:
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(separator="\n")
        except Exception:
            return html

    @classmethod
    def _try_decode(cls, text: str) -> str:
        try:
            return SubscriptionDecoder.decode(text)
        except Exception:
            return text

    @classmethod
    def _parse_text(cls, text: str, source_url: str) -> List[Proxy]:
        proxies = []

        # HTTP/S Proxies (IP:Port)
        http_matches = ProxyPatterns.extract_http_proxies(text)
        for ip, port in http_matches:
            # We assume HTTP unless verified otherwise
            proxies.append(
                Proxy(ip=ip, port=int(port), protocol="http", source=source_url)
            )

        # VMess
        for url in ProxyPatterns.extract_vmess_urls(text):
            try:
                proxies.append(VMessParser.parse(url))
            except Exception:
                pass

        # VLESS
        for url in ProxyPatterns.extract_vless_urls(text):
            try:
                proxies.append(VLESSParser.parse(url))
            except Exception:
                pass

        # Trojan
        for url in ProxyPatterns.extract_trojan_urls(text):
            try:
                proxies.append(TrojanParser.parse(url))
            except Exception:
                pass

        # Shadowsocks
        for url in ProxyPatterns.extract_ss_urls(text):
            try:
                proxies.append(SSParser.parse(url))
            except Exception:
                pass

        return proxies
