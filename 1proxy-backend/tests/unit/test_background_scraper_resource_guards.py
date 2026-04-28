import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.db_models import ProxySource


class FakeProxy:
    def __init__(self, ip: str, port: int, protocol: str = "http"):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.country_code = None
        self.country_name = None
        self.city = None
        self.latency_ms = None
        self.speed_mbps = None
        self.anonymity = None
        self.proxy_type = None

    def model_dump(self):
        return {
            "ip": self.ip,
            "port": self.port,
            "protocol": self.protocol,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "city": self.city,
            "latency_ms": self.latency_ms,
            "speed_mbps": self.speed_mbps,
            "anonymity": self.anonymity,
            "proxy_type": self.proxy_type,
        }


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_enabled_sources_once_records_source_quality(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add(
            ProxySource(
                user_id=1,
                url="https://raw.githubusercontent.com/user/repo/main/proxies.txt",
                type="github_raw",
                name="healthy",
                enabled=True,
                validated=False,
                is_admin_source=True,
            )
        )
        await session.commit()

    async def fake_extract_proxies(self, source):
        return [FakeProxy("1.1.1.1", 80), FakeProxy("2.2.2.2", 8080)]

    monkeypatch.setattr(
        "app.background_validator.GitHubGrabber.extract_proxies", fake_extract_proxies
    )

    from app.background_validator import scrape_enabled_sources_once

    async with SessionLocal() as session:
        result = await scrape_enabled_sources_once(session)

        row = (await session.execute(select(ProxySource))).scalars().one()
        assert result["total_scraped"] == 2
        assert row.validated is True
        assert row.validation_error is None
        assert row.success_rate == 1.0
        assert row.total_scraped == 2

    await engine.dispose()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_enabled_sources_once_marks_empty_sources_unvalidated(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add(
            ProxySource(
                user_id=1,
                url="https://raw.githubusercontent.com/user/repo/main/empty.txt",
                type="github_raw",
                name="empty",
                enabled=True,
                validated=True,
                is_admin_source=True,
            )
        )
        await session.commit()

    async def fake_extract_proxies(self, source):
        return []

    monkeypatch.setattr(
        "app.background_validator.GitHubGrabber.extract_proxies", fake_extract_proxies
    )

    from app.background_validator import scrape_enabled_sources_once

    async with SessionLocal() as session:
        await scrape_enabled_sources_once(session)

        row = (await session.execute(select(ProxySource))).scalars().one()
        assert row.enabled is True
        assert row.validated is False
        assert row.validation_error == "No proxies extracted from source"
        assert row.success_rate == 0.0

    await engine.dispose()
