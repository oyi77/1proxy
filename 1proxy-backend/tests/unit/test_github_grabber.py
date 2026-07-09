import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.grabber.github_grabber import GitHubGrabber
from app.models.source import SourceConfig, SourceType


def _make_mock_response(status: int, body: str = "", headers: dict | None = None):
    """Build a mock aiohttp response context manager."""
    resp = MagicMock()
    resp.status = status
    resp.content_length = None
    if headers and "Content-Length" in headers:
        resp.content_length = int(headers["Content-Length"])

    raw_bytes = body.encode("utf-8")
    # content.read() returns bytes
    resp.content = MagicMock()
    resp.content.read = AsyncMock(return_value=raw_bytes)
    resp.raise_for_status = MagicMock()

    # Async context manager support
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_mock_session(*responses):
    """Build a mock ClientSession that returns responses in sequence."""
    session = MagicMock()
    session.get = MagicMock(side_effect=list(responses))

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return session_cm


class TestGitHubGrabber:
    @pytest.mark.asyncio
    async def test_fetch_content_success(self):
        grabber = GitHubGrabber()
        source = SourceConfig(
            url="https://raw.githubusercontent.com/user/repo/main/list.txt",
            type=SourceType.GITHUB_RAW,
        )

        body = "192.168.1.1:8080\n10.0.0.1:3128"
        mock_session_cm = _make_mock_session(_make_mock_response(200, body))

        with patch("app.grabber.github_grabber.aiohttp.ClientSession", return_value=mock_session_cm):
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

        resp_cm = MagicMock()
        resp_cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        resp_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.get = MagicMock(return_value=resp_cm)

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.grabber.github_grabber.aiohttp.ClientSession", return_value=session_cm):
            with pytest.raises(Exception):
                await grabber.fetch_content(source)

    @pytest.mark.asyncio
    async def test_fetch_content_404(self):
        grabber = GitHubGrabber()
        source = SourceConfig(
            url="https://raw.githubusercontent.com/user/repo/main/notfound.txt",
            type=SourceType.GITHUB_RAW,
        )

        mock_session_cm = _make_mock_session(_make_mock_response(404, ""))

        with patch("app.grabber.github_grabber.aiohttp.ClientSession", return_value=mock_session_cm):
            with pytest.raises(Exception):
                await grabber.fetch_content(source)

    @pytest.mark.asyncio
    async def test_extract_proxies_integration(self):
        grabber = GitHubGrabber()
        source = SourceConfig(
            url="https://raw.githubusercontent.com/user/repo/main/mixed.txt",
            type=SourceType.GITHUB_RAW,
        )

        mixed_content = (
            "192.168.1.1:8080\n"
            "10.0.0.1:3128\n"
            "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDN9\n"
            "vless://uuid@example.com:443?type=tcp\n"
        )

        mock_session_cm = _make_mock_session(_make_mock_response(200, mixed_content))

        with patch("app.grabber.github_grabber.aiohttp.ClientSession", return_value=mock_session_cm):
            proxies = await grabber.extract_proxies(source)

        assert len(proxies) >= 2
        assert any(p.protocol == "http" for p in proxies)

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        grabber = GitHubGrabber(max_retries=3, retry_delay=0.01)
        source = SourceConfig(
            url="https://raw.githubusercontent.com/user/repo/main/list.txt",
            type=SourceType.GITHUB_RAW,
        )

        # Three separate session context managers: 500, 500, 200
        session_cms = [
            _make_mock_session(_make_mock_response(500, "")),
            _make_mock_session(_make_mock_response(500, "")),
            _make_mock_session(_make_mock_response(200, "192.168.1.1:8080")),
        ]

        with patch("app.grabber.github_grabber.aiohttp.ClientSession", side_effect=session_cms):
            content = await grabber.fetch_content(source)

        assert "192.168.1.1:8080" in content
