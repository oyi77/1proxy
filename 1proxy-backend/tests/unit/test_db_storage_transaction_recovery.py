import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.db_models import Proxy
from app.db_storage import DatabaseStorage


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_proxies_recovers_after_per_item_db_error():
    """Regression: one bad row must not poison the whole transaction.

    Postgres symptom in production:
      asyncpg.exceptions.InFailedSQLTransactionError: current transaction is aborted

    DB-agnostic reproduction:
      A NOT NULL violation during autoflush marks the SQLAlchemy session as needing
      rollback; subsequent statements fail unless we isolate/rollback correctly.
    """

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db = DatabaseStorage(enable_validation=False)

    async with SessionLocal() as session:
        proxies_data = [
            {
                "url": "http://1.1.1.1:80",
                "ip": "1.1.1.1",
                "port": 80,
                # NOT NULL violation for Proxy.protocol
                "protocol": None,
            },
            {
                "url": "http://2.2.2.2:80",
                "ip": "2.2.2.2",
                "port": 80,
                "protocol": "http",
            },
        ]

        processed = await db.add_proxies(session, proxies_data)
        assert processed == 2

        result = await session.execute(select(Proxy).order_by(Proxy.url))
        rows = result.scalars().all()

        assert [p.url for p in rows] == ["http://2.2.2.2:80"]

    await engine.dispose()
