import pytest
import os
from app.grabber.github_grabber import GitHubGrabber
from app.models.source import SourceConfig, SourceType


class TestGrabberIntegration:
    @pytest.mark.asyncio
    async def test_extract_from_fixture_http(self):
        fixture_path = os.path.join(
            os.path.dirname(__file__), "../fixtures/github_raw_http.txt"
        )

        with open(fixture_path, "r") as f:
            content = f.read()

        grabber = GitHubGrabber()

        proxies = await grabber.parse_content(content, SourceType.GITHUB_RAW)

        assert len(proxies) >= 4
        assert all(p.protocol == "http" for p in proxies)
        assert all(1 <= p.port <= 65535 for p in proxies)

    @pytest.mark.asyncio
    async def test_extract_from_fixture_mixed(self):
        fixture_path = os.path.join(
            os.path.dirname(__file__), "../fixtures/github_raw_mixed.txt"
        )

        with open(fixture_path, "r") as f:
            content = f.read()

        grabber = GitHubGrabber()
        proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)

        protocols = {p.protocol for p in proxies}

        assert "http" in protocols
        assert len(proxies) >= 3

    @pytest.mark.asyncio
    async def test_base64_subscription_fixture(self):
        fixture_path = os.path.join(
            os.path.dirname(__file__), "../fixtures/subscription_vmess.txt"
        )

        with open(fixture_path, "r") as f:
            content = f.read().strip()

        grabber = GitHubGrabber()
        proxies = await grabber.parse_content(content, SourceType.SUBSCRIPTION_BASE64)

        assert len(proxies) >= 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_github_url_skip(self):
        pytest.skip("Real URL test - run with: pytest -m integration")
