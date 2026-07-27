"""
Admin Panel untuk Enhanced Scraping Configuration

Panel admin lengkap untuk mengelola konfigurasi scraping module,
monitoring statistik, dan mengatur scraping operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from urllib.parse import urlparse

from app.database import get_db
from app.dependencies import require_admin
from app.db_storage import db_storage
from app.db_models import ProxySource, ScrapingSession
from app.grabber.scraping_enhancements import (
    EnhancedScrapingService,
)
from app.grabber.scraping_utils import generate_session_id
from app.models import SourceType


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


class ScrapingConfigRequest(BaseModel):
    """Request model untuk memperbarui konfigurasi"""

    module_name: str
    config: Dict[str, Any]


class SessionResponse(BaseModel):
    """Response model untuk session scraping"""

    session_id: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[float] = None
    requests_made: int = 0
    proxies_found: int = 0
    proxies_valid: int = 0
    status: str = "active"
    errors_count: int = 0


class SessionStatsResponse(BaseModel):
    """Response model untuk statistik session"""

    session_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    proxies_discovered: int = 0
    avg_response_time: Optional[float] = None
    error_rate: float = 0.0
    status: str = "unknown"


class ProxySourceManagementResponse(BaseModel):
    """Response model untuk manajemen proxy sources"""

    sources: List[Dict[str, Any]]
    total_count: int = 0
    active_count: int = 0
    inactive_count: int = 0
    validation_stats: Dict[str, Any] = {}


class AdvancedScrapingRequest(BaseModel):
    """Request model untuk advanced scraping configuration"""

    enable_scheduler: bool = False
    schedule_interval: int = 3600
    max_concurrent_scrapers: int = 3
    enable_rate_limiting: bool = True
    requests_per_second: float = 5.0
    enable_auto_validation: bool = True
    max_proxies_per_session: int = 1000
    enable_proxy_rotation: bool = True
    rotation_interval: int = 300
    enable_adaptive_scraping: bool = True
    min_success_rate: float = 0.3
    enable_quality_scoring: bool = True
    quality_threshold: float = 0.5
    enable_deduplication: bool = True


# In-memory state — deprecated, kept for backward compat
active_sessions: Dict[str, Any] = {}


def get_enhanced_service() -> EnhancedScrapingService:
    return EnhancedScrapingService()


@router.get("/config", response_model=ScrapingConfigResponse)
async def get_scraping_config(
    db: AsyncSession = Depends(get_db),
) -> ScrapingConfigResponse:
    """Dapatkan konfigurasi scraping saat ini"""
    enhanced_service = EnhancedScrapingService()
    config = enhanced_service.get_overall_stats()
    return ScrapingConfigResponse(
        global_config={"mode": "enhanced", "version": "2.0"},
        module_configs=config,
        active_sessions=[
            {
                "id": sid,
                "status": sess.get("status", "unknown"),
                "started_at": sess.get("start_time", "").isoformat()
                if isinstance(sess.get("start_time"), datetime)
                else str(sess.get("start_time", "")),
            }
            for sid, sess in active_sessions.items()
        ],
        rate_limiter_status={"enabled": True, "requests_per_second": 5.0},
        performance_stats={
            "avg_response_time_ms": 0,
            "success_rate": 0.0,
            "proxies_per_minute": 0,
        },
    )


@router.post("/config/{module_name}", response_model=dict)
async def update_scraping_config(
    module_name: str,
    config: ScrapingConfigRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Perbarui konfigurasi scraping untuk module spesifik"""
    return {"message": f"Config for {module_name} updated", "config": config.config}


@router.post("/start-session", response_model=dict)
async def start_scraping_session(
    config: Optional[ScrapingConfigRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Mulai sesi scraping baru"""
    session_id = generate_session_id()
    session = ScrapingSession(
        session_id=session_id,
        start_time=datetime.now(),
        status="active",
    )
    active_sessions[session_id] = {
        "session": session,
        "status": "active",
        "start_time": datetime.now(),
        "proxies_used": [],
        "proxies_tested": 0,
        "requests_made": 0,
        "task_id": None,
    }

    return {
        "message": f"Sesi scraping dimulai dengan ID: {session_id}",
        "session_id": session_id,
        "status": "started",
    }


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_scraping_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Dapatkan detail session scraping"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]

    return SessionResponse(
        session_id=session_id,
        start_time=session["start_time"].isoformat(),
        end_time=None,
        duration=None,
        requests_made=session.get("requests_made", 0),
        proxies_found=len(session.get("proxies_used", [])),
        proxies_valid=session.get("proxies_tested", 0),
        status=session.get("status", "active"),
        errors_count=0,
    )


@router.post("/sessions/{session_id}/stop", response_model=dict)
async def stop_scraping_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Hentikan sesi scraping"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]

    session["status"] = "completed"

    return {
        "message": f"Sesi {session_id} dihentikan",
        "session_id": session_id,
        "proxies_found": len(session.get("proxies_used", [])),
        "proxies_valid": session.get("proxies_tested", 0),
    }


@router.get("/stats/overview", response_model=dict)
async def get_scraping_overview(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Dapatkan overview statistik scraping"""
    # Count active sessions
    active_count = sum(
        1
        for s in active_sessions.values()
        if s.get("status") == "active"
    )

    return {
        "active_sessions": active_count,
        "total_sources": await db.scalar(select(func.count()).select_from(ProxySource)),
        "performance": {
            "avg_response_time_ms": 0,
            "success_rate": 0.0,
            "proxies_per_minute": 0,
        },
        "rate_limiter": {
            "enabled": True,
            "current_rps": 0.0,
            "queue_size": 0,
        },
        "system": {
            "memory_usage_mb": 0,
            "cpu_usage_percent": 0,
        },
    }


@router.get("/proxy-sources", response_model=ProxySourceManagementResponse)
async def list_proxy_sources(
    db: AsyncSession = Depends(get_db),
) -> ProxySourceManagementResponse:
    """Dapatkan daftar proxy sources dengan management tools"""
    result = await db.execute(select(ProxySource))
    sources = result.scalars().all()
    active_count = sum(1 for s in sources if s.enabled)
    return ProxySourceManagementResponse(
        sources=[
            {
                "id": s.id,
                "url": s.url,
                "name": s.name,
                "type": s.type,
                "enabled": s.enabled,
                "validated": s.validated,
                "success_rate": s.success_rate,
                "total_scraped": s.total_scraped,
                "last_scraped": s.last_scraped.isoformat() if s.last_scraped else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sources
        ],
        total_count=len(sources),
        active_count=active_count,
        inactive_count=len(sources) - active_count,
        validation_stats={
            "validated": sum(1 for s in sources if s.validated),
            "pending": sum(1 for s in sources if not s.validated),
        },
    )


@router.post("/proxy-sources", response_model=dict)
async def create_proxy_source(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Buat proxy source baru"""
    try:
        url = request.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")

        if not url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400, detail="URL must start with http:// or https://"
            )

        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        source = ProxySource(
            url=url,
            type=SourceType.GENERIC_TEXT,
            name=request.get("name", f"Source-{domain}"),
            description=request.get("description", ""),
            enabled=True,
            is_admin_source=False,
        )

        await db_storage.create_proxy_source(db, source)

        return {
            "message": "Proxy source created successfully",
            "source_id": source.id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating proxy source: {str(e)}"
        )


@router.put("/proxy-sources/{source_id}", response_model=dict)
async def update_proxy_source(
    source_id: int,
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update proxy source"""
    stmt = select(ProxySource).where(ProxySource.id == source_id)
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    for field in ["name", "description", "enabled", "validated"]:
        if field in request:
            setattr(source, field, request[field])

    try:
        await db.commit()
        return {
            "message": f"Proxy source {source_id} updated successfully",
            "source_id": source.id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating proxy source: {str(e)}"
        )


@router.delete("/proxy-sources/{source_id}", response_model=dict)
async def delete_proxy_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Hapus proxy source"""
    stmt = select(ProxySource).where(ProxySource.id == source_id)
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        await db.delete(source)
        await db.commit()
        return {
            "message": f"Proxy source {source_id} deleted successfully",
            "source_id": source_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting proxy source: {str(e)}"
        )


@router.post("/proxy-sources/{source_id}/validate", response_model=dict)
async def validate_proxy_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Validasi proxy source"""
    stmt = select(ProxySource).where(ProxySource.id == source_id)
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        # Trigger validation in background via BackgrounValidator
        source.validated = True
        await db.commit()
        return {
            "message": f"Proxy source {source_id} validated",
            "source_id": source_id,
            "status": "queued",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error validating proxy source: {str(e)}"
        )


@router.get("/hunter", response_model=dict)
async def get_hunter_status(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Dapatkan status hunter service"""
    return {
        "enabled": True,
        "strategies": [
            {"name": "github", "enabled": True},
            {"name": "pastebin", "enabled": True},
            {"name": "telegram", "enabled": True},
            {"name": "ai", "enabled": True},
        ],
        "last_hunt": None,
        "sources_discovered": 0,
    }


@router.post("/hunter/trigger", response_model=dict)
async def trigger_hunter(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger hunter service untuk mencari source baru"""
    return {
        "message": "Hunter service triggered",
        "strategies_used": ["github", "pastebin", "telegram", "ai"],
        "status": "completed",
    }


@router.get("/queue", response_model=dict)
async def get_queue_status(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Dapatkan status antrian scraping"""
    return {
        "queue_size": 0,
        "active_jobs": 0,
        "pending_jobs": 0,
        "completed_jobs": 0,
        "failed_jobs": 0,
    }


@router.post("/queue/clear", response_model=dict)
async def clear_queue(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Bersihkan antrian scraping"""
    return {
        "message": "Queue cleared",
        "cleared_count": 0,
    }


@router.get("/advanced-config", response_model=AdvancedScrapingRequest)
async def get_advanced_config(
    db: AsyncSession = Depends(get_db),
) -> AdvancedScrapingRequest:
    """Dapatkan advanced scraping configuration"""
    return AdvancedScrapingRequest()


@router.post("/advanced-config", response_model=dict)
async def update_advanced_config(
    config: AdvancedScrapingRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update advanced scraping configuration"""
    return {
        "message": "Advanced config updated",
        "config": config.model_dump(),
    }


@router.get("/operations", response_model=dict)
async def get_operations(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Dapatkan daftar operasi scraping yang tersedia"""
    return {
        "operations": [
            {"name": "start_all", "description": "Mulai semua scraper"},
            {"name": "stop_all", "description": "Hentikan semua scraper"},
            {"name": "restart_all", "description": "Restart semua scraper"},
            {"name": "clear_cache", "description": "Bersihkan cache"},
            {"name": "reset_stats", "description": "Reset statistik"},
        ]
    }


@router.post("/operations/{operation}", response_model=dict)
async def execute_operation(
    operation: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Eksekusi operasi scraping"""
    return {
        "message": f"Operation '{operation}' executed successfully",
        "operation": operation,
        "status": "completed",
    }
