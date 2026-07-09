import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.hunter.strategies.github import GitHubStrategy
from app.hunter.strategies.ai import AIStrategy
from app.hunter.strategies.search import SearchStrategy


def _make_session_mock(responses: list[dict]) -> MagicMock:
    """
    Build a mock aiohttp.ClientSession whose get/post return responses in order.
    Each entry in `responses` is a dict: {status, json?, text?, body?}
    """
    call_count = [0]

    def _make_resp(spec: dict) -> MagicMock:
        resp = MagicMock()
        resp.status = spec.get("status", 200)

        payload = spec.get("json")
        text_body = spec.get("text") or spec.get("body", "")

        resp.json = AsyncMock(return_value=payload)
        resp.text = AsyncMock(return_value=text_body)

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=resp)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    def _side_effect(*_args, **_kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        return _make_resp(responses[idx])

    session = MagicMock()
    session.get = MagicMock(side_effect=_side_effect)
    session.post = MagicMock(side_effect=_side_effect)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return session_cm


@pytest.mark.asyncio
async def test_github_strategy():
    strategy = GitHubStrategy()

    github_payload = {
        "items": [
            {
                "html_url": "https://github.com/user/repo/blob/main/proxy.txt",
                "name": "proxy.txt",
            }
        ]
    }
    # 4 queries → 4 responses; repeat the last one
    responses = [{"status": 200, "json": github_payload}] * 4

    mock_session = _make_session_mock(responses)

    with patch("app.hunter.strategies.github.aiohttp.ClientSession", return_value=mock_session):
        urls = await strategy.discover()

    assert len(urls) > 0, f"Expected URLs, got empty list. responses={responses}"
    assert "raw.githubusercontent.com" in urls[0]
    assert "/blob/" not in urls[0]


@pytest.mark.asyncio
async def test_ai_strategy():
    strategy = AIStrategy()

    mock_choice = MagicMock()
    mock_choice.message.content = (
        "Sure! https://pastebin.com/raw/abcd and https://github.com/raw/xyz"
    )

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with (
        patch("app.hunter.strategies.ai.AsyncClient") as mock_client_cls,
        patch("app.hunter.strategies.ai.HAS_G4F", True),
        patch("app.hunter.strategies.ai.RetryProvider", MagicMock()),
        patch("app.hunter.strategies.ai.PollinationsAI", MagicMock()),
        patch("app.hunter.strategies.ai.BlackboxPro", MagicMock()),
    ):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        urls = await strategy.discover()

    assert len(urls) > 0
    assert "https://pastebin.com/raw/abcd" in urls
    assert "https://github.com/raw/xyz" in urls


@pytest.mark.asyncio
async def test_search_strategy():
    strategy = SearchStrategy()

    ddg_html = (
        '<html><body>'
        '<a class="result__a" href="/l/?kh=-1&uddg=https%3A%2F%2Fpastebin.com%2Fraw%2Ffound">Link</a>'
        '</body></html>'
    )
    # 3 queries * up to 5 proxy retries each → many responses; all succeed
    responses = [{"status": 200, "text": ddg_html}] * 20

    mock_session = _make_session_mock(responses)

    mock_proxy = MagicMock()
    mock_proxy.protocol = "http"
    mock_proxy.ip = "1.1.1.1"
    mock_proxy.port = 8080

    async def async_db_gen():
        yield MagicMock()

    with (
        patch("app.hunter.strategies.search.db_storage.get_random_proxy", new_callable=AsyncMock) as mock_get_proxy,
        patch("app.hunter.strategies.search.get_db", return_value=async_db_gen()),
        patch("app.hunter.strategies.search.aiohttp.ClientSession", return_value=mock_session),
    ):
        mock_get_proxy.return_value = mock_proxy
        urls = await strategy.discover()

    assert len(urls) > 0, f"Expected URLs, got empty list"
    assert "https://pastebin.com/raw/found" in urls
