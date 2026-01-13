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

    # Mock g4f AsyncClient
    with patch("app.hunter.strategies.ai.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = (
            "Sure! https://pastebin.com/raw/abcd and https://github.com/raw/xyz"
        )

        mock_client.chat.completions.create.return_value = mock_response

        urls = await strategy.discover()

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
