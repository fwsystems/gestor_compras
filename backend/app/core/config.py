from functools import lru_cache
from enum import Enum
import re
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class AppEnvironment(str, Enum):
    DEV = "dev"
    HML = "hml"
    PRD = "prd"


class GestorDataEnvironment(str, Enum):
    DEV = "dev"
    HML = "hml"
    PRD = "prd"


class Settings(BaseSettings):
    """Centralized application and future infrastructure settings."""

    app_name: str = "gestor-compras-web"
    app_env: AppEnvironment = AppEnvironment.DEV
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    debug: bool | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5193"])

    # Optional in DEV. Completeness is checked only when a connection is requested.
    db_host: str | None = None
    db_port: int = 1433
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_driver: str | None = None
    db_connect_timeout: int = Field(default=5, ge=1)
    db_query_timeout: int = Field(default=30, ge=1)
    db_encrypt: bool = True
    db_trust_server_certificate: bool = False
    db_application_intent_read_only: bool = False
    db_protheus_table_suffix: str | None = None
    gestor_prd_read_only_validation: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/") or normalized == "":
            raise ValueError("API_PREFIX must start with '/' and cannot be empty")
        return normalized

    @field_validator("debug", mode="before")
    @classmethod
    def parse_optional_debug(cls, value: Any) -> Any:
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
            return None
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
            if not origins:
                raise ValueError("CORS_ORIGINS must contain at least one origin")
            return origins
        return value

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_cors(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("CORS_ORIGINS cannot contain wildcard origins")
        return value

    @field_validator("db_protheus_table_suffix", mode="before")
    @classmethod
    def validate_protheus_table_suffix(cls, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        if normalized == "":
            return None
        if re.fullmatch(r"[A-Z0-9]{1,10}", normalized) is None:
            raise ValueError(
                "DB_PROTHEUS_TABLE_SUFFIX must contain only letters and numbers"
            )
        return normalized

    @model_validator(mode="after")
    def apply_environment_defaults(self) -> "Settings":
        if self.debug is None:
            self.debug = self.app_env is AppEnvironment.DEV
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


class FileSettings(Settings):
    """Settings loaded from one explicit file without process-env overrides."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        del settings_cls, env_settings, file_secret_settings
        return init_settings, dotenv_settings
