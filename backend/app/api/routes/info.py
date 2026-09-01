from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.info import ApplicationInfoResponse

router = APIRouter(tags=["application"])


@router.get("/info", response_model=ApplicationInfoResponse)
def application_info() -> ApplicationInfoResponse:
    """Return public application metadata only."""
    settings = get_settings()
    return ApplicationInfoResponse(
        application=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
    )
