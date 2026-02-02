from typing import List
import aiohttp
import asyncio
from app.hunter.strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class RedditStrategy(BaseStrategy):
    """
    Discovers proxy lists from Reddit communities.
    """

    SUBREDDITS = ["proxy", "proxylists", "free_proxy_list"]

    @property
    def name(self) -> str:
        return "reddit"

    @property
    def rate_limit(self) -> float:
        return 1.0  # 1 request per second

    async def discover(self) -> List[str]:
        candidates = []
        async with aiohttp.ClientSession() as session:
            for subreddit in self.SUBREDDITS:
                try:
                    # Respect rate limits
                    await asyncio.sleep(self.rate_limit)

                    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=5"
                    async with session.get(
                        url, headers={"User-Agent": "1proxy-hunter/2.0"}
                    ) as response:
                        if response.status != 200:
                            logger.warning(
                                f"Reddit API returned {response.status} for r/{subreddit}"
                            )
                            continue

                        data = await response.json()
                        for post in data.get("data", {}).get("children", []):
                            content = post["data"].get("selftext", "")
                            # Basic URL extraction could go here, but for now we return post URL
                            # or leave extraction to the UniversalExtractor if the content IS the list.
                            # We'll assume the selftext might contain external URLs or be the list itself.
                            # For simplicity in this iteration:
                            candidates.append(post["data"]["url"])

                except Exception as e:
                    logger.error(f"Error scraping r/{subreddit}: {e}")

        return list(set(candidates))
