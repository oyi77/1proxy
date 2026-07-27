from fastapi import APIRouter, Depends, Query, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, computed_field
from datetime import datetime, timezone
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
    validation_status: Optional[str]
    last_validated: Optional[str]

    @computed_field
    @property
    def last_seen_hours_ago(self) -> Optional[float]:
        if self.last_validated is None:
            return None
        try:
            lv = datetime.fromisoformat(self.last_validated)
            delta = (datetime.now(timezone.utc).replace(tzinfo=None) - lv.replace(tzinfo=None)).total_seconds() / 3600
            return round(delta, 1)
        except (ValueError, TypeError):
            return None

    model_config = {"from_attributes": True}


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
    validation_status: Optional[str] = Query(
        None,
        description="Filter by validation status (pending, validating, validated, failed)",
    ),
    use_case: Optional[str] = Query(
        None,
        description="Optimize for use case: scraping, browsing, streaming, security",
    ),
    order_by: str = Query(
        "quality_score",
        description="Sort by: quality_score, latency_ms, speed_mbps, created_at",
    ),
    order_direction: str = Query("desc", description="Sort direction: asc or desc"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db),
):
    """
    Advanced proxy search with comprehensive filtering options.

    Public endpoint that returns validated proxies matching the specified criteria.
    Supports filtering by protocol, country, anonymity level, quality score,
    speed, latency, and validation status. Results can be sorted by various fields.
    Use the `use_case` parameter to automatically optimize for a specific scenario.

    - **Authentication**: Not required (public endpoint)
    - **Rate limit**: 100 requests/hour
    - **Returns**: Paginated list of proxies with full metadata

    Use cases:
    - `scraping`: high anonymity + fast latency (min quality: 70)
    - `browsing`: any proxy with low latency (min quality: 40)
    - `streaming`: high bandwidth + low latency prioritized
    - `security`: SOCKS5 + elite anonymity only

    Examples:
    - `/api/v1/proxies/advanced?protocol=socks5&min_quality=80&limit=10`
    - `/api/v1/proxies/advanced?country_code=US&anonymity=elite`
    - `/api/v1/proxies/advanced?order_by=latency_ms&order_direction=asc`
    - `/api/v1/proxies/advanced?use_case=scraping&limit=5`
    """
    # Apply use-case presets
    if use_case:
        if use_case == "scraping":
            order_by = "quality_score"
            order_direction = "desc"
            if min_quality is None:
                min_quality = 70
            if anonymity is None:
                anonymity = "elite"
        elif use_case == "browsing":
            order_by = "latency_ms"
            order_direction = "asc"
            if min_quality is None:
                min_quality = 40
        elif use_case == "streaming":
            order_by = "speed_mbps"
            order_direction = "desc"
            if min_quality is None:
                min_quality = 50
        elif use_case == "security":
            order_by = "quality_score"
            order_direction = "desc"
            if protocol is None:
                protocol = "socks5"
            if anonymity is None:
                anonymity = "elite"
            if min_quality is None:
                min_quality = 60

    proxies, total = await db_storage.get_proxies(
        session=session,
        protocol=protocol,
        country_code=country_code,
        anonymity=anonymity,
        min_quality=min_quality,
        is_working=is_working,
        validation_status=validation_status,
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
    """
    Get available filter options for the proxy search UI.

    Returns distinct values for protocols, countries, anonymity levels,
    proxy types, and quality ranges. Use this to populate filter dropdowns
    in the frontend.

    - **Authentication**: Not required (public endpoint)
    - **Returns**: Lists of available filter options with counts
    """
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
    format: str = Query("txt", description="Export format: txt, json, csv, pac, sing-box, clash"),
    protocol: Optional[str] = None,
    country_code: Optional[str] = None,
    min_quality: Optional[int] = None,
    limit: int = Query(1000, ge=1, le=10000),
    session: AsyncSession = Depends(get_db),
):
    """
    Export proxies in various formats for easy integration.

    Download proxies in plain text (one URL per line), JSON, CSV,
    or PAC (Proxy Auto-Configuration) format. The PAC format can be
    directly used in browser proxy settings for automatic proxy rotation.

    - **Authentication**: Not required (public endpoint)
    - **Rate limit**: 100 exports/hour
    - **Formats**:
      - `txt`: Plain text, one proxy URL per line
      - `json`: JSON array with full proxy metadata
      - `csv`: CSV file with columns (URL, Protocol, Country, etc.)
      - `pac`: PAC file for browser auto-configuration

    Examples:
    - `/api/v1/proxies/export?format=txt&protocol=socks5&min_quality=70`
    - `/api/v1/proxies/export?format=csv&country_code=US`
    """
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
        stale_cutoff_hours=8760,  # 1 year - effectively disable TTL filter for exports
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
                "can_access_google": proxy.can_access_google,
                "can_access_openai": proxy.can_access_openai,
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
            [
                "URL",
                "Protocol",
                "Country",
                "Latency(ms)",
                "Anonymity",
                "Quality",
                "Google",
                "OpenAI",
            ]
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
                    "Yes" if proxy.can_access_google else "No",
                    "Yes" if proxy.can_access_openai else "No",
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
    // Generated: {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}
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

    elif format == "sing-box":
        # Generate Sing-box configuration (JSON)
        # https://sing-box.sagernet.org/configuration/
        outbounds = []
        for i, proxy in enumerate(proxies[:50]):  # Limit to top 50
            if proxy.protocol.lower() in ["http", "https"]:
                outbound = {
                    "type": "http",
                    "tag": f"1proxy-{i+1}",
                    "server": proxy.ip or "",
                    "server_port": proxy.port or 8080,
                }
                # Add auth if available (not in current model)
            elif proxy.protocol.lower() in ["socks4", "socks5"]:
                outbound = {
                    "type": "socks",
                    "tag": f"1proxy-{i+1}",
                    "server": proxy.ip or "",
                    "server_port": proxy.port or 1080,
                    "version": "5" if proxy.protocol.lower() == "socks5" else "4",
                }
            else:
                continue
            outbounds.append(outbound)

        # Add direct outbound as fallback
        outbounds.append({"type": "direct", "tag": "direct"})

        config = {
            "outbounds": outbounds,
            "route": {
                "rules": [
                    {
                        "type": "geoip",
                        "geoip": ["private"],
                        "outbound": "direct"
                    }
                ],
                "final": "1proxy-1" if outbounds else "direct"
            }
        }

        return PlainTextResponse(
            content=json.dumps(config, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=1proxy_sing-box.json"},
        )

    elif format == "clash":
        # Generate Clash configuration (YAML)
        # https://github.com/Dreamacro/clash/wiki/Configuration
        import yaml

        proxies_list = []
        proxy_names = []
        for i, proxy in enumerate(proxies[:50]):  # Limit to top 50
            if proxy.protocol.lower() in ["http", "https"]:
                proxy_names.append(f"1proxy-{i+1}")
                proxies_list.append({
                    "name": f"1proxy-{i+1}",
                    "type": "http",
                    "server": proxy.ip or "",
                    "port": proxy.port or 8080,
                })
            elif proxy.protocol.lower() in ["socks4", "socks5"]:
                proxy_names.append(f"1proxy-{i+1}")
                proxies_list.append({
                    "name": f"1proxy-{i+1}",
                    "type": "socks5" if proxy.protocol.lower() == "socks5" else "socks4",
                    "server": proxy.ip or "",
                    "port": proxy.port or 1080,
                })

        # Add DIRECT as fallback
        proxy_names.append("DIRECT")

        config = {
            "proxies": proxies_list,
            "proxy-groups": [
                {
                    "name": "1proxy",
                    "type": "select",
                    "proxies": proxy_names
                }
            ],
            "rules": [
                "GEOIP,PRIVATE,DIRECT",
                "MATCH,1proxy"
            ]
        }

        yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)

        return PlainTextResponse(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={"Content-Disposition": "attachment; filename=1proxy_clash.yaml"},
        )

    return {"error": "Invalid format. Supported: txt, json, csv, pac, sing-box, clash"}


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

    Returns a single random proxy matching the specified criteria.
    Use the 'exclude' parameter to implement rotation by excluding
    previously used IPs. This ensures you get different proxies on each request.

    - **Authentication**: Not required (public endpoint)
    - **Rate limit**: 100 requests/hour
    - **Tip**: Combine with `min_quality` for reliable proxies

    Examples:
    - `/api/v1/proxies/random?min_quality=70`
    - `/api/v1/proxies/random?protocol=socks5&country_code=US`
    - `/api/v1/proxies/random?exclude=192.168.1.1,10.0.0.1`
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
    tested_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

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


# ========== PROXY ROTATION ENDPOINTS ==========


class RotationRequest(BaseModel):
    session_id: Optional[str] = None  # Auto-generate if not provided
    strategy: str = Query(
        "random",
        description="Rotation strategy: random, round_robin, quality, least_used",
    )
    protocol: Optional[str] = Query(None, description="Filter by protocol")
    country_code: Optional[str] = Query(None, description="Filter by country code")
    min_quality: Optional[int] = Query(
        None, ge=0, le=100, description="Minimum quality score"
    )
    anonymity: Optional[str] = Query(None, description="Filter by anonymity level")
    max_latency: Optional[int] = Query(None, ge=0, description="Maximum latency in ms")
    max_usage_per_proxy: int = Query(
        5, ge=1, le=100, description="Max times to use each proxy"
    )
    cooldown_minutes: int = Query(
        5, ge=0, le=60, description="Minutes before reusing proxy"
    )


class RotationSessionCreate(BaseModel):
    session_id: Optional[str] = None
    strategy: str = "random"
    max_usage_per_proxy: int = 5
    cooldown_minutes: int = 5


@router.get("/proxies/rotate", response_model=ProxyResponse)
@limiter.limit("60/minute")
async def rotate_proxy(
    request: Request,
    session_id: Optional[str] = Query(
        None, description="Rotation session ID (auto-generated if not provided)"
    ),
    strategy: str = Query(
        "random", description="random, round_robin, quality, least_used"
    ),
    protocol: Optional[str] = Query(None),
    country_code: Optional[str] = Query(None),
    min_quality: Optional[int] = Query(None, ge=0, le=100),
    anonymity: Optional[str] = Query(None),
    max_latency: Optional[int] = Query(None, ge=0),
    max_usage_per_proxy: int = Query(5, ge=1, le=100),
    cooldown_minutes: int = Query(5, ge=0, le=60),
    session: AsyncSession = Depends(get_db),
):
    """
    Get next proxy in automated rotation sequence.

    This endpoint manages proxy rotation state and ensures you get
    different proxies on each request. Supports multiple strategies.

    Strategies:
    - random: Randomly selects from available proxies
    - round_robin: Cycles through proxies in order
    - quality: Prioritizes highest quality proxies
    - least_used: Selects least frequently used proxies

    The rotation state is maintained in-memory with automatic cleanup
    of expired sessions (default: 60 minutes of inactivity).

    Example:
        # Get random proxy (auto-generates session)
        GET /api/v1/proxies/rotate

        # Get next proxy in round-robin with session tracking
        GET /api/v1/proxies/rotate?session_id=my-session&strategy=round_robin&protocol=socks5

        # Quality-based rotation for high-latency requests
        GET /api/v1/proxies/rotate?strategy=quality&min_quality=80&max_latency=500
    """
    from app.proxy_rotator import proxy_rotator, RotationStrategy

    # Validate strategy
    try:
        rotation_strategy = RotationStrategy(strategy)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Must be one of: {[s.value for s in RotationStrategy]}",
        )

    # Generate session ID if not provided
    if not session_id:
        import uuid

        session_id = str(uuid.uuid4())[:8]

    # Get or create rotation session
    rotation_session = proxy_rotator.get_or_create_session(
        session_id=session_id,
        strategy=rotation_strategy,
        max_usage_per_proxy=max_usage_per_proxy,
        cooldown_minutes=cooldown_minutes,
    )

    # Get proxies matching criteria
    proxies = await proxy_rotator.get_proxies_for_rotation(
        session=session,
        protocol=protocol,
        country_code=country_code,
        min_quality=min_quality,
        anonymity=anonymity,
        max_latency=max_latency,
    )

    if not proxies:
        raise HTTPException(
            status_code=404,
            detail="No proxies found matching the specified criteria",
        )

    # Get next proxy based on strategy
    proxy = proxy_rotator.get_next_proxy(rotation_session, proxies)

    if not proxy:
        raise HTTPException(
            status_code=404,
            detail="No available proxies (all excluded or used maximum times). "
            "Try resetting the session or increasing max_usage_per_proxy.",
        )

    # Mark proxy as used
    rotation_session.mark_proxy_used(proxy.id, proxy.ip)

    return ProxyResponse(
        **{
            **proxy.__dict__,
            "last_validated": proxy.last_validated.isoformat()
            if proxy.last_validated
            else None,
        }
    )


@router.post("/proxies/rotate/session")
@limiter.limit("30/minute")
async def create_rotation_session(
    request: Request,
    session_config: RotationSessionCreate,
):
    """
    Create a new rotation session with specific settings.

    Returns the session ID which should be used in subsequent
    /proxies/rotate requests to maintain state.

    Useful for:
    - Having multiple independent rotation sessions
    - Setting custom rotation parameters
    - Managing rotation for different use cases
    """
    from app.proxy_rotator import proxy_rotator, RotationStrategy

    # Generate session ID if not provided
    if not session_config.session_id:
        import uuid

        session_config.session_id = str(uuid.uuid4())[:8]

    # Validate strategy
    try:
        rotation_strategy = RotationStrategy(session_config.strategy)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Must be one of: {[s.value for s in RotationStrategy]}",
        )

    # Create session
    rotation_session = proxy_rotator.get_or_create_session(
        session_id=session_config.session_id,
        strategy=rotation_strategy,
        max_usage_per_proxy=session_config.max_usage_per_proxy,
        cooldown_minutes=session_config.cooldown_minutes,
    )

    return {
        "session_id": rotation_session.session_id,
        "strategy": rotation_session.strategy.value,
        "created_at": rotation_session.created_at.isoformat(),
        "max_usage_per_proxy": rotation_session.max_usage_per_proxy,
        "cooldown_minutes": rotation_session.cooldown_minutes,
        "message": "Use this session_id in /proxies/rotate requests",
    }


@router.get("/proxies/rotate/session/{session_id}/stats")
async def get_rotation_session_stats(session_id: str):
    """
    Get statistics for a rotation session.

    Shows usage statistics including:
    - How many proxies have been used
    - How many times each proxy was used
    - Excluded IPs count
    - Session age
    """
    from app.proxy_rotator import proxy_rotator

    stats = proxy_rotator.get_session_stats(session_id)

    if not stats:
        raise HTTPException(
            status_code=404, detail="Rotation session not found or expired"
        )

    return stats


@router.post("/proxies/rotate/session/{session_id}/reset")
async def reset_rotation_session(session_id: str):
    """
    Reset a rotation session.

    Clears all usage history and excluded IPs,
    allowing proxies to be used again.

    Useful when you want to reuse proxies or
    start fresh rotation.
    """
    from app.proxy_rotator import proxy_rotator

    stats = proxy_rotator.get_session_stats(session_id)

    if not stats:
        raise HTTPException(
            status_code=404, detail="Rotation session not found or expired"
        )

    proxy_rotator.reset_session(session_id)

    return {
        "session_id": session_id,
        "message": "Rotation session reset successfully",
        "previous_stats": stats,
    }


@router.delete("/proxies/rotate/session/{session_id}")
async def delete_rotation_session(session_id: str):
    """
    Delete a rotation session.

    Removes the session from memory entirely.
    """
    from app.proxy_rotator import proxy_rotator

    stats = proxy_rotator.get_session_stats(session_id)

    if not stats:
        raise HTTPException(
            status_code=404, detail="Rotation session not found or expired"
        )

    proxy_rotator.delete_session(session_id)

    return {
        "session_id": session_id,
        "message": "Rotation session deleted successfully",
    }


@router.post("/proxies/rotate/session/{session_id}/exclude")
async def exclude_proxy_from_rotation(session_id: str, ip: str):
    """
    Manually exclude a proxy IP from rotation.

    Useful when you encounter a bad proxy and want to
    avoid it for the rest of the session.
    """
    from app.proxy_rotator import proxy_rotator

    stats = proxy_rotator.get_session_stats(session_id)

    if not stats:
        raise HTTPException(
            status_code=404, detail="Rotation session not found or expired"
        )

    proxy_rotator.exclude_proxy_ip(session_id, ip)

    return {
        "session_id": session_id,
        "excluded_ip": ip,
        "message": f"IP {ip} excluded from rotation for this session",
    }


@router.delete("/proxies/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_proxy(
    request: Request,
    proxy_id: int,
    session: AsyncSession = Depends(get_db),
    admin_user=Depends(require_admin),
):
    """
    Delete a proxy from the database.

    Permanently removes a proxy by its ID. This operation cannot be undone.
    Only available to admin users.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 30 requests/minute
    - **Returns**: 204 No Content on success
    """
    success = await db_storage.delete_proxy(session, proxy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return None


@router.get("/health", tags=["health"], summary="Health check")
async def health_check(session: AsyncSession = Depends(get_db)):
    """
    Health check endpoint for monitoring.

    Returns service status and database connectivity.
    """
    from sqlalchemy import text

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
