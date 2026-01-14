from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

from app.database import get_db
from app.dependencies import get_current_user, require_user, require_admin
from app.db_models import User, ProxySource
from app.models import SourceType
from app.source_validator import source_validator, SourceValidationResult
from app.models import SourceConfig

router = APIRouter(prefix="/api/v1", tags=["sources"])


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

    class Config:
        from_attributes = True


class UserStats(BaseModel):
    total_sources: int
    active_sources: int
    total_proxies_contributed: int
    avg_success_rate: float


@router.get("/my-stats", response_model=UserStats)
async def get_my_stats(
    current_user: User = Depends(require_user), session: AsyncSession = Depends(get_db)
):
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
async def get_my_sources(
    current_user: User = Depends(require_user), session: AsyncSession = Depends(get_db)
):
    result = await session.execute(
        select(ProxySource).where(ProxySource.user_id == current_user.id)
    )
    sources = result.scalars().all()

    return [
        SourceResponse(**{**source.__dict__, "is_owner": True}) for source in sources
    ]


@router.post("/my-sources", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_source(
    source_data: SourceCreate,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
):
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
async def update_source(
    source_id: int,
    update_data: SourceUpdate,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
):
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
async def delete_source(
    source_id: int,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_db),
):
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


@router.get("/admin/sources", response_model=List[SourceResponse])
async def admin_get_all_sources(
    current_user: User = Depends(require_admin), session: AsyncSession = Depends(get_db)
):
    result = await session.execute(select(ProxySource))
    sources = result.scalars().all()

    return [
        SourceResponse(
            **{**source.__dict__, "is_owner": source.user_id == current_user.id}
        )
        for source in sources
    ]


@router.post("/admin/sources/{source_id}/protect", response_model=SourceResponse)
async def admin_protect_source(
    source_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
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
