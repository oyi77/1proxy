import aiohttp
import asyncio
import socket
import ipaddress
from urllib.parse import urlparse
from typing import Optional, List
from pydantic import BaseModel

from app.models import SourceConfig, SourceType
from app.grabber import GitHubGrabber


class SourceValidationResult(BaseModel):
    valid: bool
    error_message: Optional[str] = None
    proxy_count: int = 0
    sample_proxies: List[str] = []


class SourceValidator:
    def __init__(self, timeout: int = 15):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.grabber = GitHubGrabber()

    def is_internal_url(self, url: str) -> bool:
        """Check if the URL points to an internal network (SSRF protection)."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return True

            # Check for common internal hostnames
            if hostname.lower() in ["localhost", "127.0.0.1", "::1", "0.0.0.0"]:
                return True

            # Resolve hostname to IP and check if it's private
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip = item[4][0]
                if ipaddress.ip_address(ip).is_private:
                    return True
                if ipaddress.ip_address(ip).is_loopback:
                    return True
                if ipaddress.ip_address(ip).is_link_local:
                    return True

            return False
        except Exception:
            # If resolution fails, we'll treat it as potentially unsafe or handle it in reachable check
            return False

    async def validate_url_reachable(self, url: str) -> tuple[bool, Optional[str]]:
        if self.is_internal_url(url):
            return False, "Access to internal networks is restricted (SSRF protection)"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, ssl=False) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("Content-Type", "")
                        content = await resp.text()

                        if len(content) < 10:
                            return False, "Source content too short (< 10 characters)"

                        if len(content) > 50_000_000:
                            return False, "Source content too large (> 50MB)"

                        return True, None
                    elif resp.status == 404:
                        return False, "Source not found (404)"
                    elif resp.status == 403:
                        return False, "Access forbidden (403)"
                    elif resp.status >= 500:
                        return False, f"Server error ({resp.status})"
                    else:
                        return False, f"HTTP error {resp.status}"

        except asyncio.TimeoutError:
            return False, "Connection timeout - source took too long to respond"
        except aiohttp.ClientConnectorError:
            return False, "Cannot connect to source URL"
        except Exception as e:
            return False, f"Error: {str(e)[:100]}"

    async def validate_source_format(
        self, source: SourceConfig
    ) -> tuple[bool, Optional[str]]:
        url_str = str(source.url)

        if source.type == SourceType.GITHUB_RAW:
            if "github.com" not in url_str:
                return False, "GitHub source must contain 'github.com'"
            if "/raw/" not in url_str and "githubusercontent.com" not in url_str:
                return False, "GitHub source must be a raw file URL"

        elif source.type == SourceType.SUBSCRIPTION_BASE64:
            if not url_str.startswith(("http://", "https://")):
                return False, "Subscription source must start with http:// or https://"

        return True, None

    async def test_proxy_extraction(
        self, source: SourceConfig
    ) -> tuple[int, List[str], Optional[str]]:
        try:
            proxies = await self.grabber.extract_proxies(source)

            if not proxies:
                return 0, [], "No proxies found in source"

            proxy_urls = [p.url for p in proxies[:5]]
            return len(proxies), proxy_urls, None

        except Exception as e:
            return 0, [], f"Failed to extract proxies: {str(e)[:100]}"

    async def validate_source(self, source: SourceConfig) -> SourceValidationResult:
        is_format_valid, format_error = await self.validate_source_format(source)
        if not is_format_valid:
            return SourceValidationResult(valid=False, error_message=format_error)

        is_reachable, reachable_error = await self.validate_url_reachable(
            str(source.url)
        )
        if not is_reachable:
            return SourceValidationResult(valid=False, error_message=reachable_error)

        (
            proxy_count,
            sample_proxies,
            extraction_error,
        ) = await self.test_proxy_extraction(source)
        if extraction_error:
            return SourceValidationResult(
                valid=False, error_message=extraction_error, proxy_count=proxy_count
            )

        return SourceValidationResult(
            valid=True, proxy_count=proxy_count, sample_proxies=sample_proxies
        )


source_validator = SourceValidator()
