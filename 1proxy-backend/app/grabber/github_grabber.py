import aiohttp
import asyncio
import os
from app.grabber.base import BaseGrabber
from app.models.source import SourceConfig, SourceType
from app.grabber.registry import ProviderRegistry

@ProviderRegistry.register(SourceType.GITHUB_RAW)
@ProviderRegistry.register(SourceType.SUBSCRIPTION_BASE64)


class GitHubGrabber(BaseGrabber):
    async def fetch_content(self, source: SourceConfig) -> str:
        url = str(source.url)

        max_bytes = int(os.getenv("SOURCE_MAX_BYTES", "5000000"))

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
