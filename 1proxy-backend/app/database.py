import asyncio
import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/1proxy.db")

# Ensure asynchronous driver is used for PostgreSQL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Auto-create data directory for SQLite if it doesn't exist
if "sqlite" in DATABASE_URL and "./data/" in DATABASE_URL:
    os.makedirs("./data", exist_ok=True)

# Configure connection pooling for production performance
engine_kwargs = {
    "echo": False,
    "future": True,
}

# SQLite doesn't support connection pooling, only add pool settings for PostgreSQL
if DATABASE_URL.startswith("postgresql"):
    engine_kwargs.update(
        {
            "pool_size": 20,  # Number of permanent connections
            "max_overflow": 30,  # Additional connections beyond pool_size
            "pool_pre_ping": True,  # Verify connections before using
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "pool_timeout": 30,  # Wait max 30s for connection from pool
            "connect_args": {
                "statement_cache_size": 0  # Disable prepared statements for PgBouncer compatibility
            },
        }
    )

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ping_database_once() -> bool:
    """Run a lightweight database ping and return whether it succeeded."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database keepalive ping failed: %s", exc)
        return False


async def database_keepalive_worker(interval_seconds: int = 300):
    """Periodically touch the database so idle deployments stay warm."""
    logger.info("🔄 Database keepalive worker started")

    while True:
        await ping_database_once()
        await asyncio.sleep(interval_seconds)


async def dispose_database():
    """Close pooled async DB connections during application shutdown."""
    await engine.dispose()
