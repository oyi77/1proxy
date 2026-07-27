"""
Continuous lightweight proxy healthcheck worker.

Unlike the full validation pipeline (which does geo, anonymity, SSL checks),
this worker just does a quick TCP/HTTP connectivity check — Phase 1 only.

Goal: keep the "working" proxy pool fresh by quickly detecting dead proxies
and updating latency metrics in real-time for the rotator.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.db_storage import db_storage
from app.db_models import Proxy
from app.worker_heartbeat import worker_heartbeats

logger = logging.getLogger(__name__)

# How many concurrent health checks
HEALTHCHECK_CONCURRENCY = 50
# Phase 1 timeout — just need to know if it's alive
HEALTHCHECK_TIMEOUT = 3.0
# How many to check per cycle
HEALTHCHECK_BATCH_SIZE = 100
# Interval between cycles
HEALTHCHECK_INTERVAL_SECONDS = 15
# Max failures before marking dead
MAX_FAILURES_BEFORE_DEAD = 2
# Stale cutoff — skip proxies checked within this window
STALE_CUTOFF_MINUTES = 5


async def _quick_ping(
    proxy_url: str,
    semaphore: asyncio.Semaphore,
    session: "aiohttp.ClientSession",
) -> tuple[bool, int | None]:
    """Ultra-light connectivity check — Phase 1 only, no external APIs."""
    import aiohttp

    norm_url = proxy_url
    if norm_url.startswith("socks5://") or norm_url.startswith("socks4://"):
        norm_url = "http://" + norm_url.split("://", 1)[1]

    try:
        async with semaphore:
            start = time.perf_counter()
            async with session.get(
                "http://httpbin.org/ip",
                proxy=norm_url,
                ssl=False,
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(
                    total=HEALTHCHECK_TIMEOUT,
                    connect=1.5,
                    sock_read=HEALTHCHECK_TIMEOUT,
                ),
            ) as resp:
                latency_ms = int((time.perf_counter() - start) * 1000)
                return (resp.status == 200, latency_ms)
    except Exception:
        return (False, None)


async def healthcheck_worker():
    """
    Continuous lightweight healthcheck loop.

    Runs every HEALTHCHECK_INTERVAL_SECONDS, picks up to
    HEALTHCHECK_BATCH_SIZE validated working proxies that haven't been
    checked in STALE_CUTOFF_MINUTES, and does a quick Phase 1 ping.

    Dead proxies → is_working=False (will be purged by cleanup worker)
    Live proxies → latency_ms updated in real-time for the rotator
    """
    import aiohttp

    logger.info(
        f"🏥 Healthcheck worker started: "
        f"batch={HEALTHCHECK_BATCH_SIZE}, "
        f"concurrency={HEALTHCHECK_CONCURRENCY}, "
        f"timeout={HEALTHCHECK_TIMEOUT}s, "
        f"interval={HEALTHCHECK_INTERVAL_SECONDS}s"
    )

    await asyncio.sleep(15)  # Wait for app to stabilize

    connector = aiohttp.TCPConnector(
        limit=HEALTHCHECK_CONCURRENCY * 2,
        limit_per_host=5,
        ttl_dns_cache=300,
        enable_cleanup_closed=True,
    )
    timeout = aiohttp.ClientTimeout(
        total=HEALTHCHECK_TIMEOUT,
        connect=1.5,
        sock_read=HEALTHCHECK_TIMEOUT,
    )
    semaphore = asyncio.Semaphore(HEALTHCHECK_CONCURRENCY)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={"User-Agent": "1proxy-healthcheck/1.0"},
    ) as http_session:
        while True:
            try:
                worker_heartbeats["proxy-healthcheck-worker"] = {
                    "alive": True,
                    "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                }
                async with AsyncSessionLocal() as db_session:
                    now = datetime.now(timezone.utc).replace(tzinfo=None)
                    cutoff = now - timedelta(minutes=STALE_CUTOFF_MINUTES)

                    # Pick proxies that haven't been checked recently
                    query = (
                        select(Proxy)
                        .where(
                            Proxy.is_working == True,
                            Proxy.validation_status == "validated",
                            Proxy.ip.isnot(None),
                            Proxy.validation_failures < MAX_FAILURES_BEFORE_DEAD,
                            (Proxy.last_validated.is_(None) | (Proxy.last_validated < cutoff)),
                        )
                        .order_by(Proxy.last_validated.asc().nulls_first())
                        .limit(HEALTHCHECK_BATCH_SIZE)
                    )
                    result = await db_session.execute(query)
                    proxies = list(result.scalars().all())

                    if not proxies:
                        await asyncio.sleep(HEALTHCHECK_INTERVAL_SECONDS)
                        continue

                    # Quick ping all of them
                    tasks = []
                    valid_urls = {}
                    for p in proxies:
                        url = f"{p.protocol}://{p.ip}:{p.port}"
                        valid_urls[p.id] = url
                        tasks.append(_quick_ping(url, semaphore, http_session))

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Update DB results
                    alive_count = 0
                    dead_count = 0
                    updated_latencies = 0

                    for proxy, result_data in zip(proxies, results):
                        if isinstance(result_data, Exception):
                            proxy.validation_failures = (proxy.validation_failures or 0) + 1
                            if (proxy.validation_failures or 0) >= MAX_FAILURES_BEFORE_DEAD:
                                proxy.is_working = False
                                dead_count += 1
                            continue

                        success, latency_ms = result_data
                        if success and latency_ms is not None:
                            proxy.latency_ms = latency_ms
                            proxy.validation_failures = 0
                            proxy.last_validated = now
                            alive_count += 1
                            updated_latencies += 1
                        else:
                            proxy.validation_failures = (proxy.validation_failures or 0) + 1
                            if (proxy.validation_failures or 0) >= MAX_FAILURES_BEFORE_DEAD:
                                proxy.is_working = False
                                dead_count += 1

                    await db_session.commit()

                    if alive_count or dead_count:
                        logger.info(
                            f"🏥 Healthcheck: {alive_count} alive, "
                            f"{dead_count} marked dead, "
                            f"{updated_latencies} latency updated "
                            f"(checked {len(proxies)} total)"
                        )

                await asyncio.sleep(HEALTHCHECK_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                logger.info("🏥 Healthcheck worker cancelled")
                break
            except Exception as e:
                logger.error(f"⚠️  Healthcheck worker error: {e}")
                await asyncio.sleep(30)
