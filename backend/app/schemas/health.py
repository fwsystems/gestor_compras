from typing import Literal

from pydantic import BaseModel

from app.core.config import AppEnvironment


class HealthResponse(BaseModel):
    status: Literal["ok"]
    application: str
    environment: AppEnvironment
    version: str
