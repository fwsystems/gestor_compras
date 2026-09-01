from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.core.database import DatabaseConnectionError
from app.repositories import limite_repository
from app.repositories.limite_repository import (
    AmbiguousLimiteError,
    LimiteRecord,
    LimiteRepository,
)

MONTH_CASES = [
    (1, "E7_VALJAN1"),
    (2, "E7_VALFEV1"),
    (3, "E7_VALMAR1"),
    (4, "E7_VALABR1"),
    (5, "E7_VALMAI1"),
    (6, "E7_VALJUN1"),
    (7, "E7_VALJUL1"),
    (8, "E7_VALAGO1"),
    (9, "E7_VALSET1"),
    (10, "E7_VALOUT1"),
    (11, "E7_VALNOV1"),
    (12, "E7_VALDEZ1"),
]


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

    monkeypatch.setattr(limite_repository, "get_database_connection", fake_connection)
    return cursor


@pytest.mark.parametrize(("month", "expected_column"), MONTH_CASES)
def test_month_uses_only_confirmed_whitelist_column(
    monkeypatch: pytest.MonkeyPatch,
    month: int,
    expected_column: str,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    LimiteRepository(repository_settings()).list_limites("0101", 2025, month)

    assert f"se7.{expected_column}" in cursor.query
    selected_month_columns = {
        column for _, column in MONTH_CASES if f"se7.{column}" in cursor.query
    }
    assert selected_month_columns == {expected_column}


@pytest.mark.parametrize("month", [0, 13])
def test_invalid_month_is_rejected_before_query(
    monkeypatch: pytest.MonkeyPatch,
    month: int,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    with pytest.raises(ValueError, match="mes"):
        LimiteRepository(repository_settings()).list_limites("0101", 2025, month)

    assert cursor.query == ""


@pytest.mark.parametrize("year", [1999, 2101])
def test_invalid_year_is_rejected(year: int) -> None:
    with pytest.raises(ValueError, match="ano"):
        LimiteRepository(repository_settings()).list_limites("0101", year, 9)


def test_batch_query_uses_se7_suffix_parameters_and_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [("B", Decimal("2")), ("A", Decimal("1"))])

    records = LimiteRepository(repository_settings()).list_limites(" 0101 ", 2025, 9)

    normalized_query = " ".join(cursor.query.split()).upper()
    assert "FROM SE7010 AS SE7" in normalized_query
    assert "SE7.E7_FILIAL = ?" in normalized_query
    assert "SE7.E7_ANO = ?" in normalized_query
    assert "SE7.D_E_L_E_T_ = ''" in normalized_query
    assert "ORDER BY SE7.E7_NATUREZ" in normalized_query
    assert cursor.parameters == ("0101", "2025")
    assert [record.natureza for record in records] == ["A", "B"]
    assert cursor.closed is True


def test_individual_query_parameterizes_nature_including_injection_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [("4.000-010", Decimal("10"))])
    malicious_nature = "4.000-010' OR 1=1 --"

    LimiteRepository(repository_settings()).get_limite(
        "0101", malicious_nature, 2025, 9
    )

    assert "se7.E7_NATUREZ = ?" in cursor.query
    assert malicious_nature not in cursor.query
    assert cursor.parameters == ("0101", "2025", malicious_nature)


@pytest.mark.parametrize(("field", "args"), [("filial", ("", 2025, 9)), ("natureza", ("0101", "", 2025, 9))])
def test_required_text_inputs_are_validated(field: str, args: tuple[object, ...]) -> None:
    repository = LimiteRepository(repository_settings())

    with pytest.raises(ValueError, match=field):
        if field == "filial":
            repository.list_limites(*args)  # type: ignore[arg-type]
        else:
            repository.get_limite(*args)  # type: ignore[arg-type]


def test_decimal_zero_null_and_char_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        [(" A ", Decimal("10.2500")), ("B   ", 0), (" C", None)],
    )

    records = LimiteRepository(repository_settings()).list_limites("0101", 2025, 9)

    assert records == [
        LimiteRecord("A", 2025, 9, Decimal("10.2500")),
        LimiteRecord("B", 2025, 9, Decimal("0")),
        LimiteRecord("C", 2025, 9, Decimal("0")),
    ]
    assert all(isinstance(record.valor, Decimal) for record in records)


def test_empty_batch_and_absent_individual_are_distinct_from_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(monkeypatch, [])
    repository = LimiteRepository(repository_settings())

    assert repository.list_limites("0101", 2025, 9) == []
    assert repository.get_limite("0101", "A", 2025, 9) is None


def test_duplicate_nature_raises_explicit_ambiguity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        [("A", Decimal("10")), ("A ", Decimal("20"))],
    )

    with pytest.raises(AmbiguousLimiteError, match="Multiple budget rows"):
        LimiteRepository(repository_settings()).list_limites("0101", 2025, 9)


def test_query_preserves_fwacom04_currency_behavior_and_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    LimiteRepository(repository_settings()).list_limites("0101", 2025, 9)

    normalized_query = " ".join(cursor.query.split()).upper()
    assert normalized_query.startswith("SELECT")
    assert "E7_MOEDA" not in normalized_query
    assert "SELECT *" not in normalized_query
    assert "NOLOCK" not in normalized_query
    assert "TOP 1" not in normalized_query
    assert "MAX(" not in normalized_query
    assert "SUM(" not in normalized_query
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
        LimiteRepository(repository_settings()).list_limites("0101", 2025, 9)

    assert cursor.closed is True
