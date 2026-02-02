import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Response, Request
from app.routers.auth import github_callback, google_callback
from app.db_models import User


@pytest.mark.asyncio
async def test_github_callback_logs_usage():
    """Test that github_callback logs usage."""
    # Setup mocks
    mock_request = MagicMock(spec=Request)
    mock_response = MagicMock(spec=Response)
    mock_session = AsyncMock()

    mock_user = User(id=123, email="test@example.com", username="testuser")
    mock_token = "test_token"

    # Mock dependencies
    with patch(
        "app.routers.auth.oauth_handler.github_callback", new_callable=AsyncMock
    ) as mock_oauth:
        mock_oauth.return_value = (mock_user, mock_token)

        # We need to mock log_usage where it is used in the router
        # Since it's not imported yet, this test expects the import to be added to routers/auth.py
        with patch("app.routers.auth.log_usage", new_callable=AsyncMock) as mock_log:
            # Execute
            await github_callback(
                request=mock_request,
                code="test_code",
                response=mock_response,
                session=mock_session,
            )

            # Verify log_usage called
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args.kwargs["user_id"] == 123
            assert call_args.kwargs["action"] == "login"
            assert call_args.kwargs["resource_type"] == "github"


@pytest.mark.asyncio
async def test_google_callback_logs_usage():
    """Test that google_callback logs usage."""
    # Setup mocks
    mock_request = MagicMock(spec=Request)
    mock_response = MagicMock(spec=Response)
    mock_session = AsyncMock()

    mock_user = User(id=456, email="google@example.com", username="googleuser")
    mock_token = "google_token"

    with patch(
        "app.routers.auth.oauth_handler.google_callback", new_callable=AsyncMock
    ) as mock_oauth:
        mock_oauth.return_value = (mock_user, mock_token)

        with patch("app.routers.auth.log_usage", new_callable=AsyncMock) as mock_log:
            await google_callback(
                request=mock_request,
                code="test_code",
                response=mock_response,
                session=mock_session,
            )

            mock_log.assert_called_once()
            assert mock_log.call_args.kwargs["user_id"] == 456
            assert mock_log.call_args.kwargs["action"] == "login"
            assert mock_log.call_args.kwargs["resource_type"] == "google"
