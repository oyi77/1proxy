import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.db_models import ProxySource


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_enabled_sources_once_disables_on_url_not_found(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create one enabled source that will 404
    async with SessionLocal() as session:
        session.add(
            ProxySource(
                user_id=1,
                url="https://raw.githubusercontent.com/example/repo/main/missing.txt",
                type="github_raw",
                name="example",
                enabled=True,
                validated=True,
                is_admin_source=True,
            )
        )
        await session.commit()

    # Patch GitHubGrabber.extract_proxies to simulate 404
    async def fake_extract_proxies(self, source):
        raise FileNotFoundError(f"URL not found: {source.url}")

    monkeypatch.setattr(
        "app.background_validator.GitHubGrabber.extract_proxies", fake_extract_proxies
    )

    from app.background_validator import scrape_enabled_sources_once

    async with SessionLocal() as session:
        await scrape_enabled_sources_once(session)

        row = (await session.execute(select(ProxySource))).scalars().one()
        assert row.enabled is False
        assert row.validated is False
        assert row.validation_error and "URL not found" in row.validation_error

    await engine.dispose()
