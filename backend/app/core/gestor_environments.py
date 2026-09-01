from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from app.core.config import (
    AppEnvironment,
    FileSettings,
    GestorDataEnvironment,
    Settings,
)
from app.core.database import (
    DatabaseError,
    get_database_config,
    is_database_driver_available,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
HML_ENV_FILE = BACKEND_ROOT / ".env"
PRD_ENV_FILE = BACKEND_ROOT / ".env.prd"


class GestorDataEnvironmentUnavailableError(RuntimeError):
    """Safe error for a missing or disabled Gestor datasource."""


def _load_file_settings(path: Path) -> Settings:
    if not path.is_file():
        raise GestorDataEnvironmentUnavailableError(
            "Gestor data environment is unavailable."
        )
    try:
        return FileSettings(_env_file=path)
    except (OSError, ValidationError) as error:
        raise GestorDataEnvironmentUnavailableError(
            "Gestor data environment is unavailable."
        ) from error


@lru_cache
def get_hml_gestor_settings() -> Settings:
    return _load_file_settings(HML_ENV_FILE)


@lru_cache
def get_prd_gestor_settings() -> Settings:
    return _load_file_settings(PRD_ENV_FILE)


def _validate_sql_settings(
    settings: Settings,
    environment: GestorDataEnvironment,
) -> Settings:
    expected = (
        AppEnvironment.HML
        if environment is GestorDataEnvironment.HML
        else AppEnvironment.PRD
    )
    if settings.app_env is not expected:
        raise GestorDataEnvironmentUnavailableError(
            "Gestor data environment is unavailable."
        )
    if (
        environment is GestorDataEnvironment.PRD
        and not settings.gestor_prd_read_only_validation
    ):
        raise GestorDataEnvironmentUnavailableError(
            "Gestor data environment is unavailable."
        )
    try:
        get_database_config(settings)
    except DatabaseError as error:
        raise GestorDataEnvironmentUnavailableError(
            "Gestor data environment is unavailable."
        ) from error
    if (
        settings.db_protheus_table_suffix is None
        or not is_database_driver_available(settings)
    ):
        raise GestorDataEnvironmentUnavailableError(
            "Gestor data environment is unavailable."
        )
    return settings


def get_gestor_data_settings(environment: GestorDataEnvironment) -> Settings:
    if environment is GestorDataEnvironment.DEV:
        raise GestorDataEnvironmentUnavailableError(
            "DEV does not use SQL settings."
        )
    settings = (
        get_hml_gestor_settings()
        if environment is GestorDataEnvironment.HML
        else get_prd_gestor_settings()
    )
    return _validate_sql_settings(settings, environment)


def is_gestor_data_environment_available(
    environment: GestorDataEnvironment,
) -> bool:
    if environment is GestorDataEnvironment.DEV:
        return True
    try:
        get_gestor_data_settings(environment)
    except GestorDataEnvironmentUnavailableError:
        return False
    return True
