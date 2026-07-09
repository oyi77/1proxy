from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

from app.database import get_db
from app.dependencies import get_current_user, require_user, require_admin
from app.db_models import User, ProxySource
from app.models import SourceType
from app.models import SourceConfig
router = APIRouter(prefix="/api/v1", tags=["sources"])

# Access limiter from app state via request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


class SourceCreate(BaseModel):
    url: HttpUrl
    type: SourceType
    name: Optional[str] = None
    description: Optional[str] = None
    is_paid: bool = False


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    is_paid: Optional[bool] = None


class SourceResponse(BaseModel):
    id: int
    url: str
    type: str
    name: Optional[str]
    description: Optional[str]
    is_paid: bool
    enabled: bool
    validated: bool
    validation_error: Optional[str]
    total_scraped: int
    success_rate: float
    is_admin_source: bool
    is_owner: bool = False

    model_config = {"from_attributes": True}


class UserStats(BaseModel):
    total_sources: int
    active_sources: int
    total_proxies_contributed: int
    avg_success_rate: float


@router.get("/my-stats", response_model=UserStats)
@limiter.limit("60/minute")
async def get_my_stats(
    request: Request,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Get statistics for the current user's proxy sources.

    Returns counts and metrics for the authenticated user's contributed sources:
    - Total sources owned
    - Active (enabled) sources
    - Total proxies scraped from their sources
    - Average success rate across all their sources

    - **Authentication**: Required (any authenticated user)
    - **Rate limit**: 60 requests/minute
    - **Returns**: UserStats with counts and rates
    """
    result = await session.execute(
        select(ProxySource).where(ProxySource.user_id == current_user.id)
    )
    sources = result.scalars().all()

    total_sources = len(sources)
    active_sources = sum(1 for s in sources if s.enabled)
    total_proxies_contributed = sum(s.total_scraped for s in sources)

    avg_success_rate = 0.0
    if total_sources > 0:
        avg_success_rate = sum(s.success_rate for s in sources) / total_sources

    return UserStats(
        total_sources=total_sources,
        active_sources=active_sources,
        total_proxies_contributed=total_proxies_contributed,
        avg_success_rate=avg_success_rate,
    )


@router.get("/my-sources", response_model=List[SourceResponse])
@limiter.limit("60/minute")
async def get_my_sources(
    request: Request,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Get all proxy sources owned by the current user.

    Returns a list of all sources added by the authenticated user,
    including validation status, success rates, and scrape counts.

    - **Authentication**: Required (any authenticated user)
    - **Rate limit**: 60 requests/minute
    - **Returns**: List of SourceResponse objects
    """
    result = await session.execute(
        select(ProxySource).where(ProxySource.user_id == current_user.id)
    )
    sources = result.scalars().all()

    return [
        SourceResponse(**{**source.__dict__, "is_owner": True}) for source in sources
    ]


@router.post("/my-sources", response_model=dict, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def create_source(
    request: Request,
    source_data: SourceCreate,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Add a new proxy source.

    Submits a new proxy source URL for validation. The source is immediately
    validated (scraped for proxies) before being added. If validation
    fails, the source is not added.

    - **Authentication**: Required (any authenticated user)
    - **Rate limit**: 10 sources/hour
    - **Validation**: Source is tested by scraping for actual proxies
    - **Returns**: Source details with validation results and sample proxies

    Example body:
    ```json
    {
        "url": "https://raw.githubusercontent.com/example/proxies/main/list.txt",
        "type": "github_raw",
        "name": "My Proxy List",
        "description": "Daily updated proxy list"
    }
    ```
    """
    result = await session.execute(
        select(ProxySource).where(ProxySource.url == str(source_data.url))
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This source URL already exists in the database",
        )

    source_config = SourceConfig(
        url=source_data.url, type=source_data.type, enabled=True
    )

    validation_result: SourceValidationResult = await source_validator.validate_source(
        source_config
    )

    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Source validation failed",
                "reason": validation_result.error_message,
            },
        )

    new_source = ProxySource(
        user_id=current_user.id,
        url=str(source_data.url),
        type=source_data.type.value,
        name=source_data.name or str(source_data.url).split("/")[-1],
        description=source_data.description,
        is_paid=source_data.is_paid,
        enabled=True,
        validated=True,
        is_admin_source=False,
    )

    session.add(new_source)
    await session.commit()
    await session.refresh(new_source)

    return {
        "message": "Source created successfully",
        "source_id": new_source.id,
        "validation": {
            "proxy_count": validation_result.proxy_count,
            "sample_proxies": validation_result.sample_proxies,
        },
    }


@router.put("/my-sources/{source_id}", response_model=SourceResponse)
@limiter.limit("30/minute")
async def update_source(
    request: Request,
    source_id: int,
    update_data: SourceUpdate,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Update an existing proxy source.

    Modifies the name, description, enabled status, or paid status
    of a source owned by the current user. Admin-protected sources
    cannot be edited by non-admin users.

    - **Authentication**: Required (owner or admin)
    - **Rate limit**: 30 requests/minute
    - **Returns**: Updated SourceResponse
    """
    result = await session.execute(
        select(ProxySource).where(
            and_(ProxySource.id == source_id, ProxySource.user_id == current_user.id)
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found or you don't have permission to edit it",
        )

    if source.is_admin_source and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit admin-protected sources",
        )

    if update_data.name is not None:
        source.name = update_data.name
    if update_data.description is not None:
        source.description = update_data.description
    if update_data.enabled is not None:
        source.enabled = update_data.enabled
    if update_data.is_paid is not None:
        source.is_paid = update_data.is_paid

    await session.commit()
    await session.refresh(source)

    return SourceResponse(**{**source.__dict__, "is_owner": True})


@router.delete("/my-sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_source(
    request: Request,
    source_id: int,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Delete a proxy source.

    Permanently removes a source owned by the current user.
    Admin-protected sources can only be deleted by admin users.
    This operation cannot be undone.

    - **Authentication**: Required (owner or admin)
    - **Rate limit**: 30 requests/minute
    - **Returns**: 204 No Content on success
    """
    result = await session.execute(
        select(ProxySource).where(
            and_(ProxySource.id == source_id, ProxySource.user_id == current_user.id)
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found or you don't have permission to delete it",
        )

    if source.is_admin_source:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete admin-protected sources",
            )

    await session.delete(source)
    await session.commit()

    return None


@router.get("/admin/sources", response_model=dict)
@limiter.limit("30/minute")
async def admin_get_all_sources(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Admin: Get all proxy sources in the system.

    Returns a paginated list of ALL proxy sources from all users.
    Only accessible to admin users.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 30 requests/minute
    - **Returns**: Paginated list of all sources with owner info
    """
    from sqlalchemy import func

    total_result = await session.execute(select(func.count()).select_from(ProxySource))
    total = total_result.scalar() or 0

    result = await session.execute(
        select(ProxySource)
        .limit(limit)
        .offset(offset)
        .order_by(ProxySource.created_at.desc())
    )
    sources = result.scalars().all()

    return {
        "total": total,
        "count": len(sources),
        "offset": offset,
        "limit": limit,
        "sources": [
            SourceResponse(
                **{**source.__dict__, "is_owner": source.user_id == current_user.id}
            )
            for source in sources
        ],
    }


@router.post("/admin/sources/{source_id}/protect", response_model=SourceResponse)
async def admin_protect_source(
    source_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Admin: Protect a source from user deletion.

    Marks a source as admin-protected, preventing regular users
    from editing or deleting it. Useful for curated/official sources.

    - **Authentication**: Required (admin role)
    - **Returns**: Updated SourceResponse with is_admin_source=True
    """
    result = await session.execute(
        select(ProxySource).where(ProxySource.id == source_id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source not found"
        )

    source.is_admin_source = True
    await session.commit()
    await session.refresh(source)

    return SourceResponse(
        **{**source.__dict__, "is_owner": source.user_id == current_user.id}
    )
