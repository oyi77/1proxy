from fastapi import Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timezone

from app.database import get_db
from app.db_storage import db_storage
from app.routers.proxies._router import router, limiter
from app.routers.proxies.models import ProxyResponse, ProxiesListResponse


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
            if min_quality is None:
                min_quality = 70
            if anonymity is None:
                anonymity = "elite"
        elif use_case == "browsing":
            order_by = "latency_ms"
            if min_quality is None:
                min_quality = 40
        elif use_case == "streaming":
            order_by = "speed_mbps"
            if min_quality is None:
                min_quality = 50
        elif use_case == "security":
            order_by = "quality_score"
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
