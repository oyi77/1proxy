"""
Advanced Scheduling untuk Enhanced Scraping

Implementasi jadwal otomatis untuk scraping otomatis
dengan kontrol waktu, retry logic, dan resource optimization.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, time, timedelta
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.database import get_db
from app.dependencies import require_admin
from app.db_storage import db_storage


logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """Jenis jadwal scraping"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"
    RUN_NOW = "run_now"


class ScheduleEntry(BaseModel):
    """Entry jadwal scraping"""
    hour: int = Field(None, ge=0, le=23, description="Jam (0-23)")
    minute: int = Field(None, ge=0, le=59, description="Menit (0-59)")
    cron_expression: str = Field(None, description="Cron expression")
    timezone: str = Field("UTC", description="Timezone")
    enabled: bool = Field(True, description="Apakah jadwal aktif?")
    weekdays: List[str] = Field(default=["mon", "tue", "wed", "thu", "fri", "sat", "sun"], description="Hari aktif (default: Senin-Sabtu)")
    max_concurrent_tasks: int = Field(5, description="Maksimal concurrent tasks")


class ScrapingSchedule(BaseModel):
    """Konfigurasi jadwal scraping"""
    enabled: bool = Field(False, description="Enable scheduling")
    default_timezone: str = Field("UTC", description="Default timezone")
    entries: List[ScheduleEntry] = Field(default_factory=list)
    
    def validate(self) -> List[str]:
        """Validasi jadwal"""
        errors = []
        
        if not self.enabled:
            return ["Scheduling tidak diaktifkan"]
        
        for entry in self.entries:
            if entry.cron_expression and not self._validate_cron_expression(entry.cron_expression):
                errors.append(f"Invalid cron expression: {entry.cron_expression}")
            
            if entry.hour and (entry.hour < 0 or entry.hour > 23):
                errors.append(f"Invalid hour: {entry.hour}. Harus 0-23")
            
            if entry.minute and (entry.minute < 0 or entry.minute > 59):
                errors.append(f"Invalid minute: {entry.minute}. Harus 0-59")
            
            if entry.weekdays and not all(day in entry.weekdays for day in entry.weekdays):
                errors.append(f"Invalid weekday: {entry.weekdays}. Harus: {entry.weekdays}")
            
            if entry.timezone and entry.timezone != "UTC":
                try:
                    import pytz
                    pytz.timezone(entry.timezone)
                except Exception:
                    errors.append(f"Invalid timezone: {entry.timezone}")
        
        return errors if errors else None


class ScheduledJob:
    """Tugas jadwal yang dijadwalkal"""
    def __init__(
        self,
        job_id: str,
        schedule: ScrapingScheduleEntry,
        source_config: Dict[str, Any],
        scraper_service,
        background_tasks
    ):
        self.job_id = job_id
        self.schedule = schedule
        self.source_config = source_config
        self.scraper_service = scraper_service
        self.background_tasks = background_tasks
        self.background_job = None
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.is_running = False
        
    async def calculate_next_run(self) -> datetime:
        """Hitung waktu eksekusi berikutnya"""
        now = datetime.now()
        
        if self.schedule.schedule_type == ScheduleType.HOURLY:
            # Next run at next hour
            next_run = now.replace(hour=self.schedule.hour, minute=0, second=0, microsecond=0)
            while next_run <= now:
                next_run += timedelta(hours=1)
        elif self.schedule.schedule_type == ScheduleType.DAILY:
            # Next run at same time tomorrow
            next_run = (now + timedelta(days=1)).replace(hour=self.schedule.hour, minute=self.schedule.minute, second=0, microsecond=0)
        elif self.schedule.schedule_type == ScheduleType.WEEKLY:
            # Next run at same day next week
            days_ahead = (7 - now.weekday()) % 7
            next_run = (now + timedelta(days=days_ahead)).replace(hour=self.schedule.hour, minute=self.schedule.minute, second=0, microsecond=0)
        elif self.schedule_type == ScheduleType.MONTHLY:
            # Next run at same date next month
            next_run = (now + timedelta(days=30)).replace(day=1, hour=self.schedule.hour, minute=self.schedule.minute, second=0, microsecond=0)
        elif self.schedule_type == ScheduleType.RUN_NOW:
            next_run = now
        
        self.next_run = next_run
        return next_run
    
    async def is_time_to_run(self) -> bool:
        """Check if sudah waktunya menjalankan tugas"""
        now = datetime.now()
        return self.next_run <= now
    
    async def execute(self) -> Dict[str, Any]:
        """Eksekusi tugas jadwal"""
        if self.is_running:
            return {"status": "already_running", "message": "Task sedang berjalan"}
        
        try:
            self.is_running = True
            self.run_count += 1
            self.last_run = datetime.now()
            
            # Get scraping service for this specific job
            if self.job_id == "hunter_protocol":
                scraper_service = self.scraper_service
                job_func = scraper_service.run_hunter
            else:
                scraper_service = self.scraper_service
                job_func = scraper_service.run_scraping_session
            
            # Execute scraping
            result = await job_func(self.source_config)
            
            self.background_job = result
            
            self.is_running = False
            self.last_run = datetime.now()
            
            logger.info(f"Jadwal {self.job_id} dijalankan: {self.run_count}x ke-{self.run_count}x")
            
            return {
                "status": "success",
                "result": result,
                "run_count": self.run_count,
                "last_run": self.last_run.isoformat()
            }
        
        except Exception as e:
            self.is_running = False
            logger.error(f"Error menjalankan jadwal {self.job_id}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


class ScrapingScheduler:
    """Manager untuk menjalankan semua tugas jadwal scraping"""
    
    def __init__(self):
        self.jobs: Dict[str, ScheduledJob] = {}
        self.background_tasks = BackgroundTasks()
        self.scheduler_enabled = False
        
    def add_job(self, job_id: str, schedule: ScrapingScheduleEntry, source_config: Dict[str, Any], scraper_service) -> ScheduledJob:
        """Tambah tugas jadwal baru"""
        job = ScheduledJob(
            job_id=job_id,
            schedule=schedule,
            source_config=source_config,
            scraper_service=scraper_service,
            background_tasks=self.background_tasks
        )
        
        self.jobs[job_id] = job
        logger.info(f"Tugas {job_id} ditambahkan ke jadwal")
        
        # Start scheduler jika diaktifkan
        if not self.scheduler_enabled:
            await self.start_scheduler()
    
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """Hapus tugas jadwal"""
        if job_id in self.jobs:
            # Hentikan tugas jika sedang berjalan
            if self.jobs[job_id].is_running:
                return False
            
            # Cancel background task
            if self.jobs[job_id].background_job:
                self.background_tasks.cancel_task(self.jobs[job_id].background_job)
            
            del self.jobs[job_id]
            
            logger.info(f"Tugas {job_id} dihapus dari jadwal")
            return True
        
        return False
    
    async def start_scheduler(self):
        """Mulai penjadwalan tugas"""
        if self.scheduler_enabled:
            return {"status": "already_enabled"}
        
        self.scheduler_enabled = True
        logger.info("Scheduler started")
        
        # Mulai loop pengecekan setiap 5 menit
        while True:
            current_time = datetime.now()
            
            for job_id, job in list(self.jobs.items()):
                if job.is_time_to_run():
                    task_id = self.background_tasks.add_task(
                        job.execute(),
                        name=f"scheduled-{job_id}",
                        tags=[job_id, "scheduler"]
                    )
                    logger.info(f"Menjalankan tugas {job_id} pada {current_time.isoformat()}")
            
            # Tunggu sebelum cek berikutnya
            await asyncio.sleep(60)
    
    async def get_status(self) -> Dict[str, Any]:
        """Dapatkan status semua tugas jadwal"""
        jobs_status = {}
        
        for job_id, job in self.jobs.items():
            jobs_status[job_id] = {
                "schedule_type": job.schedule.schedule_type.value if job.schedule else "manual",
                "next_run": job.next_run.isoformat(),
                "last_run": job.last_run.isoformat(),
                "is_running": job.is_running,
                "run_count": job.run_count,
                "enabled": job.enabled
            }
        
        return {
            "scheduler_enabled": self.scheduler_enabled,
            "jobs": jobs_status,
            "total_jobs": len(self.jobs)
        }
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Dapatkan status tugas spesifik"""
        if job_id not in self.jobs:
            return {"status": "not_found", "message": f"Job {job_id} tidak ditemukan"}
        
        return self.jobs[job_id].get_status()
    
    async def run_job_now(self, job_id: str) -> Dict[str, Any]:
        """Jalankan tugas secara manual"""
        job = self.jobs[job_id]
        if job:
            return await job.execute()
        
        return {"status": "not_found", "message": f"Job {job_id} tidak ditemukan"}


# Background task startup
@router.on_event("startup")
async def startup_event():
    """Inisialisasi scheduler pada startup"""
    scheduler = ScrapingScheduler()
    await scheduler.start_scheduler()
    
    logger.info("Scraping scheduler initialized")


# Module extension untuk db_storage
async def create_scraping_session(
    db: AsyncSession,
    session_id: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    requests_made: int = 0,
    successful_requests: int = 0,
    failed_requests: int = 0,
    success_rate: float = 0.0,
    total_data_bytes: int = 0,
    avg_response_time: float = 0.0,
    proxies_used: List[str] = []
) -> str:
    """Buat sesi scraping baru di database"""
    
    try:
        session_record = await db_storage.create_scraping_session(
            db=db,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            requests_made=requests_made,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            total_data_bytes=total_data_bytes,
            proxies_used=proxies_used
        )
        
        return session_id
    
    except Exception as e:
        logger.error(f"Error creating scraping session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating scraping session: {str(e)}")


async def update_scraping_session(
    db: AsyncSession,
    session_id: str,
    end_time: datetime,
    requests_made: int,
    successful_requests: int,
    failed_requests: int,
    success_rate: float,
    total_data_bytes: int,
    proxies_used: List[str],
) -> str:
    """Update sesi scraping yang ada"""
    
    try:
        success = await db_storage.update_scraping_session(
            db=db,
            session_id=session_id,
            end_time=end_time,
            requests_made=requests_made,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            total_data_bytes=total_data_bytes,
            proxies_used=proxies_used
            proxies_tested=proxies_tested
        )
        
        return f"Sesi {session_id} berhasil diupdate"
    
    except Exception as e:
        logger.error(f"Error updating scraping session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating scraping session: {str(e)}")


async def validate_proxy_source(
    db: AsyncSession,
    source_id: int,
    background_tasks: BackgroundTasks,
) -> str:
    """Validasi dan test proxy source"""
    
    try:
        task_id = background_tasks.add_task(
            service.validate_proxy_source(db, source_id),
            name=f"validate-source-{source_id}"
        )
        
        return f"Validasi proxy source {source_id} dimulai"
    
    except Exception as e:
        logger.error(f"Error validating proxy source: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating proxy source: {str(e)}")