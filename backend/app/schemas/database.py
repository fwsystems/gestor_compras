from typing import Literal

from pydantic import BaseModel


class DatabaseHealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["sqlserver"] = "sqlserver"
