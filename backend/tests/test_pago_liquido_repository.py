from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.repositories import pago_liquido_repository
from app.repositories.pago_liquido_repository import (
    PagoLiquidoRecord,
    PagoLiquidoRepository,
)


class FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows
        self.query = ""
        self.parameters: tuple[object, ...] = ()
        self.closed = False

    def execute(self, query: str, *parameters: object) -> None:
        self.query = query
        self.parameters = parameters

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor

    def cursor(self) -> FakeCursor:
        return self.fake_cursor


def repository_settings() -> Settings:
    return Settings(db_protheus_table_suffix="010", _env_file=None)


def install_fake_connection(
    monkeypatch: pytest.MonkeyPatch,
    rows: list[tuple[object, ...]],
) -> FakeCursor:
    cursor = FakeCursor(rows)

    @contextmanager
    def fake_connection(_settings: Settings) -> Iterator[FakeConnection]:
        yield FakeConnection(cursor)

    monkeypatch.setattr(
        pago_liquido_repository, "get_database_connection", fake_connection
    )
    return cursor


def normalized(query: str) -> str:
    return " ".join(query.split()).upper()


def test_query_uses_configurable_se5_and_homologated_movements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [(" 001 ", 90.005)])

    records = PagoLiquidoRepository(repository_settings()).list_pago_liquido(
        " 0101 ", 2025, 9
    )

    sql = normalized(cursor.query)
    assert "FROM SE5010 AS E5" in sql
    assert "MOV.E5_FILIAL = SE2.E2_FILIAL" in sql
    assert "MOV.E5_PREFIXO = SE2.E2_PREFIXO" in sql
    assert "MOV.E5_NUMERO = SE2.E2_NUM" in sql
    assert "MOV.E5_PARCELA = SE2.E2_PARCELA" in sql
    assert "MOV.E5_CLIFOR = SE2.E2_FORNECE" in sql
    assert "MOV.E5_LOJA = SE2.E2_LOJA" in sql
    assert "E5.E5_DTCANBX" in sql
    assert "SE2.E2_STATLIB" in sql
    assert "SE2.E2_DATALIB" in sql
    assert "SE2.E2_VENCREA" in sql
    assert "SE2.E2_BAIXA" in sql
    assert "SE2.E2_SALDO" in sql
    assert "SE2.E2_TIPO <> 'NDF'" in sql
    assert "SE2.E2_NATUREZ" in sql
    assert "SEV.EV_PERC" in sql
    assert "E5.E5_MOTBX IN ('CMP', 'CEC', 'DAC')" in sql
    assert "E2.E2_PIS" in sql
    assert "E2.E2_COFINS" in sql
    assert "E2.E2_CSLL" in sql
    assert "E2.E2_DECRESC" in sql
    assert "E2.E2_ACRESC" in sql
    assert cursor.parameters == ("0101", "20250901", "20250930", "20250901", "20250930", "20250901", "20250930")
    assert records == [PagoLiquidoRecord("001", Decimal("90.01"), Decimal("0"), Decimal("90.01"))]
    assert cursor.closed is True


def test_future_period_uses_balance_tax_and_excludes_compensated_titles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    monkeypatch.setattr(pago_liquido_repository, "_is_future_period", lambda _ano, _mes: True)

    PagoLiquidoRepository(repository_settings()).list_pago_liquido("0101", 2025, 9)

    sql = normalized(cursor.query)
    assert "SE2.E2_ISS" in sql
    assert "SE2.E2_SALDO" in sql
    assert "AND BASE.COMPENSACAO = 0" in sql


def test_query_excludes_non_homologated_movement_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    PagoLiquidoRepository(repository_settings()).list_pago_liquido("0101", 2025, 9)

    sql = normalized(cursor.query)
    assert "E5_RECPAG = 'P' AND E5_TIPODOC = 'CP'" not in sql
    assert "E5_RECPAG = 'P' AND E5_TIPODOC = 'BA'" not in sql
    assert "E5_RECPAG = 'P' AND E5_TIPODOC = 'JR'" not in sql
    assert "E5_RECPAG = 'P' AND E5_TIPODOC = 'DC'" not in sql
    assert "E5_RECPAG = 'R' AND E5_TIPODOC = 'VL'" not in sql


@pytest.mark.parametrize(
    ("inicio", "fim", "expected_start", "expected_end"),
    [
        (None, None, "20250901", "20250930"),
        (date(2025, 9, 8), date(2025, 9, 14), "20250908", "20250914"),
        (date(2025, 9, 19), date(2025, 9, 19), "20250919", "20250919"),
    ],
)
def test_period_is_inclusive_for_month_week_and_day(
    monkeypatch: pytest.MonkeyPatch,
    inicio: date | None,
    fim: date | None,
    expected_start: str,
    expected_end: str,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    PagoLiquidoRepository(repository_settings()).list_pago_liquido(
        "0101", 2025, 9, inicio, fim
    )

    assert cursor.parameters == ("0101", expected_start, expected_end, expected_start, expected_end, expected_start, expected_end)


@pytest.mark.parametrize(
    ("ano", "mes", "inicio", "fim"),
    [
        (1999, 9, None, None),
        (2025, 13, None, None),
        (2025, 9, date(2025, 9, 1), None),
        (2025, 9, date(2025, 8, 31), date(2025, 9, 1)),
    ],
)
def test_invalid_period_is_rejected_before_query(
    monkeypatch: pytest.MonkeyPatch,
    ano: int,
    mes: int,
    inicio: date | None,
    fim: date | None,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    with pytest.raises(ValueError):
        PagoLiquidoRepository(repository_settings()).list_pago_liquido(
            "0101", ano, mes, inicio, fim
        )
    assert cursor.query == ""


def test_blank_branch_is_rejected_before_query(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    with pytest.raises(ValueError, match="filial"):
        PagoLiquidoRepository(repository_settings()).list_pago_liquido(" ", 2025, 9)
    assert cursor.query == ""


def test_empty_nature_is_ignored_and_values_are_decimal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        [(" A ", 12.345), (" ", 10), (None, 20)],
    )

    records = PagoLiquidoRepository(repository_settings()).list_pago_liquido(
        "0101", 2025, 9
    )

    assert records == [PagoLiquidoRecord("A", Decimal("12.35"), Decimal("0"), Decimal("12.35"))]
    assert all(isinstance(record.valor, Decimal) for record in records)
