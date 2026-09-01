from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.config import AppEnvironment, Settings
from app.repositories.pc_aberto_repository import PcAbertoRecord
from scripts.diagnose_pc_aberto_hml import (
    PcAbertoDiagnosisError,
    build_parser,
    format_diagnosis,
    run_diagnosis,
)


class FakeRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []

    def list_pc_aberto(
        self, filial: str, ano: int, mes: int
    ) -> list[PcAbertoRecord]:
        self.calls.append((filial, ano, mes))
        return [PcAbertoRecord("4.000-460", Decimal("6630.00"))]


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.rows: list[tuple[object, ...]] = []
        self.closed = False

    def execute(self, query: str, *parameters: object) -> None:
        self.executions.append((query, parameters))
        normalized = " ".join(query.split()).upper()
        if "INFORMATION_SCHEMA" in normalized and parameters[0] == "SZN010":
            self.rows = [("ZN_ITEPED",)]
        elif "INFORMATION_SCHEMA" in normalized:
            self.rows = [
                ("C7_ITEM",),
                ("C7_ZZNATUR",),
                ("C7_PRECO",),
                ("C7_TOTAL",),
            ]
        elif "FROM SZN010 AS SZN" in normalized and "GROUP BY" in normalized:
            if "LEFT(SZN.ZN_VENCTO, 6)" in normalized:
                self.rows = [
                    ("202607", 0, Decimal("100.00"), 1),
                    ("202607", 1, Decimal("8773.50"), 2),
                ]
            else:
                self.rows = [
                    ("P1", "01", "20260715", Decimal("6630.00"), 1, 1),
                    ("P2", "01", "20260720", Decimal("2143.50"), 1, 1),
                    ("P3", "01", "20260725", Decimal("100.00"), 1, 0),
                ]
        else:
            self.rows = [
                (
                    "P1",
                    "01",
                    "4.000-460",
                    Decimal("10"),
                    Decimal("2"),
                    Decimal("828.75"),
                    Decimal("8287.50"),
                    " ",
                    1,
                    1,
                    1,
                ),
                (
                    "P2",
                    "01",
                    "4.000-460",
                    Decimal("10"),
                    Decimal("10"),
                    Decimal("214.35"),
                    Decimal("2143.50"),
                    " ",
                    1,
                    0,
                    0,
                ),
            ]

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor

    def cursor(self) -> FakeCursor:
        return self.fake_cursor


def settings(environment: AppEnvironment = AppEnvironment.HML) -> Settings:
    return Settings(
        app_env=environment,
        db_protheus_table_suffix="010",
        _env_file=None,
    )


def fake_factory(cursor: FakeCursor, state: dict[str, bool]):
    @contextmanager
    def connection(_settings: Settings) -> Iterator[FakeConnection]:
        try:
            yield FakeConnection(cursor)
        finally:
            state["closed"] = True

    return connection


@pytest.mark.parametrize("environment", [AppEnvironment.DEV, AppEnvironment.PRD])
def test_runner_blocks_non_hml_before_repository_or_connection(
    environment: AppEnvironment,
) -> None:
    repository = FakeRepository()
    called = False

    @contextmanager
    def connection(_settings: Settings) -> Iterator[FakeConnection]:
        nonlocal called
        called = True
        yield FakeConnection(FakeCursor())

    with pytest.raises(PcAbertoDiagnosisError, match="only in HML"):
        run_diagnosis(
            settings=settings(environment),
            filial="0101",
            ano=2026,
            mes=7,
            natureza="4.000-460",
            repository=repository,
            connection_factory=connection,
        )
    assert repository.calls == []
    assert called is False


@pytest.mark.parametrize(
    ("filial", "ano", "mes", "natureza"),
    [
        ("", 2026, 7, "4.000-460"),
        ("0101", 1999, 7, "4.000-460"),
        ("0101", 2026, 13, "4.000-460"),
        ("0101", 2026, 7, ""),
    ],
)
def test_runner_rejects_invalid_input_before_access(
    filial: str, ano: int, mes: int, natureza: str
) -> None:
    repository = FakeRepository()
    with pytest.raises(ValueError):
        run_diagnosis(
            settings=settings(),
            filial=filial,
            ano=ano,
            mes=mes,
            natureza=natureza,
            repository=repository,
        )
    assert repository.calls == []


def test_parser_requires_all_arguments() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_diagnosis_is_select_only_parameterized_and_closes_resources() -> None:
    cursor = FakeCursor()
    state = {"closed": False}
    repository = FakeRepository()
    diagnosis = run_diagnosis(
        settings=settings(),
        filial=" 0101 ",
        ano=2026,
        mes=7,
        natureza=" 4.000-460 ",
        repository=repository,
        connection_factory=fake_factory(cursor, state),
        now=lambda: datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc),
    )

    assert repository.calls == [("0101", 2026, 7)]
    assert cursor.closed is True
    assert state["closed"] is True
    assert len(cursor.executions) == 5
    forbidden = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "EXEC",
        "EXECUTE",
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
    }
    for query, _parameters in cursor.executions:
        normalized = " ".join(query.split()).upper()
        assert normalized.startswith("SELECT")
        assert "SELECT *" not in normalized
        assert "NOLOCK" not in normalized
        tokens = {token.strip("(),").upper() for token in query.split()}
        assert tokens.isdisjoint(forbidden)
    assert cursor.executions[2][1] == ("0101", "4.000-460", "202607%")
    assert cursor.executions[3][1] == (
        " ",
        "0101",
        "4.000-460",
        "202607%",
    )
    assert cursor.executions[4][1] == ("0101", "4.000-460", "2026%")
    assert "4.000-460" not in " ".join(
        query for query, _parameters in cursor.executions
    )
    assert diagnosis.total_repository == Decimal("6630.00")
    assert diagnosis.total_szn_bruto == Decimal("8773.50")
    assert diagnosis.total_elegivel_diagnostico == Decimal("6630.00")
    assert diagnosis.total_sc7_aberto_calculado == Decimal("6630.00")
    assert diagnosis.exclusions[0].motivo == "registro_szn_logicamente_excluido"
    assert diagnosis.exclusions[0].valor == Decimal("100.00")
    assert diagnosis.exclusions[1].motivo == "sem_item_aberto"
    assert diagnosis.exclusions[1].valor == Decimal("2143.50")
    assert diagnosis.period_totals[1].valor == Decimal("8773.50")


def test_output_is_deterministic_and_does_not_expose_secrets() -> None:
    cursor = FakeCursor()
    diagnosis = run_diagnosis(
        settings=settings(),
        filial="0101",
        ano=2026,
        mes=7,
        natureza="4.000-460",
        repository=FakeRepository(),
        connection_factory=fake_factory(cursor, {"closed": False}),
        now=lambda: datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc),
    )
    output = format_diagnosis(diagnosis)
    assert "Total PcAbertoRepository: 6630.00" in output
    assert "Total bruto SZN ativo: 8773.50" in output
    assert "sem_item_aberto: 2143.50" in output
    assert "Pedido=P1" in output
    assert "C7_ZZNATUR=4.000-460" in output
    for secret in (
        "password",
        "connection string",
        "db_host",
        "db_user",
        "server=",
        "pwd=",
    ):
        assert secret not in output.lower()
