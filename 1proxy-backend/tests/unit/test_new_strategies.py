import pytest
from unittest.mock import MagicMock, AsyncMock

# Imports that should fail
from app.hunter.strategies.reddit import RedditStrategy
from app.hunter.strategies.pastebin import PastebinStrategy


@pytest.mark.asyncio
async def test_reddit_strategy_initialization():
    """Test RedditStrategy initialization."""
    strategy = RedditStrategy()
    assert strategy.name == "reddit"
    assert strategy.rate_limit is not None


@pytest.mark.asyncio
async def test_pastebin_strategy_initialization():
    """Test PastebinStrategy initialization."""
    strategy = PastebinStrategy()
    assert strategy.name == "pastebin"
    assert strategy.rate_limit is not None
