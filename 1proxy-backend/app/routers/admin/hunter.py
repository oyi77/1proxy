"""Admin hunter/candidate management endpoints — trigger hunt, list candidates, approve."""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.db_models import CandidateSource, ProxySource
from app.models.candidate import CandidateResponse
from app.dependencies import require_admin
from app.hunter.service import HunterService
from typing import List
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

hunter_router = APIRouter()


@hunter_router.post("/hunter/trigger")
@limiter.limit("5/minute")
async def trigger_hunt(request: Request, background_tasks: BackgroundTasks):
    """
    Manually trigger the Hunter Protocol to find new proxy sources.
    """
    service = HunterService()
    background_tasks.add_task(service.run_hunt)
    return {"status": "Hunter Protocol initiated", "message": "Check logs for progress"}


@hunter_router.get("/candidates", response_model=List[CandidateResponse])
@limiter.limit("30/minute")
async def list_candidates(
    request: Request,
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """
    List discovered candidate sources.
    """
    stmt = (
        select(CandidateSource)
        .where(CandidateSource.status == status)
        .order_by(CandidateSource.confidence_score.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@hunter_router.post("/candidates/{id}/approve")
@limiter.limit("10/minute")
async def approve_candidate(
    request: Request, id: int, session: AsyncSession = Depends(get_db)
):
    """
    Approve a candidate source and promote it to a real ProxySource.
    """
    # Get candidate
    stmt = select(CandidateSource).where(CandidateSource.id == id)
    result = await session.execute(stmt)
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if candidate.status == "approved":
        raise HTTPException(status_code=400, detail="Candidate already approved")

    # Check if URL already exists in sources (double check)
    stmt_source = select(ProxySource).where(ProxySource.url == candidate.url)
    result_source = await session.execute(stmt_source)
    if result_source.scalar_one_or_none():
        # Just mark as approved/duplicate
        candidate.status = "approved"
        await session.commit()
        return {"status": "merged", "message": "Source already existed"}

    # Create new ProxySource
    # We assume it's a public list found on the web
    new_source = ProxySource(
        url=candidate.url,
        type="public",  # or "url" depending on your convention
        name=f"Hunter: {candidate.domain}",
        description=f"Auto-discovered via {candidate.discovery_method}",
        enabled=True,
        is_admin_source=True,
    )
    session.add(new_source)

    # Update candidate status
    candidate.status = "approved"

    await session.commit()

    return {"status": "approved", "source_id": new_source.id}
