import pytest
import re
from unittest.mock import patch, MagicMock, AsyncMock
from aioresponses import aioresponses
from app.hunter.strategies.github import GitHubStrategy
from app.hunter.strategies.ai import AIStrategy
from app.hunter.strategies.search import SearchStrategy


@pytest.mark.asyncio
async def test_github_strategy():
    strategy = GitHubStrategy()

    with aioresponses() as m:
        # Mock GitHub Search API
        m.get(
            re.compile(r"^https://api\.github\.com/search/code.*$"),
            payload={
                "items": [
                    {
                        "html_url": "https://github.com/user/repo/blob/main/proxy.txt",
                        "name": "proxy.txt",
                    }
                ]
            },
            repeat=True,
        )

        urls = await strategy.discover()

        assert len(urls) > 0
        # Check raw conversion
        assert "raw.githubusercontent.com" in urls[0]
        assert "/blob/" not in urls[0]


@pytest.mark.asyncio
async def test_ai_strategy():
    strategy = AIStrategy()

    # Create mock response structure
    mock_choice = MagicMock()
    mock_choice.message.content = (
        "Sure! https://pastebin.com/raw/abcd and https://github.com/raw/xyz"
    )

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    # Mock g4f components
    with (
        patch("app.hunter.strategies.ai.AsyncClient") as mock_client_cls,
        patch("app.hunter.strategies.ai.HAS_G4F", True),
        patch("app.hunter.strategies.ai.RetryProvider", MagicMock()),
        patch("app.hunter.strategies.ai.PollinationsAI", MagicMock()),
        patch("app.hunter.strategies.ai.BlackboxPro", MagicMock()),
    ):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        # Set return value for create
        mock_client.chat.completions.create.return_value = mock_response

        urls = await strategy.discover()

        # Debug info if fails
        if len(urls) != 2:
            print(f"\nDEBUG: discover returned {urls}")
            print(f"DEBUG: AsyncClient patched: {mock_client_cls.called}")
            print(f"DEBUG: create called: {mock_client.chat.completions.create.called}")

        assert len(urls) == 2
        assert "https://pastebin.com/raw/abcd" in urls
        assert "https://github.com/raw/xyz" in urls


@pytest.mark.asyncio
async def test_search_strategy():
    strategy = SearchStrategy()

    # Mock DB storage get_random_proxy
    with patch(
        "app.hunter.strategies.search.db_storage.get_random_proxy",
        new_callable=AsyncMock,
    ) as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.protocol = "http"
        mock_proxy.ip = "1.1.1.1"
        mock_proxy.port = 8080
        mock_get_proxy.return_value = mock_proxy

        # Mock aiohttp request to DuckDuckGo
        with aioresponses() as m:
            # Mock the POST request to html.duckduckgo.com
            m.post(
                "https://html.duckduckgo.com/html/",
                body='<html><body><a class="result__a" href="/l/?kh=-1&uddg=https%3A%2F%2Fpastebin.com%2Fraw%2Ffound">Link</a></body></html>',
                repeat=True,
            )

            # We also need to mock get_db to yield a fake session
            with patch("app.hunter.strategies.search.get_db") as mock_get_db:
                # Create an async generator mock
                async def async_gen():
                    yield MagicMock()

                mock_get_db.return_value = async_gen()

                urls = await strategy.discover()

                assert len(urls) > 0
                assert "https://pastebin.com/raw/found" in urls
