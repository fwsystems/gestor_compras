from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.core.database import DatabaseConnectionError
from app.repositories import nf_entrada_repository
from app.repositories.nf_entrada_repository import (
    NfEntradaDetailRecord,
    NfEntradaRecord,
    NfEntradaRepository,
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
        nf_entrada_repository, "get_database_connection", fake_connection
    )
    return cursor


def normalized(query: str) -> str:
    return " ".join(query.split()).upper()


def test_query_uses_central_tables_exact_join_and_batch_aggregation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    NfEntradaRepository(repository_settings()).list_nf_entrada("0101", 2025, 9)

    sql = normalized(cursor.query)
    assert "FROM SE2010 AS SE2 INNER JOIN SEV010 AS SEV" in sql
    expected_joins = (
        "SEV.EV_FILIAL = SE2.E2_FILIAL",
        "SEV.EV_NUM = SE2.E2_NUM",
        "SEV.EV_PREFIXO = SE2.E2_PREFIXO",
        "SEV.EV_PARCELA = SE2.E2_PARCELA",
        "SEV.EV_CLIFOR = SE2.E2_FORNECE",
        "SEV.EV_LOJA = SE2.E2_LOJA",
    )
    assert all(join in sql for join in expected_joins)
    assert "SUM(SEV.EV_VALOR)" in sql
    assert "GROUP BY SEV.EV_NATUREZ" in sql
    assert "ORDER BY SEV.EV_NATUREZ" in sql
    assert cursor.closed is True


def test_filters_and_period_are_parameterized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    NfEntradaRepository(repository_settings()).list_nf_entrada(
        " 0101 ", 2025, 9
    )

    sql = normalized(cursor.query)
    assert "SEV.EV_SITUACA NOT IN (?, ?)" in sql
    assert "SEV.EV_IDENT = ?" in sql
    assert "SE2.E2_FILIAL = ?" in sql
    assert "SE2.E2_VENCTO LIKE ?" in sql
    assert cursor.parameters == ("E", "X", "1", "0101", "202509%")
    assert "'E'" not in cursor.query and "'X'" not in cursor.query


def test_logical_deletion_is_applied_to_both_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    NfEntradaRepository(repository_settings()).list_nf_entrada("0101", 2025, 9)
    sql = normalized(cursor.query)
    assert "SEV.D_E_L_E_T_ = ''" in sql
    assert "SE2.D_E_L_E_T_ = ''" in sql


@pytest.mark.parametrize(("year", "month"), [(1999, 9), (2101, 9), (2025, 0), (2025, 13)])
def test_invalid_period_is_rejected_before_query(
    monkeypatch: pytest.MonkeyPatch, year: int, month: int
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    with pytest.raises(ValueError):
        NfEntradaRepository(repository_settings()).list_nf_entrada(
            "0101", year, month
        )
    assert cursor.query == ""


def test_blank_branch_is_rejected_before_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    with pytest.raises(ValueError, match="filial"):
        NfEntradaRepository(repository_settings()).list_nf_entrada("  ", 2025, 9)
    assert cursor.query == ""


def test_decimal_null_empty_nature_and_order_are_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        [(" B ", Decimal("20.5000")), ("A   ", None), (" ", 3), (None, 4)],
    )

    records = NfEntradaRepository(repository_settings()).list_nf_entrada(
        "0101", 2025, 9
    )

    assert records == [
        NfEntradaRecord("A", Decimal("0")),
        NfEntradaRecord("B", Decimal("20.5000")),
    ]
    assert all(isinstance(record.valor, Decimal) for record in records)


def test_empty_result_returns_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_connection(monkeypatch, [])
    assert (
        NfEntradaRepository(repository_settings()).list_nf_entrada(
            "0101", 2025, 9
        )
        == []
    )


def test_branch_injection_text_remains_parameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    malicious = "0101' OR 1=1 --"
    NfEntradaRepository(repository_settings()).list_nf_entrada(
        malicious, 2025, 9
    )
    assert malicious not in cursor.query
    assert cursor.parameters[-2] == malicious


def test_query_preserves_source_absences_and_is_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    NfEntradaRepository(repository_settings()).list_nf_entrada("0101", 2025, 9)
    sql = normalized(cursor.query)
    assert sql.startswith("SELECT")
    assert "SELECT *" not in sql
    assert "NOLOCK" not in sql
    for absent in (
        "EV_TIPO",
        "E2_TIPO",
        "E2_SALDO",
        "E2_BAIXA",
        "E2_EMISSAO",
        "E2_MOEDA",
    ):
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
        NfEntradaRepository(repository_settings()).list_nf_entrada(
            "0101", 2025, 9
        )
    assert cursor.closed is True


def test_detail_reuses_nf_join_filters_and_returns_confirmed_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(
        monkeypatch,
        [(
            "123", "NF", "01", "000001", "FORNECEDOR TESTE", "01",
            "20250901", "20250925", "4.000-010", Decimal("99.90"),
        )],
    )
    records = NfEntradaRepository(repository_settings()).list_nf_entrada_details(
        "0101", 2025, 9, "4.000-010"
    )
    sql = normalized(cursor.query)
    assert "SEV.EV_NUM = SE2.E2_NUM" in sql
    assert "SEV.EV_SITUACA NOT IN (?, ?)" in sql
    assert "SEV.EV_NATUREZ = ?" in sql
    assert "LEFT JOIN SA2010 AS SA2" in sql
    assert "SA2.A2_FILIAL = LEFT(SE2.E2_FILIAL, 2)" in sql
    assert "SA2.A2_COD = SE2.E2_FORNECE" in sql
    assert "SA2.A2_LOJA = SE2.E2_LOJA" in sql
    assert "SA2.D_E_L_E_T_ = ''" in sql
    assert "SE2.E2_EMISSAO" in sql
    assert "SE2.E2_TIPO" not in sql
    assert "ORDER BY SE2.E2_VENCTO, SE2.E2_NUM, SE2.E2_PREFIXO, SE2.E2_PARCELA, SE2.E2_FORNECE, SE2.E2_LOJA" in sql
    assert "SUM(" not in sql and "GROUP BY" not in sql
    assert cursor.parameters == ("E", "X", "1", "0101", "202509%", "4.000-010")
    assert records == [
        NfEntradaDetailRecord(
            "123", "NF", "01", "000001", "FORNECEDOR TESTE", "01",
            "20250901", "20250925", "4.000-010", Decimal("99.90"),
        )
    ]


def test_detail_preserves_multiple_titles_and_missing_supplier_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        [
            ("1", "NF", "1", "F1", None, "01", "20260801", "20260810", "A", 10),
            ("2", "NF", "1", "F2", " NOME 2 ", "02", "20260802", "20260820", "A", 20),
        ],
    )

    records = NfEntradaRepository(repository_settings()).list_nf_entrada_details(
        "0101", 2026, 8, "A"
    )

    assert len(records) == 2
    assert records[0].fornecedor == "F1"
    assert records[0].fornecedor_nome == ""
    assert records[1].fornecedor_nome == "NOME 2"
    assert sum((record.valor for record in records), Decimal("0")) == Decimal("30.00")


def test_detail_query_remains_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    NfEntradaRepository(repository_settings()).list_nf_entrada_details(
        "0101", 2025, 9, "4.000-010"
    )
    assert normalized(cursor.query).startswith("SELECT")
    assert "SELECT *" not in normalized(cursor.query)


def test_sql_float_noise_is_normalized_to_currency_precision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(monkeypatch, [("A", 28056.880000000005)])
    repository = NfEntradaRepository(repository_settings())

    assert repository.list_nf_entrada("0101", 2026, 8) == [
        NfEntradaRecord("A", Decimal("28056.88"))
    ]

    install_fake_connection(
        monkeypatch,
        [("1", "NF", "1", "F", "NOME", "01", "20260801", "20260810", "A", 100.12500000000001)],
    )
    assert repository.list_nf_entrada_details("0101", 2026, 8, "A") == [
        NfEntradaDetailRecord(
            "1", "NF", "1", "F", "NOME", "01", "20260801", "20260810",
            "A", Decimal("100.13"),
        )
    ]
