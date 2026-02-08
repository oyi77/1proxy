import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_scraping_overview_does_not_raise(monkeypatch):
    from app.admin import scraping_admin

    class FakePerf:
        def get_overall_stats(self):
            return {"total_requests": 0}

    class FakeService:
        performance_monitor = FakePerf()

    async def fake_count_sources(self, _db):
        return 10

    async def fake_count_proxies(self, _db):
        return 20

    async def fake_get_stats(self, _db):
        return {"total_proxies": 5}

    async def fake_hunter_stats(_db):
        return {"total_candidates": 2}

    monkeypatch.setattr(scraping_admin, "get_enhanced_service", lambda: FakeService())
    monkeypatch.setattr(
        scraping_admin,
        "db_storage",
        type(
            "DB",
            (),
            {
                "count_sources": fake_count_sources,
                "count_proxies": fake_count_proxies,
                "get_stats": fake_get_stats,
            },
        )(),
        raising=False,
    )
    monkeypatch.setattr(
        scraping_admin.extended_db_storage, "get_hunter_statistics", fake_hunter_stats
    )

    result = await scraping_admin.get_scraping_overview(db=None)
    assert result["proxy_sources"]["total"] == 10
    assert isinstance(result["sessions"]["active"], int)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_scraping_config_awaits_module_config(monkeypatch):
    from app.admin import scraping_admin

    class FakeConfigManager:
        config = {"global": {"max_concurrent_requests": 50}}

        def get_global_config(self):
            return {"max_concurrent_requests": 50}

        async def get_config(self, module_name: str):
            return {"module": module_name}

    class FakePerf:
        def get_overall_stats(self):
            return {"total_requests": 0}

    class FakeService:
        config_manager = FakeConfigManager()
        performance_monitor = FakePerf()

    monkeypatch.setattr(scraping_admin, "get_enhanced_service", lambda: FakeService())
    scraping_admin.active_sessions.clear()

    result = await scraping_admin.get_scraping_config()
    # Ensure resolved dict, not coroutine
    assert result.module_configs["github_grabber"]["module"] == "github_grabber"
    assert isinstance(result.active_sessions, list)
