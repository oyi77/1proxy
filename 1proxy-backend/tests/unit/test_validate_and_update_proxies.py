import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.db_models import Proxy
from app.db_storage import DatabaseStorage
from app.validator import ValidationResult


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_and_update_proxies_updates_entire_batch(monkeypatch):
    """Regression: validating a batch must update every proxy.

    Production symptom when broken:
      log shows e.g. "Validated 0 proxies, ❌ 1 failed (20 total)" repeatedly.
    That indicates we validated N proxies but only updated 1 row, leaving the rest
    stuck as pending and revalidated forever.
    """

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db = DatabaseStorage(enable_validation=False)

    async def fake_validate_batch(proxies):
        # proxies: List[tuple[url, ip]]
        return [
            (
                "http://1.1.1.1:80",
                ValidationResult(
                    success=True,
                    latency_ms=123,
                    anonymity="elite",
                    can_access_google=True,
                    country_code="US",
                    country_name="United States",
                    proxy_type="residential",
                    isp="TestISP",
                    org="TestOrg",
                    quality_score=95,
                ),
            ),
            (
                "http://2.2.2.2:80",
                ValidationResult(success=False, error_message="boom"),
            ),
            (
                "http://3.3.3.3:80",
                ValidationResult(success=True, latency_ms=456, quality_score=50),
            ),
        ]

    # Patch the module-level optimized_validator used by DatabaseStorage
    monkeypatch.setattr(
        "app.db_storage.optimized_validator.validate_batch", fake_validate_batch
    )

    async with SessionLocal() as session:
        session.add_all(
            [
                Proxy(
                    url="http://1.1.1.1:80",
                    protocol="http",
                    ip="1.1.1.1",
                    port=80,
                    validation_status="pending",
                    is_working=False,
                ),
                Proxy(
                    url="http://2.2.2.2:80",
                    protocol="http",
                    ip="2.2.2.2",
                    port=80,
                    validation_status="pending",
                    is_working=False,
                ),
                Proxy(
                    url="http://3.3.3.3:80",
                    protocol="http",
                    ip="3.3.3.3",
                    port=80,
                    validation_status="pending",
                    is_working=False,
                ),
            ]
        )
        await session.commit()

        result = await db.validate_and_update_proxies(session, limit=50)
        assert result["total"] == 3
        assert result["validated"] + result["failed"] == result["total"]

        rows = (
            (await session.execute(select(Proxy).order_by(Proxy.url))).scalars().all()
        )
        statuses = {p.url: p.validation_status for p in rows}
        assert statuses == {
            "http://1.1.1.1:80": "validated",
            "http://2.2.2.2:80": "failed",
            "http://3.3.3.3:80": "validated",
        }

    await engine.dispose()
