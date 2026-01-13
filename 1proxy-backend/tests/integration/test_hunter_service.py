import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.hunter.service import HunterService
from app.db_models import CandidateSource


@pytest.mark.asyncio
async def test_hunter_service_run():
    # Mock strategies
    mock_strat_1 = MagicMock()
    mock_strat_1.name = "mock1"
    mock_strat_1.discover = AsyncMock(return_value=["http://new.com/list.txt"])

    mock_strat_2 = MagicMock()
    mock_strat_2.name = "mock2"
    mock_strat_2.discover = AsyncMock(return_value=[])

    service = HunterService()
    service.strategies = [mock_strat_1, mock_strat_2]

    # Mock DB session and get_db
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Mock extractors/fetchers to avoid network
    service._fetch_content = AsyncMock(return_value="1.1.1.1:80")
    service._calculate_confidence = MagicMock(return_value=50)

    # Mock UniversalExtractor to ensure isolation
    with patch("app.hunter.service.UniversalExtractor") as mock_extractor:
        mock_extractor.extract_proxies.return_value = [
            MagicMock(protocol="http", ip="1.1.1.1", port=80)
        ]

        with patch("app.hunter.service.get_db") as mock_get_db:

            async def async_gen():
                yield mock_session

            mock_get_db.return_value = async_gen()

            await service.run_hunt()

            # Verify strategies called
            mock_strat_1.discover.assert_called_once()
            mock_strat_2.discover.assert_called_once()

            # Verify DB add called
            if not mock_session.add.called:
                # Debugging: check if execute was called
                print(f"Execute called count: {mock_session.execute.call_count}")

            assert mock_session.add.called
            args = mock_session.add.call_args[0]
            candidate = args[0]
            assert isinstance(candidate, CandidateSource)
            assert candidate.url == "http://new.com/list.txt"
            assert candidate.confidence_score == 50
            assert candidate.status == "pending"
