import pytest

from aioresponses import aioresponses

from app.grabber.github_grabber import GitHubGrabber
from app.grabber.web_grabber import WebGrabber
from app.models.source import SourceConfig, SourceType


@pytest.mark.unit
@pytest.mark.asyncio
async def test_github_grabber_rejects_oversized_content_by_content_length(monkeypatch):
    monkeypatch.setenv("SOURCE_MAX_BYTES", "10")

    grabber = GitHubGrabber()
    source = SourceConfig(
        url="https://raw.githubusercontent.com/user/repo/main/list.txt",
        type=SourceType.GITHUB_RAW,
    )

    with aioresponses() as mocked:
        mocked.get(
            str(source.url),
            status=200,
            body="ok",
            headers={"Content-Length": "999"},
        )

        with pytest.raises(ValueError):
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

    with aioresponses() as mocked:
        mocked.get(
            str(source.url),
            status=200,
            body="ok",
            headers={"Content-Length": "999"},
        )

        with pytest.raises(ValueError):
            await grabber.fetch_content(source)
