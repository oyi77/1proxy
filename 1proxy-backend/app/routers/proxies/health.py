from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from sqlalchemy import text

from app.database import get_db
from app.routers.proxies._router import router


@router.get("/health", tags=["health"], summary="Health check")
async def health_check(session: AsyncSession = Depends(get_db)):
    """
    Health check endpoint for monitoring.

    Returns service status and database connectivity.
    """
    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "service": "1proxy",
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "db_status": db_status,
    }
