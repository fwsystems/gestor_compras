from decimal import Decimal

import pytest

from app.core.config import AppEnvironment, Settings
from app.core.database import DatabaseConfigurationError, DatabaseConnectionError
from app.schemas.gestor import GestorPeriod, GestorResponse, GestorRow
from scripts import prd_read_only_guard
from scripts.prd_read_only_guard import (
    IncompletePrdConfigurationError,
    InvalidPrdValidationEnvironmentError,
    PrdReadOnlyValidationDisabledError,
)
from scripts.validate_gestor_prd import format_result, run_validation


def prd_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": AppEnvironment.PRD,
        "gestor_prd_read_only_validation": True,
        "db_host": "prd-host",
        "db_name": "prd-database",
        "db_user": "prd-user",
        "db_password": "super-secret-password",
        "db_driver": "PRD ODBC Driver",
        "db_protheus_table_suffix": "010",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def response() -> GestorResponse:
    return GestorResponse(
        periodo=GestorPeriod(ano=2026, mes=7),
        filial="0101",
        linhas=[
            GestorRow(
                natureza_codigo="4.000-460",
                natureza_descricao="NATUREZA CONTROLADA",
                pc_aberto=Decimal("6630.00"),
                nf_entrada=Decimal("100.00"),
                contingencia_ok=Decimal("0"),
                contingencia_em_aprovacao=Decimal("0"),
                limite_original=Decimal("10000.00"),
                saldo_previsto=Decimal("3270.00"),
                saldo_real=Decimal("9900.00"),
            )
        ],
        quantidade=1,
    )


class FakeService:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.calls: list[tuple[str, int, int]] = []

    def get_gestor(self, filial: str, ano: int, mes: int) -> GestorResponse:
        self.events.append("service")
        self.calls.append((filial, ano, mes))
        return response()


@pytest.fixture(autouse=True)
def installed_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        prd_read_only_guard,
        "is_database_driver_available",
        lambda _settings: True,
    )


@pytest.mark.parametrize("environment", [AppEnvironment.DEV, AppEnvironment.HML])
def test_runner_rejects_non_prd_before_health(environment: AppEnvironment) -> None:
    called = False

    def health(_settings: Settings) -> None:
        nonlocal called
        called = True

    with pytest.raises(InvalidPrdValidationEnvironmentError, match="only"):
        run_validation(
            settings=prd_settings(app_env=environment),
            filial="0101",
            ano=2026,
            mes=7,
            health_check=health,
        )
    assert called is False


def test_runner_rejects_prd_when_flag_is_false_before_health() -> None:
    called = False

    def health(_settings: Settings) -> None:
        nonlocal called
        called = True

    with pytest.raises(PrdReadOnlyValidationDisabledError, match="disabled"):
        run_validation(
            settings=prd_settings(gestor_prd_read_only_validation=False),
            filial="0101",
            ano=2026,
            mes=7,
            health_check=health,
        )
    assert called is False


def test_incomplete_configuration_prevents_health_and_service() -> None:
    events: list[str] = []
    service = FakeService(events)
    with pytest.raises(DatabaseConfigurationError, match="incomplete"):
        run_validation(
            settings=prd_settings(db_password=None),
            filial="0101",
            ano=2026,
            mes=7,
            health_check=lambda _settings: events.append("health"),
            service_factory=lambda: service,  # type: ignore[arg-type]
        )
    assert events == []


def test_missing_suffix_or_driver_prevents_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(IncompletePrdConfigurationError, match="suffix"):
        run_validation(
            settings=prd_settings(db_protheus_table_suffix=None),
            filial="0101",
            ano=2026,
            mes=7,
        )
    monkeypatch.setattr(
        prd_read_only_guard,
        "is_database_driver_available",
        lambda _settings: False,
    )
    with pytest.raises(IncompletePrdConfigurationError, match="driver"):
        run_validation(
            settings=prd_settings(), filial="0101", ano=2026, mes=7
        )


def test_health_runs_before_service_and_service_runs_once() -> None:
    events: list[str] = []
    service = FakeService(events)
    result = run_validation(
        settings=prd_settings(),
        filial=" 0101 ",
        ano=2026,
        mes=7,
        health_check=lambda _settings: events.append("health"),
        service_factory=lambda: service,  # type: ignore[arg-type]
        clock=iter((1.0, 1.2)).__next__,
    )
    assert events == ["health", "service"]
    assert service.calls == [("0101", 2026, 7)]
    assert result.elapsed_seconds == pytest.approx(0.2)


def test_health_failure_prevents_service_without_fallback() -> None:
    service = FakeService([])

    def fail(_settings: Settings) -> None:
        raise DatabaseConnectionError("unavailable")

    with pytest.raises(DatabaseConnectionError, match="unavailable"):
        run_validation(
            settings=prd_settings(),
            filial="0101",
            ano=2026,
            mes=7,
            health_check=fail,
            service_factory=lambda: service,  # type: ignore[arg-type]
        )
    assert service.calls == []


def test_default_output_is_structural_masked_and_sanitized() -> None:
    result = run_validation(
        settings=prd_settings(),
        filial="0101",
        ano=2026,
        mes=7,
        health_check=lambda _settings: None,
        service_factory=lambda: FakeService([]),  # type: ignore[arg-type]
    )
    output = format_result(result)
    assert "Ambiente: PRD" in output
    assert "Quantidade de Naturezas: 1" in output
    assert "Filial: ***01" in output
    for private in (
        "0101",
        "prd-host",
        "prd-database",
        "prd-user",
        "super-secret-password",
        "6630.00",
        "NATUREZA CONTROLADA",
    ):
        assert private not in output


def test_controlled_nature_prints_only_selected_existing_row() -> None:
    service = FakeService([])
    result = run_validation(
        settings=prd_settings(),
        filial="0101",
        ano=2026,
        mes=7,
        natureza="4.000-460",
        health_check=lambda _settings: None,
        service_factory=lambda: service,  # type: ignore[arg-type]
    )
    output = format_result(result)
    assert service.calls == [("0101", 2026, 7)]
    assert "Código: 4.000-460" in output
    assert "PC aberto: 6630.00" in output


def test_invalid_input_prevents_health() -> None:
    called = False

    def health(_settings: Settings) -> None:
        nonlocal called
        called = True

    with pytest.raises(ValueError):
        run_validation(
            settings=prd_settings(),
            filial=" ",
            ano=2026,
            mes=7,
            health_check=health,
        )
    assert called is False
