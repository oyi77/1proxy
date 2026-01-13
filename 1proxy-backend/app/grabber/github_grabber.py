import aiohttp
import asyncio
from app.grabber.base import BaseGrabber
from app.models.source import SourceConfig


class GitHubGrabber(BaseGrabber):
    async def fetch_content(self, source: SourceConfig) -> str:
        url = str(source.url)

        if "github.com" in url and "/raw/" in url:
            url = url.replace("github.com", "raw.githubusercontent.com")
            url = url.replace("/raw/", "/")

        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            return await response.text()
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

            except aiohttp.ClientError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise

        raise RuntimeError(f"Failed to fetch after {self.max_retries} attempts")
