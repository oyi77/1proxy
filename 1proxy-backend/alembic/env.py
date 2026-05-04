from logging.config import fileConfig
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import Base, DATABASE_URL
from app.db_models import User, ProxySource, Proxy, ValidationHistory


def get_url():
    url = DATABASE_URL
    # Override if using async driver for Alembic (which is sync)
    if "postgresql+asyncpg" in url:
        url = url.replace("postgresql+asyncpg", "postgresql")
    if "sqlite+aiosqlite" in url:
        url = url.replace("sqlite+aiosqlite", "sqlite")
    return url


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()
    if url.startswith("postgresql") and "sslmode" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
