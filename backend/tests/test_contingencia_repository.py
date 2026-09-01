from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.core.database import DatabaseConnectionError
from app.repositories import contingencia_repository
from app.repositories.contingencia_repository import (
    ContingenciaDetailRecord,
    ContingenciaRecord,
    ContingenciaRepository,
)


class FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows
        self.query = ""
        self.parameters: tuple[object, ...] = ()
        self.closed = False
        self.execute_count = 0

    def execute(self, query: str, *parameters: object) -> None:
        self.execute_count += 1
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
        contingencia_repository, "get_database_connection", fake_connection
    )
    return cursor


def normalized(query: str) -> str:
    return " ".join(query.split()).upper()


def test_uses_central_szr_table_and_one_batch_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    ContingenciaRepository(repository_settings()).list_contingencias(
        "0101", 2025, 9
    )
    sql = normalized(cursor.query)
    assert "FROM SZR010 AS SZR" in sql
    assert cursor.execute_count == 1
    assert "GROUP BY SZR.ZR_NATUREZ" in sql
    assert "ORDER BY SZR.ZR_NATUREZ" in sql
    assert cursor.closed is True


def test_branch_period_and_statuses_are_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    ContingenciaRepository(repository_settings()).list_contingencias(
        " 0101 ", 2025, 9
    )
    assert cursor.parameters == (
        "T", "T", "F", "F", "0101", "202509%", "T", "T", "F", "F"
    )
    assert "202509" not in cursor.query
    assert "0101" not in cursor.query
    assert "'T'" not in cursor.query and "'F'" not in cursor.query


def test_exact_ok_and_pending_rules_use_zr_conting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    ContingenciaRepository(repository_settings()).list_contingencias(
        "0101", 2025, 9
    )
    sql = normalized(cursor.query)
    assert "ZR_APROV = ? AND SZR.ZR_REPROV <> ?" in sql
    assert "ZR_APROV = ? AND SZR.ZR_REPROV = ?" in sql
    assert sql.count("THEN SZR.ZR_CONTING") == 2
    assert "SUM(CASE" in sql


def test_source_aggregate_uses_only_szr_without_detail_joins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    ContingenciaRepository(repository_settings()).list_contingencias(
        "0101", 2025, 9
    )
    sql = normalized(cursor.query)
    assert " JOIN " not in sql
    assert "SC7" not in sql
    assert "SA2" not in sql
    assert "ZR_NUMPED" not in sql
    assert "ZR_ITEMPED" not in sql


def test_filial_period_and_logical_deletion_match_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    ContingenciaRepository(repository_settings()).list_contingencias(
        "0101", 2025, 9
    )
    sql = normalized(cursor.query)
    assert "SZR.ZR_FILIAL = ?" in sql
    assert "SZR.ZR_VENCTO LIKE ?" in sql
    assert "SZR.D_E_L_E_T_ = ''" in sql


@pytest.mark.parametrize(
    ("year", "month"), [(1999, 9), (2101, 9), (2025, 0), (2025, 13)]
)
def test_invalid_period_is_rejected_before_query(
    monkeypatch: pytest.MonkeyPatch, year: int, month: int
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    with pytest.raises(ValueError):
        ContingenciaRepository(repository_settings()).list_contingencias(
            "0101", year, month
        )
    assert cursor.query == ""


def test_blank_branch_is_rejected_before_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    with pytest.raises(ValueError, match="filial"):
        ContingenciaRepository(repository_settings()).list_contingencias(
            "  ", 2025, 9
        )
    assert cursor.query == ""


def test_ok_pending_both_multiple_and_different_natures_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        [
            (" C ", Decimal("30.25"), Decimal("0")),
            ("A   ", Decimal("15.10"), Decimal("7.20")),
            ("B", Decimal("0"), Decimal("12.30")),
        ],
    )
    records = ContingenciaRepository(repository_settings()).list_contingencias(
        "0101", 2025, 9
    )
    assert records == [
        ContingenciaRecord("A", Decimal("15.10"), Decimal("7.20")),
        ContingenciaRecord("B", Decimal("0"), Decimal("12.30")),
        ContingenciaRecord("C", Decimal("30.25"), Decimal("0")),
    ]
    assert all(
        isinstance(value, Decimal)
        for record in records
        for value in (record.contingencia_ok, record.contingencia_em_aprovacao)
    )


def test_null_values_and_empty_natures_are_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(monkeypatch, [("A", None, None), (" ", 1, 2), (None, 3, 4)])
    assert ContingenciaRepository(repository_settings()).list_contingencias(
        "0101", 2025, 9
    ) == [ContingenciaRecord("A", Decimal("0"), Decimal("0"))]


def test_empty_result_returns_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_connection(monkeypatch, [])
    assert ContingenciaRepository(repository_settings()).list_contingencias(
        "0101", 2025, 9
    ) == []


def test_injection_text_remains_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    malicious = "0101' OR 1=1 --"
    ContingenciaRepository(repository_settings()).list_contingencias(
        malicious, 2025, 9
    )
    assert malicious not in cursor.query
    assert cursor.parameters[4] == malicious


def test_query_is_explicit_read_only_and_preserves_source_absences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    ContingenciaRepository(repository_settings()).list_contingencias(
        "0101", 2025, 9
    )
    sql = normalized(cursor.query)
    assert sql.startswith("SELECT")
    assert "SELECT *" not in sql
    assert "NOLOCK" not in sql
    for absent in ("ZR_VALOR", "ZR_MANUAL", "MOEDA", "CENTRO", "PRODUTO"):
        assert absent not in sql
    forbidden = {
        "INSERT", "UPDATE", "DELETE", "MERGE", "EXEC", "EXECUTE",
        "CREATE", "ALTER", "DROP", "TRUNCATE",
    }
    tokens = {token.strip("(),").upper() for token in cursor.query.split()}
    assert tokens.isdisjoint(forbidden)


def test_database_error_is_propagated_and_cursor_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    def fail_execute(_query: str, *_parameters: object) -> None:
        raise DatabaseConnectionError("SQL Server is unavailable.")

    monkeypatch.setattr(cursor, "execute", fail_execute)
    with pytest.raises(DatabaseConnectionError, match="unavailable"):
        ContingenciaRepository(repository_settings()).list_contingencias(
            "0101", 2025, 9
        )
    assert cursor.closed is True


@pytest.mark.parametrize(
    ("method_name", "expected_parameters", "status_condition", "status_label"),
    [
        (
            "list_contingencia_ok_details",
            ("0101", "202509%", "1.000-030", "T", "T"),
            "SZR.ZR_APROV = ? AND SZR.ZR_REPROV <> ?",
            "OK",
        ),
        (
            "list_contingencia_aprovacao_details",
            ("0101", "202509%", "1.000-030", "F", "F"),
            "SZR.ZR_APROV = ? AND SZR.ZR_REPROV = ?",
            "Em aprovação",
        ),
    ],
)
def test_detail_types_share_real_filters_and_remain_independent(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_parameters: tuple[object, ...],
    status_condition: str,
    status_label: str,
) -> None:
    cursor = install_fake_connection(
        monkeypatch,
        [("000123", "0001", "20250920", "USRDEV", "1.000-030", 10.125)],
    )
    method = getattr(ContingenciaRepository(repository_settings()), method_name)

    records = method(" 0101 ", 2025, 9, " 1.000-030 ")

    sql = normalized(cursor.query)
    assert cursor.execute_count == 1
    assert cursor.parameters == expected_parameters
    assert "FROM SZR010 AS SZR" in sql
    assert "SZR.ZR_FILIAL = ?" in sql
    assert "SZR.ZR_VENCTO LIKE ?" in sql
    assert "SZR.ZR_NATUREZ = ?" in sql
    assert "SZR.D_E_L_E_T_ = ''" in sql
    assert status_condition in sql
    assert "ORDER BY SZR.ZR_VENCTO, SZR.ZR_NUMPED, SZR.ZR_ITEMPED, SZR.R_E_C_N_O_" in sql
    assert records == [
        ContingenciaDetailRecord(
            "000123", "0001", "20250920", "USRDEV", status_label,
            "1.000-030", Decimal("10.13"),
        )
    ]
    assert cursor.closed is True


def test_detail_preserves_multiple_rows_and_normalizes_float_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        [
            ("1", "01", "20260810", "U1", "A", 100.12500000000001),
            ("2", "02", "20260820", "U2", "A", 200.12400000000001),
        ],
    )

    records = ContingenciaRepository(repository_settings()).list_contingencia_ok_details(
        "0101", 2026, 8, "A"
    )

    assert [record.valor for record in records] == [
        Decimal("100.13"), Decimal("200.12")
    ]
    assert sum((record.valor for record in records), Decimal("0")) == Decimal("300.25")


def test_detail_rejects_blank_nature_before_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    with pytest.raises(ValueError, match="natureza"):
        ContingenciaRepository(repository_settings()).list_contingencia_ok_details(
            "0101", 2025, 9, " "
        )
    assert cursor.query == ""


def test_detail_query_is_select_only_without_joins_or_n_plus_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    ContingenciaRepository(repository_settings()).list_contingencia_aprovacao_details(
        "0101", 2025, 9, "A"
    )
    sql = normalized(cursor.query)
    assert sql.startswith("SELECT")
    assert "SELECT *" not in sql
    assert " JOIN " not in sql
    forbidden = {
        "INSERT", "UPDATE", "DELETE", "MERGE", "EXEC", "EXECUTE",
        "CREATE", "ALTER", "DROP", "TRUNCATE",
    }
    tokens = {token.strip("(),").upper() for token in cursor.query.split()}
    assert tokens.isdisjoint(forbidden)
