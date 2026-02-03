import pytest
from unittest.mock import AsyncMock, MagicMock
from app.db_models import UsageLog

# Import that should fail initially
from app.services.usage import log_usage


@pytest.mark.asyncio
async def test_log_usage_creates_record():
    """Test that log_usage creates a DB entry."""
    # Setup
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    # Execute
    await log_usage(
        session=mock_session,
        user_id=1,
        action="test_action",
        resource_type="proxy",
        resource_id=123,
        metadata={"foo": "bar"},
    )

    # Verify
    mock_session.add.assert_called_once()
    call_args = mock_session.add.call_args[0][0]
    assert isinstance(call_args, UsageLog)
    assert call_args.user_id == 1
    assert call_args.action == "test_action"
    assert call_args.meta_data == {"foo": "bar"}
