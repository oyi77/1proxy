import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
import os
from typing import List
from app.grabber.base import BaseGrabber
from app.models.source import SourceConfig, SourceType
from app.models.proxy import Proxy
from app.grabber.registry import ProviderRegistry

@ProviderRegistry.register(SourceType.GENERIC_TEXT)
@ProviderRegistry.register(SourceType.TOR_EXIT)


class WebGrabber(BaseGrabber):
    """
    Generic web scraper for extracting proxies from regular websites.
    Uses BeautifulSoup to parse HTML and extract proxy information.
    """

    async def fetch_content(self, source: SourceConfig) -> str:
        """Fetch content from a web URL and extract text/links"""
        url = str(source.url)

        # Handle GitHub repository pages - try to find raw proxy files
        if "github.com" in url and "/raw/" not in url:
            # Try to find common proxy file patterns
            proxy_files = [
                "http.txt",
                "https.txt",
                "socks4.txt",
                "socks5.txt",
                "proxies.txt",
                "proxy.txt",
                "all.txt",
                "raw.txt",
            ]

            for proxy_file in proxy_files:
                raw_url = url.replace("github.com", "raw.githubusercontent.com")
                raw_url = raw_url.replace("/blob/", "/")
                if not raw_url.endswith(proxy_file):
                    raw_url = f"{raw_url.rstrip('/')}/{proxy_file}"

                try:
                    content = await self._fetch_raw_url(raw_url)
                    if content and self._has_proxy_content(content):
                        return content
                except Exception:
                    continue

            # If no raw files found, try scraping the main page
            return await self._fetch_and_parse_html(url)
        else:
            return await self._fetch_raw_url(url)

    async def _fetch_raw_url(self, url: str) -> str:
        """Fetch raw content from URL"""
        max_bytes = int(os.getenv("SOURCE_MAX_BYTES", "5000000"))
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            content_length = response.content_length
                            if (
                                content_length is not None
                                and content_length > max_bytes
                            ):
                                raise ValueError(
                                    f"Source content too large (> {max_bytes} bytes)"
                                )

                            raw = await response.content.read(max_bytes + 1)
                            if len(raw) > max_bytes:
                                raise ValueError(
                                    f"Source content too large (> {max_bytes} bytes)"
                                )

                            return raw.decode("utf-8", errors="replace")
                        elif response.status == 404:
                            raise FileNotFoundError(f"URL not found: {url}")
                        else:
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(self.retry_delay)
                                continue
                            response.raise_for_status()

            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise

            except aiohttp.ClientError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise

        raise RuntimeError(f"Failed to fetch after {self.max_retries} attempts")

    async def _fetch_and_parse_html(self, url: str) -> str:
        """Fetch HTML page and extract proxy information"""
        html_content = await self._fetch_raw_url(url)

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        extracted_text = []

        # Look for proxy patterns in different elements
        # 1. Pre and code tags (common for raw text)
        for element in soup.find_all(["pre", "code"]):
            text = element.get_text()
            if self._has_proxy_content(text):
                extracted_text.append(text)

        # 2. Look for tables with proxy data
        for table in soup.find_all("table"):
            rows = []
            for row in table.find_all("tr"):
                cells = [cell.get_text().strip() for cell in row.find_all(["td", "th"])]
                # Check if row looks like proxy data (IP:PORT pattern)
                row_text = " ".join(cells)
                if self._has_proxy_content(row_text):
                    rows.append(row_text)
            if rows:
                extracted_text.extend(rows)

        # 3. Look for list items
        for li in soup.find_all("li"):
            text = li.get_text()
            if self._has_proxy_content(text):
                extracted_text.append(text)

        # 4. Look in anchor tags for proxy links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Check if link points to raw file
            if any(ext in href.lower() for ext in [".txt", ".csv", ".dat"]):
                try:
                    if not href.startswith("http"):
                        # Make relative URL absolute
                        from urllib.parse import urljoin

                        href = urljoin(url, href)

                    raw_content = await self._fetch_raw_url(href)
                    if self._has_proxy_content(raw_content):
                        extracted_text.append(raw_content)
                except Exception:
                    continue

        # Join all extracted text
        return "\n".join(extracted_text) if extracted_text else html_content

    def _has_proxy_content(self, text: str) -> bool:
        """Check if text contains proxy patterns"""
        # IP:PORT pattern
        ip_port_pattern = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):[0-9]{1,5}\b"
        return bool(re.search(ip_port_pattern, text))

    async def extract_proxies(self, source: SourceConfig) -> List[Proxy]:
        """Extract proxies from web source"""
        content = await self.fetch_content(source)
        return await self.parse_content(content, source.type)
