from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Report whether the API process is available."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        application=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
    )
