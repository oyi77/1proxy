from fastapi import Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.routers.proxies._router import router, limiter
from app.routers.proxies.models import ProxyResponse, RotationSessionCreate


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
