"""Admin cleanup operations — purge failed, unseen, stale, cap enforcement, tier recalculation."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.db_storage import db_storage
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

cleanup_router = APIRouter()


@cleanup_router.post("/cleanup/purge-failed", summary="Purge 3-strike failed proxies")
async def purge_failed_proxies(
    admin_user=Depends(require_admin), session: AsyncSession = Depends(get_db)
):
    count = await db_storage.purge_3strike_proxies(session)
    return {"deleted": count, "message": f"Purged {count} failed proxies (3+ strikes)"}


@cleanup_router.post("/cleanup/purge-unseen", summary="Purge proxies not seen in N days")
async def purge_unseen_proxies(
    days: int = Query(14, ge=1, le=90, description="Delete proxies not seen in N days"),
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    count = await db_storage.purge_unseen_proxies(session, days=days)
    return {"deleted": count, "days": days, "message": f"Purged {count} proxies not seen in {days} days"}


@cleanup_router.post("/cleanup/purge-stale-pending", summary="Purge old pending proxies")
async def purge_stale_pending_proxies(
    days: int = Query(7, ge=1, le=30, description="Delete pending proxies older than N days"),
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    count = await db_storage.purge_stale_pending(session, days=days)
    return {"deleted": count, "days": days, "message": f"Purged {count} stale pending proxies"}


@cleanup_router.post("/cleanup/enforce-cap", summary="Enforce database proxy cap")
async def enforce_db_cap(
    soft_cap: int = Query(50000, ge=10000, le=200000, description="Soft cap threshold"),
    hard_cap: int = Query(75000, ge=20000, le=300000, description="Hard cap threshold"),
    admin_user=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    count = await db_storage.enforce_db_cap(session, soft_cap=soft_cap, hard_cap=hard_cap)
    return {"deleted": count, "soft_cap": soft_cap, "hard_cap": hard_cap}


@cleanup_router.post("/cleanup/recalc-tiers", summary="Recalculate priority tiers")
async def recalc_priority_tiers(
    admin_user=Depends(require_admin), session: AsyncSession = Depends(get_db)
):
    count = await db_storage.update_priority_tiers(session)
    return {"updated": count, "message": f"Updated priority tiers for {count} proxies"}
