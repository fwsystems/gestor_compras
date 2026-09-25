from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.core.database import DatabaseConnectionError
from app.repositories import pc_aberto_repository
from app.repositories.pc_aberto_repository import (
    PcAbertoDetailRecord,
    PcAbertoRecord,
    PcAbertoRepository,
)


class FakeCursor:
    def __init__(self, rows: list[tuple[object, object]]) -> None:
        self.rows = rows
        self.query = ""
        self.parameters: tuple[object, ...] = ()
        self.closed = False

    def execute(self, query: str, *parameters: object) -> None:
        self.query = query
        self.parameters = parameters

    def fetchall(self) -> list[tuple[object, object]]:
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
    rows: list[tuple[object, object]],
) -> FakeCursor:
    cursor = FakeCursor(rows)

    @contextmanager
    def fake_connection(_settings: Settings) -> Iterator[FakeConnection]:
        yield FakeConnection(cursor)

    monkeypatch.setattr(pc_aberto_repository, "get_database_connection", fake_connection)
    return cursor


def test_batch_query_uses_central_tables_parameters_and_period(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    PcAbertoRepository(repository_settings()).list_pc_aberto(" 0101 ", 2025, 9)

    normalized_query = " ".join(cursor.query.split()).upper()
    assert "FROM SZN010 AS SZN" in normalized_query
    assert "FROM SC7010 AS SC7" in normalized_query
    assert "SZN.ZN_FILIAL = ?" in normalized_query
    assert "SZN.ZN_VENCTO LIKE ?" in normalized_query
    assert cursor.parameters == ("0101", "202509%", " ")
    assert cursor.closed is True


@pytest.mark.parametrize(("year", "month"), [(1999, 1), (2101, 1), (2025, 0), (2025, 13)])
def test_invalid_period_is_rejected_before_query(
    monkeypatch: pytest.MonkeyPatch,
    year: int,
    month: int,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    with pytest.raises(ValueError):
        PcAbertoRepository(repository_settings()).list_pc_aberto("0101", year, month)

    assert cursor.query == ""


def test_empty_branch_is_rejected() -> None:
    with pytest.raises(ValueError, match="filial"):
        PcAbertoRepository(repository_settings()).list_pc_aberto("  ", 2025, 9)


def test_open_and_partially_received_item_rule_matches_fwacom04(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    PcAbertoRepository(repository_settings()).list_pc_aberto("0101", 2025, 9)

    normalized_query = " ".join(cursor.query.split()).upper()
    assert "NOT (SC7.C7_QUJE >= SC7.C7_QUANT)" in normalized_query
    assert "SC7.C7_RESIDUO = ?" in normalized_query
    assert cursor.parameters[-1] == " "
    assert "SC7.C7_FILIAL = SZN.ZN_FILIAL" in normalized_query
    assert "SC7.C7_NUM = SZN.ZN_NUMPED" in normalized_query


def test_fully_received_and_residual_orders_are_excluded_by_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    PcAbertoRepository(repository_settings()).list_pc_aberto("0101", 2025, 9)

    assert "NOT (sc7.C7_QUJE >= sc7.C7_QUANT)" in cursor.query
    assert "sc7.C7_RESIDUO = ?" in cursor.query
    assert "EXISTS" in cursor.query


def test_logical_deletion_is_filtered_in_szn_and_sc7(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    PcAbertoRepository(repository_settings()).list_pc_aberto("0101", 2025, 9)

    normalized_query = " ".join(cursor.query.split()).upper()
    assert "SZN.D_E_L_E_T_ = ''" in normalized_query
    assert "SC7.D_E_L_E_T_ = ''" in normalized_query


def test_commitments_are_aggregated_by_nature_in_one_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(
        monkeypatch,
        [(" B ", Decimal("25.50")), ("A   ", Decimal("100.1250"))],
    )

    records = PcAbertoRepository(repository_settings()).list_pc_aberto("0101", 2025, 9)

    normalized_query = " ".join(cursor.query.split()).upper()
    assert "SUM(SZN.ZN_SALDO)" in normalized_query
    assert "GROUP BY SZN.ZN_NATUREZ" in normalized_query
    assert "ORDER BY SZN.ZN_NATUREZ" in normalized_query
    assert records == [
        PcAbertoRecord("B", Decimal("25.50")),
        PcAbertoRecord("A", Decimal("100.13")),
    ]
    assert all(isinstance(record.valor, Decimal) for record in records)


def test_zero_null_and_empty_results_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(monkeypatch, [("A", 0), ("B", None)])
    repository = PcAbertoRepository(repository_settings())

    assert repository.list_pc_aberto("0101", 2025, 9) == [
        PcAbertoRecord("A", Decimal("0")),
        PcAbertoRecord("B", Decimal("0")),
    ]

    install_fake_connection(monkeypatch, [])
    assert repository.list_pc_aberto("0101", 2025, 9) == []


def test_branch_injection_text_remains_parameterized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    malicious_branch = "0101' OR 1=1 --"

    PcAbertoRepository(repository_settings()).list_pc_aberto(
        malicious_branch, 2025, 9
    )

    assert malicious_branch not in cursor.query
    assert cursor.parameters == (malicious_branch, "202509%", " ")


def test_query_is_explicit_read_only_and_without_nolock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    PcAbertoRepository(repository_settings()).list_pc_aberto("0101", 2025, 9)

    normalized_query = " ".join(cursor.query.split()).upper()
    assert normalized_query.startswith("SELECT")
    assert "SELECT *" not in normalized_query
    assert "NOLOCK" not in normalized_query
    forbidden = {"INSERT", "UPDATE", "DELETE", "MERGE", "EXEC", "EXECUTE", "CREATE", "ALTER", "DROP", "TRUNCATE"}
    assert {token.strip("(),").upper() for token in cursor.query.split()}.isdisjoint(forbidden)


def test_database_error_is_propagated_and_cursor_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    def fail_execute(_query: str, *_parameters: object) -> None:
        raise DatabaseConnectionError("SQL Server is unavailable.")

    monkeypatch.setattr(cursor, "execute", fail_execute)

    with pytest.raises(DatabaseConnectionError, match="unavailable"):
        PcAbertoRepository(repository_settings()).list_pc_aberto("0101", 2025, 9)

    assert cursor.closed is True


def test_detail_reuses_open_order_filters_and_is_parameterized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(
        monkeypatch,
        [(" 000123 ", "20250920", " 4.000-010 ", Decimal("125.50"), "000001", "Fornecedor Teste")],  # type: ignore[list-item]
    )
    records = PcAbertoRepository(repository_settings()).list_pc_aberto_details(
        " 0101 ", 2025, 9, " 4.000-010 "
    )
    sql = " ".join(cursor.query.split()).upper()
    assert "NOT (SC7.C7_QUJE >= SC7.C7_QUANT)" in sql
    assert "SC7.C7_RESIDUO = ?" in sql
    assert "SZN.ZN_NATUREZ = ?" in sql
    assert "OUTER APPLY" in sql
    assert "SC7_SUPPLIER.C7_FORNECE" in sql
    assert "SA2_SUPPLIER.A2_NOME" in sql
    assert "LEFT JOIN SA2010 AS SA2_SUPPLIER" in sql
    assert "SUM(" not in sql and "GROUP BY" not in sql
    assert cursor.parameters == ("0101", "202509%", " ", "4.000-010")
    assert records == [
        PcAbertoDetailRecord("000123", "20250920", "4.000-010", Decimal("125.50"), "000001", "Fornecedor Teste")
    ]


def test_detail_keeps_order_when_supplier_name_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        [("000124", "20250921", "4.000-010", Decimal("75.50"), "000999", None)],  # type: ignore[list-item]
    )

    records = PcAbertoRepository(repository_settings()).list_pc_aberto_details(
        "0101", 2025, 9, "4.000-010"
    )

    assert records == [
        PcAbertoDetailRecord("000124", "20250921", "4.000-010", Decimal("75.50"), "000999", "")
    ]


def test_detail_rejects_blank_nature_before_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    with pytest.raises(ValueError, match="natureza"):
        PcAbertoRepository(repository_settings()).list_pc_aberto_details(
            "0101", 2025, 9, " "
        )
    assert cursor.query == ""
