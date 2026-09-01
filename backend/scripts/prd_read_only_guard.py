from app.core.config import AppEnvironment, Settings
from app.core.database import (
    get_database_config,
    is_database_driver_available,
)


class PrdReadOnlyValidationError(RuntimeError):
    """Safe error raised before any controlled PRD access."""


class InvalidPrdValidationEnvironmentError(PrdReadOnlyValidationError):
    pass


class PrdReadOnlyValidationDisabledError(PrdReadOnlyValidationError):
    pass


class IncompletePrdConfigurationError(PrdReadOnlyValidationError):
    pass


def validate_prd_read_only_settings(settings: Settings) -> None:
    """Validate the PRD opt-in and local prerequisites without connecting."""
    if settings.app_env is not AppEnvironment.PRD:
        raise InvalidPrdValidationEnvironmentError(
            "PRD validation is allowed only when APP_ENV is prd."
        )
    if not settings.gestor_prd_read_only_validation:
        raise PrdReadOnlyValidationDisabledError(
            "PRD read-only validation is disabled."
        )
    get_database_config(settings)
    if settings.db_protheus_table_suffix is None:
        raise IncompletePrdConfigurationError(
            "PRD table suffix configuration is incomplete."
        )
    if not is_database_driver_available(settings):
        raise IncompletePrdConfigurationError(
            "The configured ODBC driver is not installed."
        )
