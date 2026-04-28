import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ping_database_once_returns_true_for_active_engine():
    from app.database import ping_database_once

    assert await ping_database_once() is True
