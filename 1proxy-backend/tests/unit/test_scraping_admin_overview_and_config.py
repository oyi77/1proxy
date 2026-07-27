"""Tests for admin scraping overview and config endpoints."""
import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_scraping_overview_does_not_raise(monkeypatch):
    from app.admin import scraping_admin
    from app.db_models import ProxySource
    from unittest.mock import AsyncMock

    mock_db = type(
        "MockDB",
        (),
        {"scalar": AsyncMock(return_value=0)},
    )()

    result = await scraping_admin.get_scraping_overview(db=mock_db)
    assert result["active_sessions"] >= 0
    assert isinstance(result["total_sources"], int)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_scraping_config_returns_valid_response(monkeypatch):
    from app.admin import scraping_admin
    from unittest.mock import AsyncMock

    class FakeService:
        def get_overall_stats(self):
            return {
                "total_requests": 10,
                "successful_requests": 8,
                "total_data_bytes": 5000,
                "avg_response_time": 0.15,
            }

    monkeypatch.setattr(
        scraping_admin,
        "EnhancedScrapingService",
        lambda: FakeService(),
    )
    scraping_admin.active_sessions.clear()
    mock_db = type(
        "MockDB",
        (),
        {"scalar": AsyncMock(return_value=0)},
    )()

    result = await scraping_admin.get_scraping_config(db=mock_db)
    assert isinstance(result.module_configs, dict)
    assert isinstance(result.active_sessions, list)
