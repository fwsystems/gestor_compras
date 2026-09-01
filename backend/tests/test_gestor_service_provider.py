import pytest

from app.core.config import AppEnvironment, GestorDataEnvironment, Settings
from app.core.gestor_environments import GestorDataEnvironmentUnavailableError
from app.services import gestor_service_provider
from app.services.gestor_service_provider import (
    GestorEnvironmentUnavailableError,
    MockGestorService,
    get_gestor_service,
)
from app.services.gestor_sql_service import GestorSqlService


def sql_settings(environment: AppEnvironment) -> Settings:
    return Settings(
        app_env=environment,
        db_host=f"sql-{environment.value}",
        db_port=1433,
        db_name="protheus",
        db_user="readonly",
        db_password="secret",
        db_driver="ODBC Driver 17 for SQL Server",
        protheus_table_suffix="010",
        gestor_prd_read_only_validation=(environment is AppEnvironment.PRD),
        _env_file=None,
    )


def test_dev_selects_mock_without_resolving_sql() -> None:
    resolved = False

    def resolver(_environment: GestorDataEnvironment) -> Settings:
        nonlocal resolved
        resolved = True
        return sql_settings(AppEnvironment.HML)

    service = get_gestor_service(GestorDataEnvironment.DEV, settings_resolver=resolver)

    assert isinstance(service, MockGestorService)
    assert resolved is False
    assert service.get_gestor("0101", 2025, 9).quantidade == 20


@pytest.mark.parametrize(
    ("data_environment", "app_environment"),
    [
        (GestorDataEnvironment.HML, AppEnvironment.HML),
        (GestorDataEnvironment.PRD, AppEnvironment.PRD),
    ],
)
def test_sql_environment_uses_its_isolated_settings(
    data_environment: GestorDataEnvironment,
    app_environment: AppEnvironment,
) -> None:
    settings = sql_settings(app_environment)

    service = get_gestor_service(
        data_environment,
        settings_resolver=lambda _environment: settings,
    )

    assert isinstance(service, GestorSqlService)
    assert service._repositories.natureza._settings is settings
    assert service._repositories.pc_aberto._settings is settings
    assert service._repositories.nf_entrada._settings is settings
    assert service._repositories.contingencia._settings is settings
    assert service._repositories.limite._settings is settings


def test_unavailable_environment_does_not_construct_sql_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed = False

    def sql_factory(*_args: object, **_kwargs: object) -> GestorSqlService:
        nonlocal constructed
        constructed = True
        return GestorSqlService()

    def unavailable(_environment: GestorDataEnvironment) -> Settings:
        raise GestorDataEnvironmentUnavailableError("sensitive configuration detail")

    monkeypatch.setattr(gestor_service_provider, "GestorSqlService", sql_factory)

    with pytest.raises(GestorEnvironmentUnavailableError):
        get_gestor_service(
            GestorDataEnvironment.PRD,
            settings_resolver=unavailable,
        )

    assert constructed is False


def test_hml_and_prd_services_coexist_without_global_mutation() -> None:
    hml_settings = sql_settings(AppEnvironment.HML)
    prd_settings = sql_settings(AppEnvironment.PRD)
    snapshots = (hml_settings.model_dump(), prd_settings.model_dump())

    def resolver(environment: GestorDataEnvironment) -> Settings:
        return {
            GestorDataEnvironment.HML: hml_settings,
            GestorDataEnvironment.PRD: prd_settings,
        }[environment]

    hml_service = get_gestor_service(
        GestorDataEnvironment.HML, settings_resolver=resolver
    )
    prd_service = get_gestor_service(
        GestorDataEnvironment.PRD, settings_resolver=resolver
    )
    second_hml_service = get_gestor_service(
        GestorDataEnvironment.HML, settings_resolver=resolver
    )

    assert isinstance(hml_service, GestorSqlService)
    assert isinstance(prd_service, GestorSqlService)
    assert isinstance(second_hml_service, GestorSqlService)
    assert hml_service._repositories.natureza._settings is hml_settings
    assert prd_service._repositories.natureza._settings is prd_settings
    assert second_hml_service._repositories.natureza._settings is hml_settings
    assert hml_settings.model_dump() == snapshots[0]
    assert prd_settings.model_dump() == snapshots[1]
