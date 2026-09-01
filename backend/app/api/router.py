from fastapi import APIRouter

from app.api.routes.database import router as database_router
from app.api.routes.gestor import router as gestor_router
from app.api.routes.info import router as info_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings

settings = get_settings()
api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(info_router, prefix=settings.api_prefix)
api_router.include_router(gestor_router, prefix=settings.api_prefix)
api_router.include_router(database_router, prefix=settings.api_prefix)
