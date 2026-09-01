from fastapi import APIRouter, Response, status

from app.core.database import DatabaseError, check_database_connection
from app.schemas.database import DatabaseHealthResponse

router = APIRouter(tags=["database"])


@router.get("/database/health", response_model=DatabaseHealthResponse)
def database_health(response: Response) -> DatabaseHealthResponse:
    """Report SQL Server connectivity without exposing infrastructure details."""
    try:
        check_database_connection()
    except DatabaseError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return DatabaseHealthResponse(status="unavailable")
    return DatabaseHealthResponse(status="ok")
