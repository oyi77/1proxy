import logging
import urllib.parse
from typing import List
import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.hunter.strategy import BaseStrategy
from app.db_storage import db_storage
from app.database import get_db

logger = logging.getLogger(__name__)


class SearchStrategy(BaseStrategy):
    SEARCH_URL = "https://html.duckduckgo.com/html/"

    @property
    def name(self) -> str:
        return "search"

    async def discover(self) -> List[str]:
        # We need a DB session to get proxies.
        # Since strategies are called from service, maybe service should provide session?
        # For now, we'll create a new one using the async generator manually or just use get_random_proxy which needs session.

        # Strategy: Get a session, get a proxy, make a request.
        found_urls = []

        queries = [
            'site:pastebin.com "vmess://"',
            'site:github.com "clash config" "proxies"',
            'intitle:"proxy list" "ss://"',
        ]

        # Get a DB session
        async for session in get_db():
            for query in queries:
                urls = await self._search_with_rotation(session, query)
                found_urls.extend(urls)
            break  # Just need one session context

        return list(set(found_urls))

    async def _search_with_rotation(
        self, session: AsyncSession, query: str
    ) -> List[str]:
        # Try up to 5 times with different proxies
        for _ in range(5):
            proxy = await db_storage.get_random_proxy(
                session=session,
                is_working=True,
                protocol="http",  # aiohttp prefers http/https proxies
            )

            if not proxy:
                logger.warning("No working proxies available for search strategy")
                return []

            proxy_url = f"{proxy.protocol}://{proxy.ip}:{proxy.port}"

            try:
                return await self._execute_search(query, proxy_url)
            except Exception as e:
                logger.debug(f"Search failed with proxy {proxy.ip}: {str(e)}")
                # Continue to next proxy

        return []

    async def _execute_search(self, query: str, proxy_url: str) -> List[str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        data = {"q": query}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.SEARCH_URL, data=data, headers=headers, proxy=proxy_url, timeout=10
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Status {resp.status}")

                html = await resp.text()
                return self._parse_duckduckgo(html)

    def _parse_duckduckgo(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        for link in soup.select(".result__a"):
            href = link.get("href")
            if href:
                # DuckDuckGo redirect link
                # format: /l/?kh=-1&uddg=https%3A%2F%2Fpastebin.com%2F...
                if "uddg=" in href:
                    parsed = urllib.parse.urlparse(href)
                    qs = urllib.parse.parse_qs(parsed.query)
                    real_url = qs.get("uddg", [None])[0]
                    if real_url:
                        urls.append(real_url)
        return urls
