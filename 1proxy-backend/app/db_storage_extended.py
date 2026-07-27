"""
Extended database storage methods for enhanced scraping functionality.
Builds upon the existing db_storage.py with additional session management,
Hunter Protocol integration, and performance monitoring.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, update
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta, timezone
import logging
import json

from app.db_models import User, ProxySource, Proxy, CandidateSource
from app.db_storage import DatabaseStorage

logger = logging.getLogger(__name__)


class ExtendedDatabaseStorage(DatabaseStorage):
    """Extended storage with enhanced scraping session management and monitoring."""

    async def create_scraping_session(
        self,
        session: AsyncSession,
        source_id: int,
        scraping_type: str = "scheduled",
        config: Optional[Dict] = None,
        initiated_by: Optional[int] = None,
    ) -> Dict:
        """Create a new scraping session record."""

        from app.db_models import ScrapingSession

        scraping_session = ScrapingSession(
            source_id=source_id,
            scraping_type=scraping_type,
            status="running",
            config=config or {},
            initiated_by=initiated_by,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        session.add(scraping_session)
        await session.commit()
        await session.refresh(scraping_session)

        return {
            "session_id": scraping_session.id,
            "status": scraping_session.status,
            "started_at": scraping_session.started_at,
        }

    async def update_scraping_session(
        self,
        session: AsyncSession,
        session_id: int,
        status: str,
        proxies_found: int = 0,
        proxies_valid: int = 0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Update scraping session status and results."""
        from app.db_models import ScrapingSession

        try:
            stmt = (
                update(ScrapingSession)
                .where(ScrapingSession.id == session_id)
                .values(
                    status=status,
                    proxies_found=proxies_found,
                    proxies_valid=proxies_valid,
                    error_message=error_message,
                    metadata=metadata or {},
                    finished_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    if status in ["completed", "failed"]
                    else None,
                )
            )

            await session.execute(stmt)
            await session.commit()
            return True

        except Exception as e:
            logger.error(f"Error updating scraping session {session_id}: {e}")
            await session.rollback()
            return False

    async def get_scraping_sessions(
        self,
        session: AsyncSession,
        source_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict], int]:
        """Get scraping sessions with filtering."""
        from app.db_models import ScrapingSession

        query = select(ScrapingSession).options(selectinload(ScrapingSession.source))

        if source_id:
            query = query.where(ScrapingSession.source_id == source_id)
        if status:
            query = query.where(ScrapingSession.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar()

        query = (
            query.order_by(desc(ScrapingSession.started_at)).limit(limit).offset(offset)
        )
        result = await session.execute(query)
        sessions = result.scalars().all()

        sessions_data = []
        for s in sessions:
            sessions_data.append(
                {
                    "id": s.id,
                    "source_id": s.source_id,
                    "source_name": s.source.name if s.source else "Unknown",
                    "scraping_type": s.scraping_type,
                    "status": s.status,
                    "proxies_found": s.proxies_found,
                    "proxies_valid": s.proxies_valid,
                    "started_at": s.started_at,
                    "finished_at": s.finished_at,
                    "error_message": s.error_message,
                    "config": s.config,
                }
            )

        return sessions_data, total

    async def get_scraping_stats(
        self,
        session: AsyncSession,
        days: int = 7,
    ) -> Dict:
        """Get scraping statistics for the last N days."""
        from app.db_models import ScrapingSession

        since_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

        status_stats = await session.execute(
            select(
                ScrapingSession.status,
                func.count(ScrapingSession.id).label("count"),
            )
            .where(ScrapingSession.started_at >= since_date)
            .group_by(ScrapingSession.status)
        )

        status_counts = {}
        for row in status_stats:
            status_counts[row.status] = row.count

        daily_stats = await session.execute(
            select(
                func.date(ScrapingSession.started_at).label("date"),
                func.count(ScrapingSession.id).label("sessions"),
                func.sum(ScrapingSession.proxies_found).label("proxies_found"),
                func.sum(ScrapingSession.proxies_valid).label("proxies_valid"),
            )
            .where(ScrapingSession.started_at >= since_date)
            .group_by(func.date(ScrapingSession.started_at))
            .order_by(desc(func.date(ScrapingSession.started_at)))
        )

        daily_data = []
        for row in daily_stats:
            daily_data.append(
                {
                    "date": row.date.isoformat(),
                    "sessions": row.sessions or 0,
                    "proxies_found": row.proxies_found or 0,
                    "proxies_valid": row.proxies_valid or 0,
                }
            )

        total_completed = status_counts.get("completed", 0) + status_counts.get(
            "failed", 0
        )
        success_rate = (
            (status_counts.get("completed", 0) / total_completed * 100)
            if total_completed > 0
            else 0
        )

        return {
            "period_days": days,
            "status_counts": status_counts,
            "daily_stats": daily_data,
            "success_rate": round(success_rate, 2),
            "total_sessions": sum(status_counts.values()),
        }

    async def create_hunter_candidate(
        self,
        session: AsyncSession,
        url: str,
        discovery_method: str,
        confidence_score: int = 0,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create a new Hunter candidate source."""
        from urllib.parse import urlparse

        domain = urlparse(url).netloc

        existing = await session.execute(
            select(CandidateSource).where(CandidateSource.url == url)
        )
        if existing.scalar_one_or_none():
            return {"error": "Candidate already exists"}

        candidate = CandidateSource(
            url=url,
            domain=domain,
            discovery_method=discovery_method,
            confidence_score=confidence_score,
            metadata=metadata or {},
        )

        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)

        return {
            "id": candidate.id,
            "url": candidate.url,
            "domain": candidate.domain,
            "discovery_method": candidate.discovery_method,
            "confidence_score": candidate.confidence_score,
            "status": candidate.status,
        }

    async def update_hunter_candidate(
        self,
        session: AsyncSession,
        candidate_id: int,
        status: Optional[str] = None,
        confidence_score: Optional[int] = None,
        proxies_found: Optional[int] = None,
        fail_count: Optional[int] = None,
    ) -> bool:
        """Update Hunter candidate status and metrics."""
        try:
            update_data = {}
            if status is not None:
                update_data["status"] = status
                if status in ["approved", "rejected"]:
                    update_data["last_checked_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
            if confidence_score is not None:
                update_data["confidence_score"] = confidence_score
            if proxies_found is not None:
                update_data["proxies_found_count"] = proxies_found
            if fail_count is not None:
                update_data["fail_count"] = fail_count

            if not update_data:
                return False

            stmt = (
                update(CandidateSource)
                .where(CandidateSource.id == candidate_id)
                .values(**update_data)
            )

            await session.execute(stmt)
            await session.commit()
            return True

        except Exception as e:
            logger.error(f"Error updating hunter candidate {candidate_id}: {e}")
            await session.rollback()
            return False

    async def get_hunter_statistics(
        self,
        session: AsyncSession,
        days: int = 30,
    ) -> Dict:
        """Get Hunter protocol statistics and performance metrics."""
        since_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

        status_stats = await session.execute(
            select(
                CandidateSource.status,
                func.count(CandidateSource.id).label("count"),
                func.avg(CandidateSource.confidence_score).label("avg_confidence"),
            )
            .where(CandidateSource.created_at >= since_date)
            .group_by(CandidateSource.status)
        )

        status_data = {}
        for row in status_stats:
            status_data[row.status] = {
                "count": row.count,
                "avg_confidence": round(row.avg_confidence or 0, 2),
            }

        method_stats = await session.execute(
            select(
                CandidateSource.discovery_method,
                func.count(CandidateSource.id).label("count"),
                func.avg(CandidateSource.proxies_found_count).label("avg_proxies"),
            )
            .where(CandidateSource.created_at >= since_date)
            .group_by(CandidateSource.discovery_method)
        )

        method_data = {}
        for row in method_stats:
            method_data[row.discovery_method] = {
                "count": row.count,
                "avg_proxies": round(row.avg_proxies or 0, 2),
            }

        top_domains = await session.execute(
            select(
                CandidateSource.domain,
                func.count(CandidateSource.id).label("candidates"),
                func.sum(CandidateSource.proxies_found_count).label("total_proxies"),
            )
            .where(CandidateSource.created_at >= since_date)
            .group_by(CandidateSource.domain)
            .having(func.count(CandidateSource.id) >= 2)
            .order_by(desc(func.sum(CandidateSource.proxies_found_count)))
            .limit(10)
        )

        domain_data = []
        for row in top_domains:
            domain_data.append(
                {
                    "domain": row.domain,
                    "candidates": row.candidates,
                    "total_proxies": row.total_proxies or 0,
                    "avg_proxies_per_candidate": round(
                        (row.total_proxies or 0) / row.candidates, 2
                    ),
                }
            )

        total_processed = sum(
            data["count"]
            for status, data in status_data.items()
            if status in ["approved", "rejected"]
        )
        approved_count = status_data.get("approved", {}).get("count", 0)
        approval_rate = (
            (approved_count / total_processed * 100) if total_processed > 0 else 0
        )

        return {
            "period_days": days,
            "status_stats": status_data,
            "method_stats": method_data,
            "top_domains": domain_data,
            "approval_rate": round(approval_rate, 2),
            "total_candidates": sum(data["count"] for data in status_data.values()),
        }

    async def batch_process_proxies_with_rate_limit(
        self,
        session: AsyncSession,
        proxies_data: List[Dict],
        source_id: Optional[int] = None,
        rate_limit_per_second: int = 10,
        batch_size: int = 50,
    ) -> Dict:
        """Process proxies with rate limiting and detailed progress tracking."""
        import asyncio
        import time

        if not proxies_data:
            return {"processed": 0, "success": 0, "failed": 0, "errors": []}

        processed = 0
        success = 0
        failed = 0
        errors = []
        start_time = time.time()

        for i in range(0, len(proxies_data), batch_size):
            batch = proxies_data[i : i + batch_size]
            batch_start = time.time()

            for proxy_data in batch:
                try:
                    result = await self.add_proxy_with_validation(
                        session, proxy_data, source_id
                    )
                    if result:
                        success += 1
                    else:
                        failed += 1
                        errors.append(
                            f"Failed to add proxy: {proxy_data.get('url', 'unknown')}"
                        )

                    processed += 1

                    await asyncio.sleep(1.0 / rate_limit_per_second)

                except Exception as e:
                    failed += 1
                    errors.append(f"Error processing proxy: {str(e)}")
                    processed += 1

            batch_time = time.time() - batch_start
            expected_batch_time = len(batch) / rate_limit_per_second
            if batch_time < expected_batch_time:
                await asyncio.sleep(expected_batch_time - batch_time)

        total_time = time.time() - start_time
        actual_rate = processed / total_time if total_time > 0 else 0

        return {
            "processed": processed,
            "success": success,
            "failed": failed,
            "errors": errors[:10],
            "total_time_seconds": round(total_time, 2),
            "actual_rate_per_second": round(actual_rate, 2),
            "target_rate_per_second": rate_limit_per_second,
        }

    async def get_performance_metrics(
        self,
        session: AsyncSession,
        days: int = 7,
    ) -> Dict:
        """Get comprehensive performance metrics."""
        since_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

        validation_metrics = await session.execute(
            select(
                func.avg(Proxy.latency_ms).label("avg_latency"),
                func.min(Proxy.latency_ms).label("min_latency"),
                func.max(Proxy.latency_ms).label("max_latency"),
                func.count(Proxy.id).label("total_validated"),
            )
            .where(Proxy.validation_status == "validated")
            .where(Proxy.last_validated >= since_date)
        )

        val_row = validation_metrics.first()

        quality_dist = await session.execute(
            select(
                Proxy.quality_score,
                func.count(Proxy.id).label("count"),
            )
            .where(Proxy.validation_status == "validated")
            .where(Proxy.last_validated >= since_date)
            .group_by(Proxy.quality_score)
            .order_by(Proxy.quality_score)
        )

        quality_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        for row in quality_dist:
            score = row.quality_score or 0
            if score <= 20:
                quality_buckets["0-20"] += row.count
            elif score <= 40:
                quality_buckets["21-40"] += row.count
            elif score <= 60:
                quality_buckets["41-60"] += row.count
            elif score <= 80:
                quality_buckets["61-80"] += row.count
            else:
                quality_buckets["81-100"] += row.count

        protocol_dist = await session.execute(
            select(
                Proxy.protocol,
                func.count(Proxy.id).label("count"),
            )
            .where(Proxy.validation_status == "validated")
            .where(Proxy.last_validated >= since_date)
            .group_by(Proxy.protocol)
            .order_by(desc(func.count(Proxy.id)))
        )

        protocol_data = {}
        for row in protocol_dist:
            protocol_data[row.protocol or "unknown"] = row.count

        country_dist = await session.execute(
            select(
                Proxy.country_code,
                func.count(Proxy.id).label("count"),
            )
            .where(Proxy.validation_status == "validated")
            .where(Proxy.last_validated >= since_date)
            .where(Proxy.country_code.isnot(None))
            .group_by(Proxy.country_code)
            .order_by(desc(func.count(Proxy.id)))
            .limit(10)
        )

        country_data = []
        for row in country_dist:
            country_data.append(
                {
                    "country_code": row.country_code,
                    "count": row.count,
                }
            )

        return {
            "period_days": days,
            "validation_performance": {
                "avg_latency_ms": round(val_row.avg_latency or 0, 2),
                "min_latency_ms": val_row.min_latency or 0,
                "max_latency_ms": val_row.max_latency or 0,
                "total_validated": val_row.total_validated or 0,
            },
            "quality_distribution": quality_buckets,
            "protocol_distribution": protocol_data,
            "top_countries": country_data,
        }

    async def create_background_task(
        self,
        session: AsyncSession,
        task_type: str,
        task_data: Dict,
        scheduled_for: Optional[datetime] = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> Dict:
        """Create a background task record."""
        from app.db_models import BackgroundTask

        task = BackgroundTask(
            task_type=task_type,
            task_data=task_data,
            status="pending",
            scheduled_for=scheduled_for or datetime.now(timezone.utc).replace(tzinfo=None),
            retry_count=retry_count,
            max_retries=max_retries,
        )

        session.add(task)
        await session.commit()
        await session.refresh(task)

        return {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "scheduled_for": task.scheduled_for,
        }

    async def update_background_task(
        self,
        session: AsyncSession,
        task_id: int,
        status: str,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update background task status and results."""
        from app.db_models import BackgroundTask

        try:
            task = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task_obj = task.scalar_one_or_none()

            if not task_obj:
                return False

            update_data = {
                "status": status,
                "completed_at": datetime.now(timezone.utc).replace(tzinfo=None)
                if status in ["completed", "failed"]
                else None,
            }

            if result:
                update_data["result"] = result
            if error_message:
                update_data["error_message"] = error_message
                update_data["retry_count"] = task_obj.retry_count + 1

            stmt = (
                update(BackgroundTask)
                .where(BackgroundTask.id == task_id)
                .values(**update_data)
            )

            await session.execute(stmt)
            await session.commit()
            return True

        except Exception as e:
            logger.error(f"Error updating background task {task_id}: {e}")
            await session.rollback()
            return False

    async def get_pending_background_tasks(
        self,
        session: AsyncSession,
        task_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Get pending background tasks for execution."""
        from app.db_models import BackgroundTask

        query = select(BackgroundTask).where(
            and_(
                BackgroundTask.status == "pending",
                BackgroundTask.scheduled_for <= datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        if task_type:
            query = query.where(BackgroundTask.task_type == task_type)

        query = query.order_by(BackgroundTask.scheduled_for).limit(limit)
        result = await session.execute(query)
        tasks = result.scalars().all()

        tasks_data = []
        for task in tasks:
            tasks_data.append(
                {
                    "id": task.id,
                    "task_type": task.task_type,
                    "task_data": task.task_data,
                    "scheduled_for": task.scheduled_for,
                    "retry_count": task.retry_count,
                    "max_retries": task.max_retries,
                }
            )

        return tasks_data


extended_db_storage = ExtendedDatabaseStorage()
