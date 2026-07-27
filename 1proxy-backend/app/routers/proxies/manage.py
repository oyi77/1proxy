from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import time
import aiohttp
import asyncio

from app.database import get_db
from app.db_storage import db_storage
from app.dependencies import require_admin
from app.routers.proxies._router import router, limiter
from app.routers.proxies.models import ProxyTestRequest, ProxyTestResponse


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
