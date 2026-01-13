import asyncio
from datetime import datetime, timedelta
from app.database import AsyncSessionLocal
from app.db_storage import db_storage


async def background_validation_worker(
    batch_size: int = 50, interval_seconds: int = 60
):
    """Continuously validate pending proxies in the background"""
    print("🔄 Background validation worker started")

    while True:
        try:
            async with AsyncSessionLocal() as session:
                result = await db_storage.validate_and_update_proxies(
                    session, limit=batch_size
                )

                if result["total"] > 0:
                    print(
                        f"✅ Validated {result['validated']} proxies, "
                        f"❌ {result['failed']} failed ({result['total']} total)"
                    )

                await asyncio.sleep(interval_seconds)

        except Exception as e:
            print(f"⚠️  Background validation error: {e}")
            await asyncio.sleep(interval_seconds)


async def revalidate_old_proxies(hours: int = 24, batch_size: int = 50):
    """Revalidate proxies that haven't been checked in X hours"""
    from sqlalchemy import select, or_
    from app.db_models import Proxy

    print(f"🔄 Revalidating proxies older than {hours} hours")

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
                print("✅ No old proxies to revalidate")
                return

            for proxy in old_proxies:
                proxy.validation_status = "pending"

            await session.commit()

            validation_result = await db_storage.validate_and_update_proxies(
                session, proxy_ids=[p.id for p in old_proxies]
            )

            print(
                f"✅ Revalidated {validation_result['validated']} old proxies, "
                f"❌ {validation_result['failed']} failed"
            )

    except Exception as e:
        print(f"⚠️  Revalidation error: {e}")
