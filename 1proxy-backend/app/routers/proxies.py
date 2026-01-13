from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.db_storage import db_storage

router = APIRouter(prefix="/api/v1", tags=["proxies"])


class ProxyResponse(BaseModel):
    id: int
    url: str
    protocol: str
    ip: Optional[str]
    port: Optional[int]
    country_code: Optional[str]
    country_name: Optional[str]
    state: Optional[str]
    city: Optional[str]
    latency_ms: Optional[int]
    speed_mbps: Optional[float]
    anonymity: Optional[str]
    proxy_type: Optional[str]
    can_access_google: Optional[bool]
    quality_score: Optional[int]
    is_working: bool
    last_validated: Optional[str]

    class Config:
        from_attributes = True


class ProxiesListResponse(BaseModel):
    total: int
    count: int
    offset: int
    limit: int
    proxies: List[ProxyResponse]


@router.get("/proxies/advanced", response_model=ProxiesListResponse)
async def get_proxies_advanced(
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    country_code: Optional[str] = Query(
        None, description="Filter by country code (e.g., US, GB)"
    ),
    anonymity: Optional[str] = Query(
        None, description="Filter by anonymity level (transparent, anonymous, elite)"
    ),
    proxy_type: Optional[str] = Query(
        None, description="Filter by type (datacenter, residential, mobile)"
    ),
    can_access_google: Optional[bool] = Query(
        None, description="Filter by Google accessibility"
    ),
    min_quality: Optional[int] = Query(
        None, ge=0, le=100, description="Minimum quality score (0-100)"
    ),
    min_speed: Optional[float] = Query(None, ge=0, description="Minimum speed in Mbps"),
    max_latency: Optional[int] = Query(None, ge=0, description="Maximum latency in ms"),
    is_working: bool = Query(True, description="Show only working proxies"),
    order_by: str = Query(
        "quality_score",
        description="Sort by: quality_score, latency_ms, speed_mbps, created_at",
    ),
    order_direction: str = Query("desc", description="Sort direction: asc or desc"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db),
):
    proxies, total = await db_storage.get_proxies(
        session=session,
        protocol=protocol,
        country_code=country_code,
        anonymity=anonymity,
        min_quality=min_quality,
        is_working=is_working,
        limit=limit,
        offset=offset,
        order_by=order_by,
    )

    filtered_proxies = []
    for proxy in proxies:
        if proxy_type and proxy.proxy_type != proxy_type:
            continue
        if (
            can_access_google is not None
            and proxy.can_access_google != can_access_google
        ):
            continue
        if min_speed is not None and (
            proxy.speed_mbps is None or proxy.speed_mbps < min_speed
        ):
            continue
        if max_latency is not None and (
            proxy.latency_ms is None or proxy.latency_ms > max_latency
        ):
            continue

        filtered_proxies.append(proxy)

    return ProxiesListResponse(
        total=total,
        count=len(filtered_proxies),
        offset=offset,
        limit=limit,
        proxies=[
            ProxyResponse(
                **{
                    **proxy.__dict__,
                    "last_validated": proxy.last_validated.isoformat()
                    if proxy.last_validated
                    else None,
                }
            )
            for proxy in filtered_proxies
        ],
    )


@router.get("/proxies/filters/options")
async def get_filter_options(session: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func, distinct
    from app.db_models import Proxy

    protocols_result = await session.execute(
        select(distinct(Proxy.protocol)).where(Proxy.is_working == True)
    )
    protocols = [p for p in protocols_result.scalars().all() if p]

    countries_result = await session.execute(
        select(
            Proxy.country_code, Proxy.country_name, func.count(Proxy.id).label("count")
        )
        .where(Proxy.is_working == True, Proxy.country_code.isnot(None))
        .group_by(Proxy.country_code, Proxy.country_name)
        .order_by(func.count(Proxy.id).desc())
        .limit(50)
    )
    countries = [
        {"code": row.country_code, "name": row.country_name, "count": row.count}
        for row in countries_result.all()
    ]

    anonymity_levels = ["transparent", "anonymous", "elite"]
    proxy_types = ["datacenter", "residential", "mobile", "unknown"]

    quality_ranges = [
        {"label": "Excellent (80-100)", "min": 80, "max": 100},
        {"label": "Good (60-79)", "min": 60, "max": 79},
        {"label": "Fair (40-59)", "min": 40, "max": 59},
        {"label": "Poor (0-39)", "min": 0, "max": 39},
    ]

    return {
        "protocols": protocols,
        "countries": countries,
        "anonymity_levels": anonymity_levels,
        "proxy_types": proxy_types,
        "quality_ranges": quality_ranges,
        "sort_options": [
            {"value": "quality_score", "label": "Quality Score"},
            {"value": "latency_ms", "label": "Latency (fastest first)"},
            {"value": "speed_mbps", "label": "Speed (fastest first)"},
            {"value": "created_at", "label": "Recently Added"},
        ],
    }


@router.get("/proxies/export")
async def export_proxies(
    format: str = Query("txt", description="Export format: txt, json, csv"),
    protocol: Optional[str] = None,
    country_code: Optional[str] = None,
    min_quality: Optional[int] = None,
    limit: int = Query(1000, ge=1, le=10000),
    session: AsyncSession = Depends(get_db),
):
    from fastapi.responses import PlainTextResponse, StreamingResponse
    import json
    import io

    proxies, _ = await db_storage.get_proxies(
        session=session,
        protocol=protocol,
        country_code=country_code,
        min_quality=min_quality,
        is_working=True,
        limit=limit,
        offset=0,
        order_by="quality_score",
    )

    if format == "txt":
        content = "\n".join([proxy.url for proxy in proxies])
        return PlainTextResponse(content=content, media_type="text/plain")

    elif format == "json":
        data = [
            {
                "url": proxy.url,
                "protocol": proxy.protocol,
                "country": proxy.country_code,
                "latency_ms": proxy.latency_ms,
                "anonymity": proxy.anonymity,
                "quality_score": proxy.quality_score,
            }
            for proxy in proxies
        ]
        return PlainTextResponse(
            content=json.dumps(data, indent=2), media_type="application/json"
        )

    elif format == "csv":
        import csv

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["URL", "Protocol", "Country", "Latency(ms)", "Anonymity", "Quality"]
        )

        for proxy in proxies:
            writer.writerow(
                [
                    proxy.url,
                    proxy.protocol,
                    proxy.country_code or "",
                    proxy.latency_ms or "",
                    proxy.anonymity or "",
                    proxy.quality_score or "",
                ]
            )

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=proxies.csv"},
        )

    return {"error": "Invalid format"}


@router.get("/proxies/random", response_model=ProxyResponse)
async def get_random_proxy(
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    country_code: Optional[str] = Query(None, description="Filter by country code"),
    min_quality: Optional[int] = Query(None, description="Minimum quality score"),
    anonymity: Optional[str] = Query(
        None, description="Filter by anonymity (transparent, anonymous, elite)"
    ),
    max_latency: Optional[int] = Query(None, description="Maximum latency in ms"),
    session: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException

    proxy = await db_storage.get_random_proxy(
        session=session,
        protocol=protocol,
        country_code=country_code,
        min_quality=min_quality,
        anonymity=anonymity,
        max_latency=max_latency,
    )

    if not proxy:
        raise HTTPException(status_code=404, detail="No matching proxies found")

    return ProxyResponse(
        **{
            **proxy.__dict__,
            "last_validated": proxy.last_validated.isoformat()
            if proxy.last_validated
            else None,
        }
    )
