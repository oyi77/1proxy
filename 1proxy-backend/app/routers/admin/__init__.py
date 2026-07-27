"""Admin API package — composed from domain-specific sub-routers."""

from fastapi import APIRouter, Depends
from app.dependencies import require_admin

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

from app.routers.admin.users import users_router
from app.routers.admin.sources import sources_router
from app.routers.admin.cleanup import cleanup_router
from app.routers.admin.stats import stats_router
from app.routers.admin.hunter import hunter_router

router.include_router(users_router)
router.include_router(sources_router)
router.include_router(cleanup_router)
router.include_router(stats_router)
router.include_router(hunter_router)
