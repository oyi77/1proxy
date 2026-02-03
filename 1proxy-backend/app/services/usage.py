from sqlalchemy.ext.asyncio import AsyncSession
from app.db_models import UsageLog


async def log_usage(
    session: AsyncSession,
    user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    """Log user activity to the database."""
    log_entry = UsageLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta_data=metadata,
    )
    session.add(log_entry)
    # We don't commit here to allow bundling with other transactions
    # or to let the caller handle the transaction scope.
