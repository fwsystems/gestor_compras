from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.config import AppEnvironment, Settings
from app.core.database import DatabaseConfigurationError, DatabaseConnectionError
from app.repositories.limite_repository import AmbiguousLimiteError
from app.schemas.gestor import GestorPeriod, GestorResponse, GestorRow
from app.services.gestor_sql_service import (
    DuplicateGestorNaturezaError,
    UnexpectedGestorNaturezaError,
)
from scripts import validate_gestor_hml
from scripts.validate_gestor_hml import (
    IncompleteHmlConfigurationError,
    InvalidValidationEnvironmentError,
    format_result,
    run_validation,
)


def hml_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": AppEnvironment.HML,
        "db_host": "hml-host",
        "db_name": "hml-database",
        "db_user": "hml-user",
        "db_password": "super-secret-password",
        "db_driver": "HML ODBC Driver",
        "db_protheus_table_suffix": "010",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def sample_response() -> GestorResponse:
    return GestorResponse(
        periodo=GestorPeriod(ano=2025, mes=9),
        filial="0101",
        linhas=[
            GestorRow(
                natureza_codigo="0010",
                natureza_descricao="NATUREZA TESTE",
                pc_aberto=Decimal("250.00"),
                nf_entrada=Decimal("100.00"),
                contingencia_ok=Decimal("200.00"),
                contingencia_em_aprovacao=Decimal("500.00"),
                limite_original=Decimal("1000.00"),
                limite_total=Decimal("1200.00"),
                saldo_previsto=Decimal("850.00"),
                saldo_real=Decimal("1100.00"),
            )
        ],
        quantidade=1,
    )


class FakeService:
    def __init__(self, response: GestorResponse, events: list[str]) -> None:
        self.response = response
        self.events = events
        self.calls: list[tuple[str, int, int]] = []

    def get_gestor(self, filial: str, ano: int, mes: int) -> GestorResponse:
        self.events.append("service")
        self.calls.append((filial, ano, mes))
        return self.response


@pytest.fixture(autouse=True)
def installed_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        validate_gestor_hml, "is_database_driver_available", lambda _settings: True
    )


@pytest.mark.parametrize("environment", [AppEnvironment.DEV, AppEnvironment.PRD])
def test_runner_rejects_every_environment_except_hml(
    environment: AppEnvironment,
) -> None:
    with pytest.raises(InvalidValidationEnvironmentError, match="only"):
        run_validation(
            settings=hml_settings(app_env=environment),
            filial="0101",
            ano=2025,
            mes=9,
        )


def test_incomplete_sql_configuration_prevents_health() -> None:
    called = False

    def health(_settings: Settings) -> None:
        nonlocal called
        called = True

    with pytest.raises(DatabaseConfigurationError, match="incomplete"):
        run_validation(
            settings=hml_settings(db_password=None),
            filial="0101",
            ano=2025,
            mes=9,
            health_check=health,
        )
    assert called is False


def test_missing_suffix_and_driver_prevent_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(IncompleteHmlConfigurationError, match="suffix"):
        run_validation(
            settings=hml_settings(db_protheus_table_suffix=None),
            filial="0101",
            ano=2025,
            mes=9,
        )
    monkeypatch.setattr(
        validate_gestor_hml, "is_database_driver_available", lambda _settings: False
    )
    with pytest.raises(IncompleteHmlConfigurationError, match="driver"):
        run_validation(
            settings=hml_settings(), filial="0101", ano=2025, mes=9
        )


@pytest.mark.parametrize(
    ("filial", "ano", "mes"),
    [("", 2025, 9), ("  ", 2025, 9), ("0101", 1999, 9), ("0101", 2025, 13)],
)
def test_invalid_query_input_prevents_health(
    filial: str, ano: int, mes: int
) -> None:
    called = False

    def health(_settings: Settings) -> None:
        nonlocal called
        called = True

    with pytest.raises((ValueError, ValidationError)):
        run_validation(
            settings=hml_settings(),
            filial=filial,
            ano=ano,
            mes=mes,
            health_check=health,
        )
    assert called is False


def test_health_runs_before_service_and_service_runs_once() -> None:
    events: list[str] = []
    service = FakeService(sample_response(), events)

    def health(_settings: Settings) -> None:
        events.append("health")

    result = run_validation(
        settings=hml_settings(),
        filial=" 0101 ",
        ano=2025,
        mes=9,
        health_check=health,
        service_factory=lambda: service,  # type: ignore[arg-type]
        clock=iter((10.0, 10.25)).__next__,
    )
    assert events == ["health", "service"]
    assert service.calls == [("0101", 2025, 9)]
    assert result.elapsed_seconds == 0.25


def test_health_failure_prevents_service() -> None:
    events: list[str] = []
    service = FakeService(sample_response(), events)

    def failing_health(_settings: Settings) -> None:
        raise DatabaseConnectionError("SQL Server is unavailable.")

    with pytest.raises(DatabaseConnectionError, match="unavailable"):
        run_validation(
            settings=hml_settings(),
            filial="0101",
            ano=2025,
            mes=9,
            health_check=failing_health,
            service_factory=lambda: service,  # type: ignore[arg-type]
        )
    assert service.calls == []


def test_default_output_is_structural_and_sanitized() -> None:
    service = FakeService(sample_response(), [])
    result = run_validation(
        settings=hml_settings(),
        filial="0101",
        ano=2025,
        mes=9,
        health_check=lambda _settings: None,
        service_factory=lambda: service,  # type: ignore[arg-type]
        clock=iter((1.0, 1.1)).__next__,
    )
    output = format_result(result)
    assert "Quantidade de Naturezas: 1" in output
    assert "Naturezas com PC aberto diferente de zero: 1" in output
    assert "0101" not in output
    assert "hml-host" not in output
    assert "hml-database" not in output
    assert "hml-user" not in output
    assert "super-secret-password" not in output
    assert "250.00" not in output
    assert "NATUREZA TESTE" not in output


def test_controlled_nature_uses_existing_response_without_another_call() -> None:
    service = FakeService(sample_response(), [])
    result = run_validation(
        settings=hml_settings(),
        filial="0101",
        ano=2025,
        mes=9,
        natureza="0010",
        health_check=lambda _settings: None,
        service_factory=lambda: service,  # type: ignore[arg-type]
    )
    output = format_result(result)
    assert service.calls == [("0101", 2025, 9)]
    assert "Código: 0010" in output
    assert "PC aberto: 250.00" in output
    assert "Saldo real: 1100.00" in output


def test_missing_controlled_nature_is_not_a_technical_error() -> None:
    service = FakeService(sample_response(), [])
    result = run_validation(
        settings=hml_settings(),
        filial="0101",
        ano=2025,
        mes=9,
        natureza="9999",
        health_check=lambda _settings: None,
        service_factory=lambda: service,  # type: ignore[arg-type]
    )
    assert "não encontrada" in format_result(result)


@pytest.mark.parametrize(
    "error",
    [
        UnexpectedGestorNaturezaError("PcAbertoRepository", "999"),
        DuplicateGestorNaturezaError("NfEntradaRepository", "001"),
        AmbiguousLimiteError("ambiguous"),
        DatabaseConnectionError("unavailable"),
    ],
)
def test_service_errors_are_not_masked(error: Exception) -> None:
    class FailingService:
        def get_gestor(self, _filial: str, _ano: int, _mes: int) -> GestorResponse:
            raise error

    with pytest.raises(type(error), match=str(error)):
        run_validation(
            settings=hml_settings(),
            filial="0101",
            ano=2025,
            mes=9,
            health_check=lambda _settings: None,
            service_factory=FailingService,  # type: ignore[arg-type]
        )
