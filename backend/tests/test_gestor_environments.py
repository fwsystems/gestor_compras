from pathlib import Path

import pytest

from app.core.config import AppEnvironment, GestorDataEnvironment, Settings
from app.core import gestor_environments
from app.core.gestor_environments import (
    GestorDataEnvironmentUnavailableError,
    _load_file_settings,
    _validate_sql_settings,
    is_gestor_data_environment_available,
)


def sql_settings(
    environment: AppEnvironment,
    *,
    production_enabled: bool = False,
) -> Settings:
    return Settings(
        app_env=environment,
        db_host=f"sql-{environment.value}",
        db_port=1433,
        db_name="protheus",
        db_user="readonly",
        db_password="secret",
        db_driver="ODBC Driver 17 for SQL Server",
        db_protheus_table_suffix="010",
        gestor_prd_read_only_validation=production_enabled,
        _env_file=None,
    )


def test_data_environment_identifiers_are_stable() -> None:
    assert [environment.value for environment in GestorDataEnvironment] == [
        "dev",
        "hml",
        "prd",
    ]


def test_explicit_file_does_not_inherit_process_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment_file = tmp_path / ".env.hml"
    environment_file.write_text(
        "APP_ENV=hml\nDB_HOST=file-host\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_ENV", "prd")
    monkeypatch.setenv("DB_HOST", "process-host")

    settings = _load_file_settings(environment_file)

    assert settings.app_env is AppEnvironment.HML
    assert settings.db_host == "file-host"


@pytest.mark.parametrize(
    ("settings", "environment"),
    [
        (sql_settings(AppEnvironment.PRD, production_enabled=True), GestorDataEnvironment.HML),
        (sql_settings(AppEnvironment.HML), GestorDataEnvironment.PRD),
        (sql_settings(AppEnvironment.PRD), GestorDataEnvironment.PRD),
        (Settings(app_env=AppEnvironment.HML, _env_file=None), GestorDataEnvironment.HML),
    ],
)
def test_invalid_or_disabled_sql_environment_is_rejected(
    settings: Settings,
    environment: GestorDataEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gestor_environments, "is_database_driver_available", lambda _settings: True)

    with pytest.raises(GestorDataEnvironmentUnavailableError):
        _validate_sql_settings(settings, environment)


def test_valid_prd_requires_complete_config_flag_and_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = sql_settings(AppEnvironment.PRD, production_enabled=True)
    monkeypatch.setattr(gestor_environments, "is_database_driver_available", lambda _settings: True)

    assert _validate_sql_settings(settings, GestorDataEnvironment.PRD) is settings


def test_availability_is_safe_when_environment_cannot_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(_environment: GestorDataEnvironment) -> Settings:
        raise GestorDataEnvironmentUnavailableError("sensitive detail")

    monkeypatch.setattr(gestor_environments, "get_gestor_data_settings", unavailable)

    assert is_gestor_data_environment_available(GestorDataEnvironment.DEV) is True
    assert is_gestor_data_environment_available(GestorDataEnvironment.PRD) is False
