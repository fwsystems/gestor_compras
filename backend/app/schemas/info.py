from pydantic import BaseModel

from app.core.config import AppEnvironment


class ApplicationInfoResponse(BaseModel):
    application: str
    environment: AppEnvironment
    version: str
