from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.config import AppEnvironment, Settings
from app.core.database import DatabaseConnectionError
from scripts import prd_read_only_guard
from scripts.diagnose_pc_aberto_hml import PcAbertoDiagnosis
from scripts.diagnose_pc_aberto_prd import build_parser, run_diagnosis
from scripts.prd_read_only_guard import (
    InvalidPrdValidationEnvironmentError,
    PrdReadOnlyValidationDisabledError,
)


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": AppEnvironment.PRD,
        "gestor_prd_read_only_validation": True,
        "db_host": "prd-host",
        "db_name": "prd-db",
        "db_user": "prd-user",
        "db_password": "secret",
        "db_driver": "PRD Driver",
        "db_protheus_table_suffix": "010",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def diagnosis() -> PcAbertoDiagnosis:
    return PcAbertoDiagnosis(
        executed_at_utc=datetime(2026, 8, 26, tzinfo=timezone.utc),
        filial="0101",
        ano=2026,
        mes=7,
        natureza="4.000-460",
        total_repository=Decimal("6630"),
        total_szn_bruto=Decimal("6630"),
        total_elegivel_diagnostico=Decimal("6630"),
        total_sc7_aberto_calculado=Decimal("6630"),
        contributions=(),
        sc7_items=(),
        exclusions=(),
        period_totals=(),
    )


@pytest.fixture(autouse=True)
def installed_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        prd_read_only_guard,
        "is_database_driver_available",
        lambda _settings: True,
    )


def test_parser_requires_all_arguments() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


@pytest.mark.parametrize("environment", [AppEnvironment.DEV, AppEnvironment.HML])
def test_runner_rejects_non_prd_before_health_or_diagnosis(
    environment: AppEnvironment,
) -> None:
    events: list[str] = []
    with pytest.raises(InvalidPrdValidationEnvironmentError, match="only"):
        run_diagnosis(
            settings=settings(app_env=environment),
            filial="0101",
            ano=2026,
            mes=7,
            natureza="4.000-460",
            health_check=lambda _settings: events.append("health"),
            diagnosis_runner=lambda **_kwargs: events.append("diagnosis"),  # type: ignore[arg-type,return-value]
        )
    assert events == []


def test_runner_rejects_disabled_flag_before_health_or_diagnosis() -> None:
    events: list[str] = []
    with pytest.raises(PrdReadOnlyValidationDisabledError, match="disabled"):
        run_diagnosis(
            settings=settings(gestor_prd_read_only_validation=False),
            filial="0101",
            ano=2026,
            mes=7,
            natureza="4.000-460",
            health_check=lambda _settings: events.append("health"),
            diagnosis_runner=lambda **_kwargs: events.append("diagnosis"),  # type: ignore[arg-type,return-value]
        )
    assert events == []


def test_health_runs_before_select_only_diagnosis() -> None:
    events: list[str] = []

    def runner(**kwargs: object) -> PcAbertoDiagnosis:
        events.append("diagnosis")
        assert kwargs["filial"] == " 0101 "
        assert kwargs["natureza"] == " 4.000-460 "
        return diagnosis()

    result = run_diagnosis(
        settings=settings(),
        filial=" 0101 ",
        ano=2026,
        mes=7,
        natureza=" 4.000-460 ",
        health_check=lambda _settings: events.append("health"),
        diagnosis_runner=runner,
    )
    assert events == ["health", "diagnosis"]
    assert result.total_repository == Decimal("6630")


def test_health_failure_prevents_diagnosis_without_fallback() -> None:
    called = False

    def runner(**_kwargs: object) -> PcAbertoDiagnosis:
        nonlocal called
        called = True
        return diagnosis()

    def fail(_settings: Settings) -> None:
        raise DatabaseConnectionError("unavailable")

    with pytest.raises(DatabaseConnectionError, match="unavailable"):
        run_diagnosis(
            settings=settings(),
            filial="0101",
            ano=2026,
            mes=7,
            natureza="4.000-460",
            health_check=fail,
            diagnosis_runner=runner,
        )
    assert called is False


def test_invalid_input_prevents_health() -> None:
    called = False

    def health(_settings: Settings) -> None:
        nonlocal called
        called = True

    with pytest.raises(ValueError):
        run_diagnosis(
            settings=settings(),
            filial="",
            ano=2026,
            mes=7,
            natureza="4.000-460",
            health_check=health,
        )
    assert called is False
