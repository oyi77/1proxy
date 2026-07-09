import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.grabber.github_grabber import GitHubGrabber
from app.grabber.web_grabber import WebGrabber
from app.models.source import SourceConfig, SourceType


def _mock_session_with_response(status: int, body: bytes = b"ok", content_length: int | None = None):
    """Build a mock aiohttp.ClientSession that returns one response."""
    resp = MagicMock()
    resp.status = status
    resp.content_length = content_length
    resp.content = MagicMock()
    resp.content.read = AsyncMock(return_value=body)
    resp.raise_for_status = MagicMock()

    resp_cm = MagicMock()
    resp_cm.__aenter__ = AsyncMock(return_value=resp)
    resp_cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.get = MagicMock(return_value=resp_cm)
    session.post = MagicMock(return_value=resp_cm)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return session_cm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_github_grabber_rejects_oversized_content_by_content_length(monkeypatch):
    monkeypatch.setenv("SOURCE_MAX_BYTES", "10")

    grabber = GitHubGrabber()
    source = SourceConfig(
        url="https://raw.githubusercontent.com/user/repo/main/list.txt",
        type=SourceType.GITHUB_RAW,
    )

    mock_session = _mock_session_with_response(200, b"ok", content_length=999)

    with patch("app.grabber.github_grabber.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(ValueError, match="too large"):
            await grabber.fetch_content(source)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_web_grabber_rejects_oversized_content_by_content_length(monkeypatch):
    monkeypatch.setenv("SOURCE_MAX_BYTES", "10")

    grabber = WebGrabber()
    source = SourceConfig(
        url="https://example.com/list.txt",
        type=SourceType.GENERIC_TEXT,
    )

    mock_session = _mock_session_with_response(200, b"ok", content_length=999)

    with patch("app.grabber.web_grabber.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(ValueError, match="too large"):
            await grabber.fetch_content(source)
