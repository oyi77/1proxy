import asyncio
from datetime import datetime, timedelta
from app.database import AsyncSessionLocal, get_db
from app.db_storage import db_storage
from app.grabber import GitHubGrabber
from app.sources import SourceRegistry
import logging

logger = logging.getLogger(__name__)


async def background_scraper_worker(interval_minutes: int = 10):
    """Automatically scrape all enabled sources periodically"""
    
    # Initial scrape on startup
    await asyncio.sleep(10)  # Wait 10 seconds for app to fully start

    while True:
        try:
            async with get_db() as session:
                # Get all enabled sources from database
                sources_db = await db_storage.get_sources(session, enabled_only=True)

            if not sources_db:
                logger.warning("⚠️  No enabled sources found")
                return

            grabber = GitHubGrabber()
            total_scraped = 0
            total_added = 0

            for source_db in sources_db:
                try:
                    from app.models import SourceConfig, SourceType

                    # Create SourceConfig from database source
                    source = SourceConfig(
                        url=source_db.url, type=SourceType(source_db.type)
                    )

                    proxies = await grabber.extract_proxies(source)

                    proxies_data = []
                    for p in proxies:
                        data = (
                            p.model_dump() if hasattr(p, "model_dump") else p.__dict__
                        )
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

                    # Update source stats
                    source_db.total_scraped = (source_db.total_scraped or 0) + len(
                        proxies
                    )
                    source_db.last_scraped = datetime.utcnow()

                    logger.info(
                        f"✅ Scraped {len(proxies)} proxies from {source_db.name} (added {added} new)"
                    )

                except Exception as e:
                    logger.error(f"❌ Failed to scrape {source_db.url}: {e}")
                    continue

            await session.commit()
            logger.info(
                f"✅ Auto-scraping complete: {total_scraped} scraped, {total_added} new proxies added"
            )

    except Exception as e:
        logger.error(f"⚠️  Auto-scraping error: {e}")


async def background_validation_worker(
    batch_size: int = 50, interval_seconds: int = 60
):
    """Continuously validate pending proxies in the background"""
    logger.info("🔄 Background validation worker started")

    while True:
        try:
            async with AsyncSessionLocal() as session:
                result = await db_storage.validate_and_update_proxies(
                    session, limit=batch_size
                )

                if result["total"] > 0:
                    logger.info(
                        f"✅ Validated {result['validated']} proxies, "
                        f"❌ {result['failed']} failed ({result['total']} total)"
                    )

                await asyncio.sleep(interval_seconds)

        except Exception as e:
            logger.error(f"⚠️  Background validation error: {e}")
            await asyncio.sleep(interval_seconds)


async def revalidate_old_proxies(hours: int = 24, batch_size: int = 50):
    """Revalidate proxies that haven't been checked in X hours"""
    from sqlalchemy import select, or_
    from app.db_models import Proxy

    logger.info(f"🔄 Revalidating proxies older than {hours} hours")

    try:
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

            for proxy in old_proxies:
                proxy.validation_status = "pending"

            await session.commit()

            validation_result = await db_storage.validate_and_update_proxies(
                session, proxy_ids=[p.id for p in old_proxies]
            )

            logger.info(
                f"✅ Revalidated {validation_result['validated']} old proxies, "
                f"❌ {validation_result['failed']} failed"
            )

    except Exception as e:
        logger.error(f"⚠️  Revalidation error: {e}")
