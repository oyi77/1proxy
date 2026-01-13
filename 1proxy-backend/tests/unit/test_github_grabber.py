import pytest
import asyncio
from aioresponses import aioresponses
from app.grabber.github_grabber import GitHubGrabber
from app.models.source import SourceConfig, SourceType


class TestGitHubGrabber:
    @pytest.mark.asyncio
    async def test_fetch_content_success(self):
        grabber = GitHubGrabber()
        source = SourceConfig(
            url="https://raw.githubusercontent.com/user/repo/main/list.txt",
            type=SourceType.GITHUB_RAW,
        )

        with aioresponses() as mocked:
            mocked.get(
                str(source.url), status=200, body="192.168.1.1:8080\n10.0.0.1:3128"
            )

            content = await grabber.fetch_content(source)

            assert "192.168.1.1:8080" in content
            assert "10.0.0.1:3128" in content

    @pytest.mark.asyncio
    async def test_fetch_content_timeout(self):
        grabber = GitHubGrabber(timeout=1)
        source = SourceConfig(
            url="https://raw.githubusercontent.com/user/repo/main/list.txt",
            type=SourceType.GITHUB_RAW,
        )

        with aioresponses() as mocked:
            mocked.get(str(source.url), exception=asyncio.TimeoutError())

            with pytest.raises(Exception):
                await grabber.fetch_content(source)

    @pytest.mark.asyncio
    async def test_fetch_content_404(self):
        grabber = GitHubGrabber()
        source = SourceConfig(
            url="https://raw.githubusercontent.com/user/repo/main/notfound.txt",
            type=SourceType.GITHUB_RAW,
        )

        with aioresponses() as mocked:
            mocked.get(str(source.url), status=404)

            with pytest.raises(Exception):
                await grabber.fetch_content(source)

    @pytest.mark.asyncio
    async def test_extract_proxies_integration(self):
        grabber = GitHubGrabber()
        source = SourceConfig(
            url="https://raw.githubusercontent.com/user/repo/main/mixed.txt",
            type=SourceType.GITHUB_RAW,
        )

        mixed_content = """
        192.168.1.1:8080
        10.0.0.1:3128
        vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDN9
        vless://uuid@example.com:443?type=tcp
        """

        with aioresponses() as mocked:
            mocked.get(str(source.url), status=200, body=mixed_content)

            proxies = await grabber.extract_proxies(source)

            assert len(proxies) >= 2
            assert any(p.protocol == "http" for p in proxies)

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        grabber = GitHubGrabber(max_retries=3, retry_delay=0.1)
        source = SourceConfig(
            url="https://raw.githubusercontent.com/user/repo/main/list.txt",
            type=SourceType.GITHUB_RAW,
        )

        with aioresponses() as mocked:
            mocked.get(str(source.url), status=500)
            mocked.get(str(source.url), status=500)
            mocked.get(str(source.url), status=200, body="192.168.1.1:8080")

            content = await grabber.fetch_content(source)

            assert "192.168.1.1:8080" in content
