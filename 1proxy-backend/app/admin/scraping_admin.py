"""
Admin Panel untuk Enhanced Scraping Configuration

Panel admin lengkap untuk mengelola konfigurasi scraping module,
monitoring statistik, dan mengatur scraping operations.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel, Field
from fastapi import BackgroundTasks

from app.database import get_db
from app.dependencies import require_admin
from app.db_storage_extended import extended_db_storage
from app.db_models import ProxySource, User, ValidationHistory, ScrapingSession
from app.grabber.scraping_enhancements import (
    EnhancedScrapingService,
    ScrapingEnhancementConfig,
)
from app.grabber.scraping_utils import (
    RequestQueue,
    RateLimiter,
    ExponentialBackoff,
    ProxyRotator,
    calculate_proxy_score,
    format_bytes,
    generate_session_id,
)


router = APIRouter(
    prefix="/api/v1/admin/scraping",
    tags=["admin", "scraping"],
    dependencies=[Depends(require_admin), Depends(get_db)],
)


# Pydantic models untuk admin panel
class ScrapingConfigResponse(BaseModel):
    """Response model untuk scraping configuration"""

    global_config: Dict[str, Any]
    module_configs: Dict[str, Any]
    active_sessions: List[Dict[str, Any]]
    rate_limiter_status: Dict[str, Any]
    performance_stats: Dict[str, Any]
    performance_stats: Dict[str, Any]


class ScrapingConfigRequest(BaseModel):
    """Request model untuk memperbarui konfigurasi"""

    module_name: str
    settings: Dict[str, Any]


class SessionResponse(BaseModel):
    """Response model untuk session scraping"""

    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]
    requests_made: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    total_data_bytes: int
    avg_response_time: float
    proxies_used: List[str]
    proxies_tested: int


class SessionStatsResponse(BaseModel):
    """Response model untuk statistik session"""

    total_sessions: int
    active_sessions: int
    total_requests: int
    successful_requests: int
    avg_session_duration: float
    total_data_bytes: int
    success_rate: float


class ProxySourceManagementResponse(BaseModel):
    """Response model untuk manajemen proxy sources"""

    sources: List[Dict[str, Any]]
    total: int
    pending_approval: int
    auto_discovered: int


class AdvancedScrapingRequest(BaseModel):
    """Request model untuk advanced scraping configuration"""

    enable_scheduler: bool = False
    schedule: Optional[Dict[str, Any]] = None
    enable_proxy_testing: bool = False
    proxy_rotation_enabled: bool = False
    max_proxies_per_source: Optional[int] = None
    test_urls: Optional[List[str]] = None


# Background tasks
background_tasks = BackgroundTasks()


# Global scraping service instance
enhanced_service: Optional[EnhancedScrapingService] = None


def get_enhanced_service() -> EnhancedScrapingService:
    """Get atau buat enhanced scraping service instance"""
    global enhanced_service
    if not enhanced_service:
        default_config = ScrapingEnhancementConfig(
            enable_proxy_rotation=True,
            max_concurrent_requests=10,
            rate_limit_per_second=5,
            enable_retry=True,
            max_retries=3,
            timeout_seconds=30,
        )
        enhanced_service = EnhancedScrapingService(config=default_config)

    return enhanced_service


# Global session manager
active_sessions: Dict[str, ScrapingSession] = {}


@router.get("/scraping/config", response_model=ScrapingConfigResponse)
async def get_scraping_config() -> ScrapingConfigResponse:
    """Dapatkan konfigurasi scraping global dan per-module"""
    service = get_enhanced_service()

    # Get global config
    global_config = service.config_manager.get_global_config()

    # Get module configs
    module_configs = {}
    for module_name in ["github_grabber", "subscription_grabber", "advanced_grabber"]:
        module_configs[module_name] = service.config_manager.get_config(module_name)

    # Get active sessions
    global_sessions = {
        session_id: session_data.session_id
        for session_id, session_data in active_sessions.items()
    }

    # Get rate limiter status
    rate_limiter_status = service.config_manager.config.get("global", {})

    return ScrapingConfigResponse(
        global_config=global_config,
        module_configs=module_configs,
        active_sessions=global_sessions,
        rate_limiter_status=rate_limiter_status,
        performance_stats=service.performance_monitor.get_overall_stats()
        if service.performance_monitor
        else {},
    )


@router.post("/scraping/config/{module_name}", response_model=dict)
async def update_scraping_config(
    request: ScrapingConfigRequest,
    module_name: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Perbarui konfigurasi scraping untuk module spesifik"""
    service = get_enhanced_service()

    # Validate request
    if not module_name or module_name not in [
        "github_grabber",
        "subscription_grabber",
        "advanced_grabber",
    ]:
        raise HTTPException(status_code=400, detail="Invalid module name")

    # Validate settings
    for key, value in request.settings.items():
        if key not in [
            "max_concurrent_requests",
            "default_timeout",
            "max_retries",
            "retry_delay",
            "github_timeout",
            "github_max_retries",
            "subscription_timeout",
            "subscription_max_retries",
            "enable_base64_padding_fix",
            "supported_formats",
            "enable_batching",
            "batch_size",
            "min_proxy_quality",
            "enable_duplicate_filtering",
            "enable_user_agent_rotation",
            "enable_proxy_rotation",
            "max_proxies_per_source",
            "success_rate_threshold",
        ]:
            raise HTTPException(status_code=400, detail=f"Invalid setting: {key}")

    try:
        # Update konfigurasi
        success = await service.config_manager.update_config(
            module_name, request.settings
        )
        if not success:
            raise HTTPException(
                status_code=500, detail=f"Gagal memperbarui konfigurasi {module_name}"
            )

        return {
            "message": f"Konfigurasi {module_name} berhasil diperbarui",
            "success": True,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error memperbarui konfigurasi: {str(e)}"
        )


@router.post("/scraping/start-session", response_model=dict)
async def start_scraping_session(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Memulai sesi scraping baru"""

    service = get_enhanced_service()

    # Dapatkan konfigurasi
    module_configs = {}
    for module_name in ["github_grabber", "subscription_grabber", "advanced_grabber"]:
        module_configs[module_name] = service.config_manager.get_config(module_name)

    # Validasi input
    source_config = request.get("source_config", {})
    if not source_config:
        raise HTTPException(status_code=400, detail="Source config required")

    # Create session ID
    session_id = generate_session_id()
    session = ScrapingSession(session_id=session_id, start_time=datetime.now())

    # Create scraping session
    task_id = background_tasks.add_task(
        service.run_scraping_session(
            session=session, source_config=source_config, module_configs=module_configs
        ),
        name=f"scraping-session-{session_id[:8]}",
    )

    active_sessions[session_id] = session

    return {
        "message": f"Sesi scraping dimulai dengan ID: {session_id}",
        "session_id": session_id,
        "task_id": task_id,
    }


@router.get("/scraping/sessions/{session_id}", response_model=SessionResponse)
async def get_scraping_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Dapatkan detail sesi scraping"""
    service = get_enhanced_service()

    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]

    return SessionResponse(
        session_id=session_id,
        start_time=session.start_time.isoformat(),
        end_time=session.end_time.isoformat() if session.end_time else None,
        duration=(session.end_time - session.start_time).total_seconds()
        if session.end_time
        else None,
        requests_made=session.requests_made,
        successful_requests=session.successful_requests,
        failed_requests=session.failed_requests,
        success_rate=session.success_rate,
        total_data_bytes=session.total_data_bytes,
        avg_response_time=session.avg_response_time,
        proxies_used=session.proxies_used,
    )


@router.post("/scraping/sessions/{session_id}/stop", response_model=dict)
async def stop_scraping_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Hentikan sesi scraping"""
    service = get_enhanced_service()

    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]

    # Simpanikan background task
    task_id = session.task_id
    if task_id and background_tasks:
        background_tasks.cancel_task(task_id)

    # Mark session as ended
    session.end_time = datetime.now()

    # Update session data
    success = await extended_db_storage.update_scraping_session(
        session=db,
        session_id=session.session_id,
        status="completed",
        proxies_found=len(session.proxies_used),
        proxies_valid=session.proxies_tested,
    )

    # Remove dari aktif
    del active_sessions[session_id]

    return {"message": f"Sesi {session_id} dihentikan", "session_id": session_id}


@router.get("/scraping/stats/overview", response_model=dict)
async def get_scraping_overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Dapatkan statistik overview scraping"""
    service = get_enhanced_service()

    # Dapatkan statistik dari performance monitor
    overview_stats = service.performance_monitor.get_overall_stats()

    # Dapatkan statistik proxy sources
    total_sources = await db_storage.count_sources(db)
    hunter_stats = await extended_db_storage.get_hunter_statistics(db)
    pending_approval = hunter_stats.get("total_candidates", 0)

    total_sessions = 0

    total_proxies = await db_storage.count_proxies(db)
    validated_proxies = await db_storage.count_proxies(
        db, validation_status="validated"
    )

    return {
        "proxy_sources": {
            "total": total_sources,
            "auto_discovered": pending_approval,
            "manual": total_sources - pending_approval,
        },
        "sessions": {
            "total": total_sessions,
            "active": active_sessions,
            "completed": total_sessions - active_sessions,
        },
        "validation": {
            "total_proxies": total_proxies,
            "validated": validated_proxies,
            "validation_rate": (validated_proxies / total_proxies) * 100
            if total_proxies > 0
            else 0,
        },
        "performance": overview_stats,
    }


@router.get(
    "/scraping/stats/sessions/{session_id}", response_model=SessionStatsResponse
)
async def get_session_stats(session_id: str) -> SessionStatsResponse:
    """Dapatkan statistik detail sesi spesifik"""
    service = get_enhanced_service()

    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]

    # Calculate detailed statistics
    # Implementasi...
    session_start = session.start_time
    session_end = session.end_time or datetime.now()

    return SessionStatsResponse(
        session_id=session_id,
        start_time=session_start.isoformat(),
        end_time=session_end.isoformat(),
        duration=(session_end - session_start).total_seconds(),
        requests_made=session.requests_made,
        successful_requests=session.successful_requests,
        failed_requests=session.failed_requests,
        success_rate=session.success_rate,
        total_data_bytes=session.total_data_bytes,
        avg_response_time=session.avg_response_time,
        proxies_used=len(session.proxies_used) if session.proxies_used else 0,
    )


@router.get("/scraping/proxy-sources", response_model=ProxySourceManagementResponse)
async def get_proxy_sources(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> ProxySourceManagementResponse:
    """Dapatkan daftar proxy sources dengan management tools"""

    # Get proxy sources
    sources = await db_storage.get_sources(db, enabled_only=(status == "enabled"))

    if status == "pending":
        hunter_stats = await extended_db_storage.get_hunter_statistics(db)
        pending_approval = (
            hunter_stats.get("status_stats", {}).get("pending", {}).get("count", 0)
        )
    else:
        pending_approval = 0

    return ProxySourceManagementResponse(
        sources=[
            {
                "id": source.id,
                "url": source.url,
                "type": source.type.value,
                "name": source.name,
                "description": source.description,
                "enabled": source.enabled,
                "validated": source.validated,
                "validation_error": source.validation_error,
                "total_scraped": source.total_scraped,
                "success_rate": source.success_rate,
                "created_at": source.created_at.isoformat(),
                "updated_at": source.updated_at.isoformat(),
                "is_admin_source": source.is_admin_source,
                "candidate_id": source.candidate_id,
            }
            for source in sources
        ],
        total=len(sources),
        pending_approval=pending_approval,
    )


@router.post("/scraping/proxy-sources", response_model=dict)
async def create_proxy_source(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Tambah proxy source baru"""
    service = get_enhanced_service()

    try:
        # Validasi input
        if not request.get("url"):
            raise HTTPException(status_code=400, detail="URL is required")

        url = request.get("url")
        if not url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400, detail="URL must start with http:// or https://"
            )

        # Validasi URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        # Cek domain yang diblokir
        blocked_domains = ["example.com", "test.com"]
        if any(blocked in domain for blocked in blocked_domains):
            raise HTTPException(status_code=400, detail=f"Domain {domain} is blocked")

        source = ProxySource(
            url=url,
            type=SourceType.MANUAL,
            name=request.get("name", f"Source-{domain}"),
            description=request.get("description", ""),
            enabled=True,
            is_admin_source=False,
        )

        # Simpankan dengan database
        await db_storage.create_proxy_source(db, source)

        return {"message": "Proxy source created successfully", "source_id": source.id}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating proxy source: {str(e)}"
        )


@router.put("/scraping/proxy-sources/{source_id}", response_model=dict)
async def update_proxy_source(
    source_id: int,
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update proxy source"""
    service = get_enhanced_service()

    # Get existing source
    stmt = select(ProxySource).where(ProxySource.id == source_id)
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Update fields
    for field in ["name", "description", "enabled", "validated"]:
        if field in request:
            setattr(source, field, request[field])

    try:
        session.add(source)
        await session.commit()

        return {
            "message": f"Proxy source {source_id} updated successfully",
            "source_id": source.id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating proxy source: {str(e)}"
        )


@router.delete("/scraping/proxy-sources/{source_id}", response_model=dict)
async def delete_proxy_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Hapus proxy source"""
    service = get_enhanced_service()

    # Get existing source
    stmt = select(ProxySource).where(ProxySource.id == source_id)
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        await session.delete(source)
        await session.commit()

        return {
            "message": f"Proxy source {source_id} deleted successfully",
            "source_id": source_id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting proxy source: {str(e)}"
        )


@router.post("/scraping/proxy-sources/{source_id}/validate", response_model=dict)
async def validate_proxy_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Validasi proxy source"""
    service = get_enhanced_service()

    # Get existing source
    stmt = select(ProxySource).where(ProxySource.id == source_id)
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        # Trigger validation
        task_id = background_tasks.add_task(
            service.validate_proxy_source(db=db, source_id=source_id),
            name=f"validate-source-{source_id}",
        )

        return {
            "message": f"Validation started for proxy source {source_id}",
            "task_id": task_id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error starting validation: {str(e)}"
        )


@router.get("/scraping/hunter", response_model=dict)
async def get_hunter_status(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Dapatkan status Hunter Protocol"""
    service = get_enhanced_service()

    # Get Hunter statistics
    hunter_stats = await extended_db_storage.get_hunter_statistics(db)

    # Get active Hunter tasks
    active_tasks = background_tasks.list_tasks()

    return {
        "active_tasks": active_tasks,
        "statistics": hunter_stats,
        "candidates_found": hunter_stats.get("candidates_found", 0),
        "sources_approved": hunter_stats.get("sources_approved", 0),
        "approval_rate": hunter_stats.get("approval_rate", 0.0),
        "last_run": hunter_stats.get("last_run"),
    }


@router.post("/scraping/hunter/trigger", response_model=dict)
async def trigger_hunter_manual(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Manual trigger Hunter Protocol"""
    service = get_enhanced_service()

    try:
        task_id = background_tasks.add_task(
            service.run_hunter(),
            name=f"hunter-manual-trigger-{datetime.now().isoformat()}",
        )

        return {"message": "Hunter Protocol triggered manually", "task_id": task_id}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error triggering Hunter: {str(e)}"
        )


@router.get("/scraping/queue", response_model=dict)
async def get_request_queue(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Dapatkan antrian request queue"""
    service = get_enhanced_service()
    queue = service.request_queue

    return {
        "queue_size": queue.size(),
        "active_requests": len(queue.active_requests),
        "completed_requests": len(queue.completed_requests),
        "failed_requests": len(queue.failed_requests),
        "global_requests": queue.global_requests,
        "rate_limiter_stats": {
            "domain_requests": queue.limiter.domain_requests,
            "ip_requests": queue.limiter.ip_requests,
            "global_rate_limiting": queue.limiter.global_rate_limiting,
        },
    }


@router.post("/scraping/queue/clear", response_model=dict)
async def clear_request_queue(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Bersihkan antrian request queue"""
    service = get_enhanced_service()

    try:
        await service.request_queue.clear()

        return {"message": "Request queue cleared successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing queue: {str(e)}")


@router.get("/scraping/advanced-config", response_model=AdvancedScrapingRequest)
async def get_advanced_config() -> AdvancedScrapingRequest:
    """Dapatkan konfigurasi advanced scraping"""
    service = get_enhanced_service()

    config = service.config_manager.get_global_config()
    advanced_config = config.get("enhanced", {})

    return AdvancedScrapingRequest(
        enable_scheduler=advanced_config.get("enable_scheduler", False),
        schedule=advanced_config.get("schedule"),
        enable_proxy_testing=advanced_config.get("enable_proxy_testing", False),
        proxy_rotation_enabled=advanced_config.get("enable_proxy_rotation", False),
        max_proxies_per_source=advanced_config.get("max_proxies_per_source"),
        test_urls=advanced_config.get("test_urls", []),
    )


@router.post("/scraping/advanced-config", response_model=dict)
async def update_advanced_config(
    request: AdvancedScrapingRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Perbarui konfigurasi advanced scraping"""
    service = get_enhanced_service()

    try:
        success = await service.config_manager.update_config(
            "enhanced", request.settings
        )
        if not success:
            raise HTTPException(
                status_code=500, detail=f"Gagal memperbarui konfigurasi advanced"
            )

        return {"message": "Konfigurasi advanced berhasil diperbarui", "success": True}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error memperbarui konfigurasi advanced: {str(e)}"
        )


# Module: app/db_storage extension
@router.get("/scraping/operations", response_model=dict)
async def get_scraping_operations(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Dapatkan operasi scraping yang tersedia"""

    operations = {
        "validate_proxy_source": "validasi proxy source",
        "run_hunter_protocol": "jalankan Hunter Protocol",
        "start_scraping_session": "memulai sesi scraping",
        "stop_scraping_session": "hentikan sesi scraping",
        "manage_proxy_sources": "kelola proxy sources",
        "view_scraping_stats": "lihat statistik scraping",
        "advanced_configuration": "konfigurasi advanced",
        "queue_management": "kelola antrian request queue",
    }

    return operations


@router.post("/scraping/operations/{operation}", response_model=dict)
async def execute_operation(
    operation: str,
    params: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Eksekusi operasi scraping"""
    service = get_enhanced_service()

    try:
        if operation == "validate_proxy_source":
            return await validate_proxy_source(
                params["source_id"], db, background_tasks
            )
        elif operation == "run_hunter_protocol":
            return await trigger_hunter_manual(db, background_tasks)
        elif operation == "start_scraping_session":
            return await start_scraping_session(params, db, background_tasks)
        elif operation == "stop_scraping_session":
            return await stop_scraping_session(
                params["session_id"], db, background_tasks
            )
        elif operation == "clear_request_queue":
            return await clear_request_queue(db, background_tasks)
        else:
            raise HTTPException(
                status_code=400, detail=f"Invalid operation: {operation}"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error executing operation {operation}: {str(e)}"
        )
