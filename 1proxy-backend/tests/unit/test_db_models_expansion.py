import pytest
from sqlalchemy import inspect
from app.db_models import UsageLog, ProxyPerformanceHistory, SourceTrustScore, Base


@pytest.mark.asyncio
async def test_usage_log_model_exists():
    """Test UsageLog model definition"""
    mapper = inspect(UsageLog)
    assert mapper.persist_selectable is not None
    columns = {c.key for c in mapper.columns}
    expected = {
        "id",
        "user_id",
        "action",
        "resource_type",
        "resource_id",
        "meta_data",
        "created_at",
    }
    assert expected.issubset(columns)


@pytest.mark.asyncio
async def test_performance_history_model_exists():
    """Test ProxyPerformanceHistory model definition"""
    mapper = inspect(ProxyPerformanceHistory)
    assert mapper.persist_selectable is not None
    columns = {c.key for c in mapper.columns}
    expected = {
        "id",
        "proxy_id",
        "validated_at",
        "latency_ms",
        "latency_p50",
        "latency_p95",
        "uptime_percent",
        "packet_loss",
        "jitter_ms",
        "success",
    }
    assert expected.issubset(columns)


@pytest.mark.asyncio
async def test_source_trust_score_model_exists():
    """Test SourceTrustScore model definition"""
    mapper = inspect(SourceTrustScore)
    assert mapper.persist_selectable is not None
    columns = {c.key for c in mapper.columns}
    expected = {"id", "source_id", "trust_score", "confidence", "updated_at"}
    assert expected.issubset(columns)
