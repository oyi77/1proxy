import asyncio
from datetime import datetime, timedelta
from app.database import AsyncSessionLocal
from app.db_storage import db_storage
from app.grabber import GitHubGrabber, WebGrabber
from app.models import SourceType
import logging

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent database operations (prevent SQLite lock contention)
DB_SEMAPHORE = asyncio.Semaphore(3)  # Max 3 concurrent database operations

async def scrape_enabled_sources_once(session) -> dict:
    """Scrape all currently-enabled sources once.

    Intended for reuse by the background worker and for unit testing.
    """

    sources_db = await db_storage.get_sources(session, enabled_only=True)

    if not sources_db:
        logger.warning("⚠️  No enabled sources found, auto-seeding...")
        from app.db_models import User
        from sqlalchemy import select
        
        admin_result = await session.execute(
            select(User).where(User.role == "admin").limit(1)
        )
        admin = admin_result.scalar_one_or_none()
        
        if not admin:
            admin = User(
                oauth_provider="local",
                oauth_id="admin",
                email="admin@1proxy.local",
                username="admin",
                role="admin",
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
        
        await db_storage.seed_admin_sources(session, admin_user_id=admin.id)
        sources_db = await db_storage.get_sources(session, enabled_only=True)
        if not sources_db:
            logger.error("❌ Auto-seed failed, no sources available")
            return {"total_scraped": 0, "total_added": 0, "sources": 0}

    total_scraped = 0
    total_added = 0

    for source_db in sources_db:
        try:
            from app.models import SourceConfig

            source = SourceConfig(url=source_db.url, type=SourceType(source_db.type))

            # GENERIC_TEXT sources use WebGrabber for HTML parsing
            # They may be slower but provide fresh proxies from web tables
            if source.type == SourceType.GENERIC_TEXT:
                grabber = WebGrabber()
            elif source.type == SourceType.TOR_EXIT:
                grabber = WebGrabber()
            elif source.type == SourceType.GITHUB_RAW:
                grabber = GitHubGrabber()
            else:
                grabber = GitHubGrabber()

            proxies = await grabber.extract_proxies(source)

            proxies_data = []
            for p in proxies:
                data = p.model_dump() if hasattr(p, "model_dump") else p.__dict__
                proxies_data.append(
                    {
                        "url": f"{data.get('protocol', 'http')}://{data.get('ip')}:{data.get('port')}",
                        "protocol": data.get("protocol", "http"),
                        "ip": data.get("ip"),
                        "port": data.get("port"),
                        "country_code": data.get("country_code"),
                        "country_name": data.get("country_name"),
                        "city": data.get("city"),
                        "latency_ms": data.get("latency_ms"),
                        "speed_mbps": data.get("speed_mbps"),
                        "anonymity": data.get("anonymity"),
                        "proxy_type": data.get("proxy_type"),
                        "source_id": source_db.id,
                    }
                )

            added = await db_storage.add_proxies(session, proxies_data)
            total_scraped += len(proxies)
            total_added += added

            source_db.total_scraped = (source_db.total_scraped or 0) + len(proxies)
            source_db.last_scraped = datetime.utcnow()
            source_db.validated = len(proxies) > 0
            source_db.validation_error = None if proxies else "No proxies extracted from source"
            if len(proxies) > 0:
                source_db.success_rate = min(1.0, added / len(proxies))
            else:
                source_db.success_rate = 0.0

            logger.info(
                f"✅ Scraped {len(proxies)} proxies from {source_db.name} (added {added} new)"
            )

        except FileNotFoundError as e:
            # A 404 raw URL is effectively a dead source: disable it to prevent
            # endless retries/log spam in constrained deployment environments.
            source_db.enabled = False
            source_db.validated = False
            source_db.validation_error = str(e)
            logger.warning(f"⚠️  Disabling source {source_db.url}: {e}")

        except ValueError as e:
            # Common case: oversized source content; disable to prevent repeated
            # memory pressure / OOM kills.
            if "too large" in str(e).lower():
                source_db.enabled = False
                source_db.validated = False
                source_db.validation_error = str(e)
                logger.warning(f"⚠️  Disabling source {source_db.url}: {e}")
            else:
                logger.error(f"❌ Failed to scrape {source_db.url}: {e}")

        except Exception as e:
            logger.error(f"❌ Failed to scrape {source_db.url}: {e}")
            continue

    await session.commit()

    logger.info(
        f"✅ Auto-scraping complete: {total_scraped} scraped, {total_added} new proxies added"
    )

    return {
        "total_scraped": total_scraped,
        "total_added": total_added,
        "sources": len(sources_db),
    }


async def background_scraper_worker(interval_minutes: int = 10):
    """Automatically scrape all enabled sources periodically"""

    # Initial scrape on startup
    await asyncio.sleep(10)  # Wait 10 seconds for app to fully start

    while True:
        try:
            async with DB_SEMAPHORE:  # Limit concurrent database operations
                async with AsyncSessionLocal() as session:
                    await scrape_enabled_sources_once(session)

            await asyncio.sleep(interval_minutes * 60)

        except Exception as e:
            logger.error(f"[WARN] Background scraper error: {e}")
            await asyncio.sleep(300)

async def background_validation_worker(
    batch_size: int = 20, interval_seconds: int = 60
):
    """Continuously validate pending proxies in the background"""
    logger.info("✓ Background validation worker started")

    while True:
        try:
            async with DB_SEMAPHORE:  # Limit concurrent database operations
                async with AsyncSessionLocal() as session:
                    result = await db_storage.validate_and_update_proxies(
                        session, limit=batch_size
                    )

                    if result["validated"] > 0:
                        logger.info(
                            f"[OK] Validated {result['validated']} proxies, "
                            f"[FAIL] {result['failed']} failed"
                        )

            await asyncio.sleep(interval_seconds)

        except Exception as e:
            logger.error(f"[WARN] Validation worker error: {e}")
            await asyncio.sleep(60)


async def revalidate_old_proxies(hours: int = 24, batch_size: int = 15):
    """Revalidate proxies that haven't been checked in X hours"""
    # Wait for initial surge to pass
    await asyncio.sleep(60)

    from sqlalchemy import select, or_
    from app.db_models import Proxy

    logger.info(f"🔄 Revalidating proxies older than {hours} hours")

    try:
        async with DB_SEMAPHORE:  # Limit concurrent database operations
            async with AsyncSessionLocal() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)

                query = (
                    select(Proxy)
                    .where(
                        or_(
                            Proxy.last_validated < cutoff_time,
                            Proxy.last_validated.is_(None),
                        )
                    )
                    .limit(batch_size)
                )

                result = await session.execute(query)
                old_proxies = result.scalars().all()

                if not old_proxies:
                    logger.info("✅ No old proxies to revalidate")
                    return

                # Note: We NO LONGER set validation_status = "pending" here.
                # This ensures proxies stay visible in the UI while being re-checked.
                # validate_and_update_proxies now handles non-pending IDs if passed explicitly.

                validation_result = await db_storage.validate_and_update_proxies(
                    session, proxy_ids=[p.id for p in old_proxies]
                )

                logger.info(
                    f"✅ Revalidated {validation_result['validated']} old proxies, "
                    f"❌ {validation_result['failed']} failed"
                )

    except Exception as e:
        logger.error(f"⚠️  Revalidation error: {e}")
