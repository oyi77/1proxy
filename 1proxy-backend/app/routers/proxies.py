from fastapi import APIRouter, Depends, Query, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address
import aiohttp
import asyncio
import time

from app.database import get_db
from app.db_storage import db_storage
from app.dependencies import require_admin

# Rate limiter for this router
limiter = Limiter(key_func=get_remote_address)

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
@limiter.limit("100/hour")  # Rate limit: 100 exports per hour
async def export_proxies(
    request: Request,
    format: str = Query("txt", description="Export format: txt, json, csv, pac"),
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

    elif format == "pac":
        # Generate PAC (Proxy Auto-Config) file for browser configuration
        # Filter to HTTP/HTTPS proxies only (PAC doesn't support other protocols)
        http_proxies = [p for p in proxies if p.protocol.lower() in ["http", "https"]]

        if not http_proxies:
            proxy_list = "DIRECT"
        else:
            # Build proxy list (round-robin load balancing)
            proxy_list = "; ".join(
                [
                    f"PROXY {p.ip}:{p.port}"
                    for p in http_proxies[:10]  # Limit to top 10 for performance
                ]
            )
            proxy_list += "; DIRECT"

        pac_content = f"""function FindProxyForURL(url, host) {{
    // 1proxy PAC File - Auto-generated proxy configuration
    // Generated: {datetime.utcnow().isoformat()}
    // Total proxies: {len(http_proxies)}
    
    // Bypass localhost and private networks
    if (isPlainHostName(host) ||
        shExpMatch(host, "*.local") ||
        isInNet(host, "10.0.0.0", "255.0.0.0") ||
        isInNet(host, "172.16.0.0", "255.240.0.0") ||
        isInNet(host, "192.168.0.0", "255.255.0.0") ||
        isInNet(host, "127.0.0.0", "255.0.0.0")) {{
        return "DIRECT";
    }}
    
    // Use proxy for all other requests (round-robin)
    return "{proxy_list}";
}}"""

        return PlainTextResponse(
            content=pac_content,
            media_type="application/x-ns-proxy-autoconfig",
            headers={"Content-Disposition": "attachment; filename=1proxy.pac"},
        )

    return {"error": "Invalid format. Supported: txt, json, csv, pac"}


@router.get("/proxies/random", response_model=ProxyResponse)
async def get_random_proxy(
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    country_code: Optional[str] = Query(None, description="Filter by country code"),
    min_quality: Optional[int] = Query(None, description="Minimum quality score"),
    anonymity: Optional[str] = Query(
        None, description="Filter by anonymity (transparent, anonymous, elite)"
    ),
    max_latency: Optional[int] = Query(None, description="Maximum latency in ms"),
    exclude: Optional[str] = Query(
        None,
        description="Comma-separated list of IPs to exclude (e.g., '1.2.3.4,5.6.7.8')",
    ),
    session: AsyncSession = Depends(get_db),
):
    """
    Get a random high-quality proxy with smart filtering.

    Use the 'exclude' parameter to implement rotation by excluding
    previously used IPs. This ensures you get different proxies
    on each request.

    Example: /proxies/random?min_quality=70&exclude=192.168.1.1,10.0.0.1
    """

    # Parse exclude list
    excluded_ips = set()
    if exclude:
        excluded_ips = set(ip.strip() for ip in exclude.split(",") if ip.strip())

    proxy = await db_storage.get_random_proxy(
        session=session,
        protocol=protocol,
        country_code=country_code,
        min_quality=min_quality,
        anonymity=anonymity,
        max_latency=max_latency,
    )

    # If proxy is in exclude list, try to get another one
    max_attempts = 5
    attempts = 0
    while proxy and proxy.ip in excluded_ips and attempts < max_attempts:
        proxy = await db_storage.get_random_proxy(
            session=session,
            protocol=protocol,
            country_code=country_code,
            min_quality=min_quality,
            anonymity=anonymity,
            max_latency=max_latency,
        )
        attempts += 1

    if not proxy:
        raise HTTPException(status_code=404, detail="No matching proxies found")

    if proxy.ip in excluded_ips:
        raise HTTPException(
            status_code=404,
            detail="No proxies available that are not in the exclude list",
        )

    return ProxyResponse(
        **{
            **proxy.__dict__,
            "last_validated": proxy.last_validated.isoformat()
            if proxy.last_validated
            else None,
        }
    )


class ProxyTestRequest(BaseModel):
    proxy_url: str
    target_url: str = "https://www.google.com"
    timeout: int = 5


class ProxyTestResponse(BaseModel):
    proxy_url: str
    target_url: str
    working: bool
    latency_ms: Optional[int]
    status_code: Optional[int]
    error: Optional[str]
    tested_at: str


@router.post("/proxies/test", response_model=ProxyTestResponse)
@limiter.limit("10/minute")  # Rate limit: 10 tests per minute to prevent abuse
async def test_proxy(request: Request, test_request: ProxyTestRequest):
    """
    Test if a proxy works by making a request through it.

    This endpoint is rate-limited to prevent abuse.
    Free tier: 10 tests per minute.
    """
    tested_at = datetime.utcnow().isoformat()

    try:
        # Parse proxy URL
        if not test_request.proxy_url.startswith(("http://", "https://", "socks5://")):
            raise HTTPException(
                status_code=400,
                detail="Invalid proxy URL. Must start with http://, https://, or socks5://",
            )

        start_time = time.time()

        # Create aiohttp session with proxy
        timeout_config = aiohttp.ClientTimeout(total=test_request.timeout)

        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            try:
                async with session.get(
                    test_request.target_url,
                    proxy=test_request.proxy_url,
                    ssl=False,  # Skip SSL verification for testing
                ) as response:
                    latency_ms = int((time.time() - start_time) * 1000)

                    return ProxyTestResponse(
                        proxy_url=test_request.proxy_url,
                        target_url=test_request.target_url,
                        working=True,
                        latency_ms=latency_ms,
                        status_code=response.status,
                        error=None,
                        tested_at=tested_at,
                    )
            except aiohttp.ClientError as e:
                return ProxyTestResponse(
                    proxy_url=test_request.proxy_url,
                    target_url=test_request.target_url,
                    working=False,
                    latency_ms=None,
                    status_code=None,
                    error=f"Connection error: {str(e)}",
                    tested_at=tested_at,
                )

    except asyncio.TimeoutError:
        return ProxyTestResponse(
            proxy_url=test_request.proxy_url,
            target_url=test_request.target_url,
            working=False,
            latency_ms=None,
            status_code=None,
            error="Connection timeout",
            tested_at=tested_at,
        )


@router.delete("/proxies/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_proxy(
    request: Request,
    proxy_id: int,
    session: AsyncSession = Depends(get_db),
    admin_user=Depends(require_admin),
):
    success = await db_storage.delete_proxy(session, proxy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return None
