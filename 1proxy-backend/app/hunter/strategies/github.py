import os
import aiohttp
import logging
from typing import List
from datetime import datetime, timedelta
from app.hunter.strategy import BaseStrategy

logger = logging.getLogger(__name__)


class GitHubStrategy(BaseStrategy):
    BASE_URL = "https://api.github.com/search/code"

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")

    @property
    def name(self) -> str:
        return "github"

    async def discover(self) -> List[str]:
        """
        Search GitHub for recently updated proxy files.
        """
        urls = []
        # Search queries to try
        queries = [
            "filename:proxy.txt",
            "filename:proxies.txt",
            "extension:yaml proxies",
            "extension:txt vmess://",
        ]

        # Calculate date for "pushed:>" filter (last 24h)
        yesterday = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d")

        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        async with aiohttp.ClientSession() as session:
            for q in queries:
                try:
                    # Construct query with date filter
                    full_query = f"{q} pushed:>{yesterday}"
                    params = {
                        "q": full_query,
                        "sort": "indexed",
                        "order": "desc",
                        "per_page": 10,  # Limit to top 10 per query to save quota
                    }

                    async with session.get(
                        self.BASE_URL, params=params, headers=headers
                    ) as resp:
                        if resp.status == 401:
                            logger.warning(
                                "GitHub API authentication failed (401). "
                                "Ensure GITHUB_TOKEN is valid or unset it to use public rate limits."
                            )
                            # If token is invalid, try removing it for next iterations
                            if "Authorization" in headers:
                                del headers["Authorization"]
                                continue
                            break

                        if resp.status == 403:
                            logger.warning("GitHub API rate limit exceeded")
                            break

                        if resp.status != 200:
                            logger.error(f"GitHub Search failed: {resp.status}")
                            continue

                        data = await resp.json()
                        items = data.get("items", [])

                        for item in items:
                            # Convert blob URL to raw URL
                            # Blob: https://github.com/user/repo/blob/main/file.txt
                            # Raw: https://raw.githubusercontent.com/user/repo/main/file.txt
                            html_url = item.get("html_url", "")
                            if html_url:
                                raw_url = html_url.replace(
                                    "github.com", "raw.githubusercontent.com"
                                ).replace("/blob/", "/")
                                urls.append(raw_url)

                except Exception as e:
                    logger.error(f"Error in GitHub strategy: {str(e)}")

        return list(set(urls))  # Deduplicate
