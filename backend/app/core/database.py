import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

import pyodbc

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Base exception that is safe to handle without exposing connection data."""


class DatabaseConfigurationError(DatabaseError):
    """Raised when a SQL Server connection is requested without complete settings."""


class DatabaseConnectionError(DatabaseError):
    """Raised when SQL Server connectivity or its technical query fails."""


@dataclass(frozen=True)
class DatabaseConnectionConfig:
    driver: str
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)
    connect_timeout: int = 5
    query_timeout: int = 30
    encrypt: bool = True
    trust_server_certificate: bool = False
    application_intent_read_only: bool = False


def get_database_config(settings: Settings | None = None) -> DatabaseConnectionConfig:
    current_settings = settings or get_settings()
    driver = current_settings.db_driver
    host = current_settings.db_host
    database = current_settings.db_name
    user = current_settings.db_user
    password = current_settings.db_password
    required_values = {
        "DB_DRIVER": driver,
        "DB_HOST": host,
        "DB_NAME": database,
        "DB_USER": user,
        "DB_PASSWORD": password,
    }
    missing = [name for name, value in required_values.items() if not value or not value.strip()]

    if missing:
        logger.warning(
            "SQL Server configuration incomplete environment=%s",
            current_settings.app_env.value,
        )
        raise DatabaseConfigurationError("SQL Server configuration is incomplete.")

    assert driver is not None
    assert host is not None
    assert database is not None
    assert user is not None
    assert password is not None

    return DatabaseConnectionConfig(
        driver=driver.strip(),
        host=host.strip(),
        port=current_settings.db_port,
        database=database.strip(),
        user=user.strip(),
        password=password,
        connect_timeout=current_settings.db_connect_timeout,
        query_timeout=current_settings.db_query_timeout,
        encrypt=current_settings.db_encrypt,
        trust_server_certificate=current_settings.db_trust_server_certificate,
        application_intent_read_only=current_settings.db_application_intent_read_only,
    )


def _odbc_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def build_connection_string(config: DatabaseConnectionConfig) -> str:
    parts = [
        f"DRIVER={_odbc_value(config.driver)}",
        f"SERVER={_odbc_value(f'{config.host},{config.port}')}",
        f"DATABASE={_odbc_value(config.database)}",
        f"UID={_odbc_value(config.user)}",
        f"PWD={_odbc_value(config.password)}",
        f"Encrypt={'yes' if config.encrypt else 'no'}",
        "TrustServerCertificate="
        f"{'yes' if config.trust_server_certificate else 'no'}",
    ]
    if config.application_intent_read_only:
        parts.append("ApplicationIntent=ReadOnly")
    return ";".join(parts)


@contextmanager
def get_database_connection(
    settings: Settings | None = None,
) -> Iterator[pyodbc.Connection]:
    config = get_database_config(settings)
    connection: pyodbc.Connection | None = None

    try:
        connection = pyodbc.connect(
            build_connection_string(config),
            timeout=config.connect_timeout,
            autocommit=True,
        )
        connection.timeout = config.query_timeout
        logger.info("SQL Server connection succeeded")
        yield connection
    except pyodbc.Error as error:
        logger.warning("SQL Server connection failed")
        raise DatabaseConnectionError("SQL Server is unavailable.") from error
    finally:
        if connection is not None:
            connection.close()


def check_database_connection(settings: Settings | None = None) -> None:
    """Run only the minimal technical query required to validate connectivity."""
    with get_database_connection(settings) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result is None or result[0] != 1:
                raise DatabaseConnectionError("SQL Server validation failed.")
        except pyodbc.Error as error:
            logger.warning("SQL Server validation query failed")
            raise DatabaseConnectionError("SQL Server is unavailable.") from error
        finally:
            cursor.close()


def is_database_driver_available(settings: Settings | None = None) -> bool:
    """Check the configured driver name without exposing infrastructure values."""
    current_settings = settings or get_settings()
    driver = current_settings.db_driver
    return bool(driver and driver.strip() in pyodbc.drivers())
