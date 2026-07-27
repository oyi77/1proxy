"""Admin-only scrape endpoints extracted from main.py."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
import asyncio

from app.database import AsyncSessionLocal
from app.db_storage import db_storage
from app.dependencies import require_admin
from app.db_models import User
from app.models import SourceConfig, SourceType
from app.grabber import GitHubGrabber
from app.utils import proxy_to_dict

router = APIRouter(prefix="/api/v1/proxies", tags=["scraping"], dependencies=[Depends(require_admin)])

grabber = GitHubGrabber()


@router.post("/scrape", response_model=dict)
@limiter.limit("10/minute")
async def scrape_proxies(
    request: Request, source: SourceConfig, current_user: User = Depends(require_admin)
):
    async with AsyncSessionLocal() as session:
        try:
            proxies = await grabber.extract_proxies(source)
            proxies_data = [proxy_to_dict(p) for p in proxies]
            added = await db_storage.add_proxies(session, proxies_data)

            validation_results = await db_storage.validate_and_update_proxies(
                session, limit=min(added, 100)
            )

            return {
                "source": str(source.url),
                "scraped": len(proxies),
                "added": added,
                "validated": validation_results["validated"],
                "failed": validation_results["failed"],
                "total": await db_storage.count_proxies(session),
            }
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Request timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo")
@limiter.limit("5/minute")
async def demo_scrape(request: Request, current_user: User = Depends(require_admin)):
    async with AsyncSessionLocal() as session:
        source = SourceConfig(
            url="https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            type=SourceType.GITHUB_RAW,
        )
        try:
            proxies = await grabber.extract_proxies(source)
            proxies_data = [proxy_to_dict(p) for p in proxies]
            sample_list = [proxy_to_dict(p) for p in proxies[:5]]

            added = await db_storage.add_proxies(session, proxies_data)

            validation_results = await db_storage.validate_and_update_proxies(
                session, limit=min(added, 50)
            )

            return {
                "message": "Demo scrape completed",
                "source": str(source.url),
                "scraped": len(proxies),
                "added": added,
                "validated": validation_results["validated"],
                "failed": validation_results["failed"],
                "total_stored": await db_storage.count_proxies(session),
                "sample": sample_list,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape-all")
@limiter.limit("5/minute")
async def scrape_all_sources(request: Request, current_user: User = Depends(require_admin)):
    async with AsyncSessionLocal() as session:
        sources = await db_storage.get_sources(session, enabled_only=True)
        results = []
        total_scraped = 0
        total_added = 0
        total_validated = 0
        total_failed = 0

        for source_db in sources:
            try:
                source = SourceConfig(url=source_db.url, type=SourceType(source_db.type))
                proxies = await grabber.extract_proxies(source)
                proxies_data = [proxy_to_dict(p) for p in proxies]
                added = await db_storage.add_proxies(session, proxies_data)

                validation_results = await db_storage.validate_and_update_proxies(
                    session, limit=min(added, 50)
                )

                total_scraped += len(proxies)
                total_added += added
                total_validated += validation_results["validated"]
                total_failed += validation_results["failed"]
                results.append(
                    {
                        "url": str(source.url),
                        "status": "success",
                        "scraped": len(proxies),
                        "added": added,
                        "validated": validation_results["validated"],
                        "failed": validation_results["failed"],
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "url": str(source_db.url),
                        "status": "failed",
                        "error": str(e),
                        "scraped": 0,
                        "added": 0,
                        "validated": 0,
                        "failed": 0,
                    }
                )

        return {
            "message": f"Scraped {len(sources)} sources",
            "total_scraped": total_scraped,
            "total_added": total_added,
            "total_validated": total_validated,
            "total_failed": total_failed,
            "total_stored": await db_storage.count_proxies(session),
            "results": results,
        }
