import pytest
import asyncio
import base64
import os

# Ensure data directory exists for SQLite BEFORE any app imports
if not os.path.exists("./data"):
    os.makedirs("./data", exist_ok=True)

from typing import List
from app.models.proxy import Proxy, ValidationResult
from app.models.source import SourceConfig, SourceType
from app.database import engine, Base
from app.db_models import UsageLog, ProxyPerformanceHistory, SourceTrustScore
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test database tables before running integration tests."""
    import asyncio
    from app.database import engine, Base
    
    async def create_tables():
        async with engine.begin() as conn:
            # Drop all tables and recreate to ensure schema is up to date
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    
    asyncio.run(create_tables())
    yield
    # Cleanup
    asyncio.run(engine.dispose())

@pytest.fixture
def mock_prometheus(monkeypatch):
    """Mock Prometheus client to prevent actual registry registration."""
    mock_registry = MagicMock()
    mock_counter = MagicMock()
    mock_histogram = MagicMock()
    mock_gauge = MagicMock()

    # Setup mock methods
    mock_counter.labels.return_value = mock_counter
    mock_histogram.labels.return_value = mock_histogram
    mock_gauge.labels.return_value = mock_gauge

    # Mock classes
    monkeypatch.setattr(
        "prometheus_client.Counter", MagicMock(return_value=mock_counter)
    )
    monkeypatch.setattr(
        "prometheus_client.Histogram", MagicMock(return_value=mock_histogram)
    )
    monkeypatch.setattr("prometheus_client.Gauge", MagicMock(return_value=mock_gauge))
    monkeypatch.setattr("prometheus_client.start_http_server", MagicMock())

    return {"counter": mock_counter, "histogram": mock_histogram, "gauge": mock_gauge}


@pytest.fixture
def sample_usage_log(sample_http_proxy) -> UsageLog:
    return UsageLog(
        user_id=1,
        action="copy_proxy",
        resource_type="proxy",
        resource_id=sample_http_proxy.id,
        meta_data={"protocol": "http"},
    )


@pytest.fixture
def sample_performance_history(sample_http_proxy) -> ProxyPerformanceHistory:
    return ProxyPerformanceHistory(
        proxy_id=sample_http_proxy.id,
        latency_ms=100.0,
        latency_p50=95.0,
        latency_p95=120.0,
        uptime_percent=99.9,
        success=True,
    )
