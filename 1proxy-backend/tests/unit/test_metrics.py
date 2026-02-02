import pytest
from unittest.mock import MagicMock

# Import that should fail initially
from app.metrics import ProxyMetrics


def test_metrics_singleton_initialization():
    """Test ProxyMetrics singleton pattern."""
    metrics = ProxyMetrics()
    assert metrics.requests_total is not None
    assert metrics.latency_histogram is not None
