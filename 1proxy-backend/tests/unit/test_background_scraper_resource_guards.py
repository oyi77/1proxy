import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.db_models import ProxySource


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_enabled_sources_once_skips_generic_text_sources(monkeypatch):
    """Regression: background scraper must not run heavy HTML scraping.

    On memory-constrained platforms (Railway), scraping GitHub repo HTML pages can
    OOM the container. We skip GENERIC_TEXT sources in the background worker.
    """

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add(
            ProxySource(
                user_id=1,
                url="https://github.com/example/repo",
                type="generic_text",
                name="example",
                enabled=True,
                validated=True,
                is_admin_source=True,
            )
        )
        await session.commit()

    async def boom(self, source):
        raise AssertionError("WebGrabber.extract_proxies should not be called")

    monkeypatch.setattr("app.background_validator.WebGrabber.extract_proxies", boom)

    from app.background_validator import scrape_enabled_sources_once

    async with SessionLocal() as session:
        # Should not raise
        await scrape_enabled_sources_once(session)

        row = (await session.execute(select(ProxySource))).scalars().one()
        assert row.enabled is True

    await engine.dispose()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_enabled_sources_once_disables_source_when_too_large(monkeypatch):
    """Regression: oversized sources must be disabled to avoid repeated OOM risk."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add(
            ProxySource(
                user_id=1,
                url="https://raw.githubusercontent.com/user/repo/main/big.txt",
                type="github_raw",
                name="big",
                enabled=True,
                validated=True,
                is_admin_source=True,
            )
        )
        await session.commit()

    async def boom(self, source):
        raise ValueError("Source content too large (> 10 bytes)")

    monkeypatch.setattr("app.background_validator.GitHubGrabber.extract_proxies", boom)

    from app.background_validator import scrape_enabled_sources_once

    async with SessionLocal() as session:
        await scrape_enabled_sources_once(session)

        row = (await session.execute(select(ProxySource))).scalars().one()
        assert row.enabled is False
        assert row.validated is False
        assert row.validation_error and "too large" in row.validation_error

    await engine.dispose()
