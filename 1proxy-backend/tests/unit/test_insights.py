import pytest
from unittest.mock import MagicMock, AsyncMock
from app.db_models import ValidationHistory
from app.services.insights import (
    calculate_stability_score,
    calculate_source_trust,
    detect_geo_anomalies,
)


@pytest.mark.asyncio
async def test_calculate_stability_score():
    """Test stability score calculation."""
    mock_session = AsyncMock()

    # Mock result for execute().scalars().all()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        ValidationHistory(success=True),
        ValidationHistory(success=True),
        ValidationHistory(success=False),
        ValidationHistory(success=True),
    ]
    mock_session.execute.return_value = mock_result

    score = await calculate_stability_score(mock_session, 1)
    assert score == 75  # 3/4 success


@pytest.mark.asyncio
async def test_calculate_source_trust():
    """Test source trust score."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 80.0
    mock_session.execute.return_value = mock_result

    score = await calculate_source_trust(mock_session, 1)
    assert score == 80


@pytest.mark.asyncio
async def test_detect_geo_anomalies():
    """Test anomaly detection."""
    mock_session = AsyncMock()
    # Currently a placeholder returning empty list
    anomalies = await detect_geo_anomalies(mock_session)
    assert isinstance(anomalies, list)
