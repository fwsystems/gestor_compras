from typing import Literal

from app.core.config import Settings
from app.core.database import DatabaseConfigurationError

ProtheusTable = Literal["SA2", "SC7", "SE2", "SED", "SE7", "SEV", "SZN", "SZR"]
_ALLOWED_TABLE_PREFIXES: frozenset[ProtheusTable] = frozenset(
    {"SA2", "SC7", "SE2", "SED", "SE7", "SEV", "SZN", "SZR"}
)


def get_protheus_table_name(table: ProtheusTable, settings: Settings) -> str:
    if table not in _ALLOWED_TABLE_PREFIXES:
        raise DatabaseConfigurationError("Unsupported Protheus table.")
    suffix = settings.db_protheus_table_suffix
    if suffix is None:
        raise DatabaseConfigurationError(
            "Protheus physical table suffix is not configured."
        )
    return f"{table}{suffix}"
