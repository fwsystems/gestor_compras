from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from app.core.config import Settings
from app.core.database import DatabaseConfigurationError, DatabaseConnectionError
from app.core.gestor import GESTOR_COMPRAS_PAINEL
from app.repositories import natureza_repository
from app.repositories.natureza_repository import (
    AmbiguousNaturezaError,
    NaturezaRecord,
    NaturezaRepository,
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


def repository_settings(suffix: str = "010") -> Settings:
    return Settings(db_protheus_table_suffix=suffix, _env_file=None)


def install_fake_connection(
    monkeypatch: pytest.MonkeyPatch,
    rows: list[tuple[object, object]],
) -> FakeCursor:
    cursor = FakeCursor(rows)

    @contextmanager
    def fake_connection(_settings: Settings) -> Iterator[FakeConnection]:
        yield FakeConnection(cursor)

    monkeypatch.setattr(natureza_repository, "get_database_connection", fake_connection)
    return cursor


def test_repository_uses_sed_se7_panel_universe_with_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [("4.000-010", "MATÉRIA-PRIMA")])

    records = NaturezaRepository(repository_settings()).list_naturezas(" 0101 ")

    normalized_query = " ".join(cursor.query.split()).upper()
    assert normalized_query.startswith("SELECT")
    assert "FROM SED010 AS SED" in normalized_query
    assert "FROM SE7010 AS SE7" in normalized_query
    assert "EXISTS" in normalized_query
    assert "SED.ED_FILIAL = ?" in normalized_query
    assert "SED.ED_ZPAINEL = ?" in normalized_query
    assert "SE7.E7_FILIAL = SED.ED_FILIAL" in normalized_query
    assert "SE7.E7_NATUREZ = SED.ED_CODIGO" in normalized_query
    assert cursor.parameters == ("0101", GESTOR_COMPRAS_PAINEL)
    assert records == [NaturezaRecord("4.000-010", "MATÉRIA-PRIMA")]
    assert cursor.closed is True


def test_repository_filters_logical_deletion_and_orders_by_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [("B", "Beta"), ("A", "Alfa")])

    records = NaturezaRepository(repository_settings()).list_naturezas("0101")

    normalized_query = " ".join(cursor.query.split()).upper()
    assert "SED.D_E_L_E_T_ = ''" in normalized_query
    assert "SE7.D_E_L_E_T_ = ''" in normalized_query
    assert "ORDER BY SED.ED_CODIGO" in normalized_query
    assert [record.codigo for record in records] == ["A", "B"]


def test_repository_normalizes_char_fields_and_rejects_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        [(" 4.000-010 ", " MATÉRIA-PRIMA "), ("4.000-010", "OUTRA")],
    )

    with pytest.raises(AmbiguousNaturezaError, match="Multiple SED rows"):
        NaturezaRepository(repository_settings()).list_naturezas("0101")


def test_repository_handles_null_description_and_discards_empty_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(monkeypatch, [("A", None), (None, "Inválida"), ("   ", "Inválida")])

    records = NaturezaRepository(repository_settings()).list_naturezas("0101")

    assert records == [NaturezaRecord("A", "")]


def test_repository_returns_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_connection(monkeypatch, [])

    assert NaturezaRepository(repository_settings()).list_naturezas("0101") == []


def test_panel_filter_is_always_parameterized(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    NaturezaRepository(repository_settings()).list_naturezas("0101")

    assert "sed.ED_ZPAINEL = ?" in cursor.query
    assert cursor.parameters == ("0101", "02")


def test_se7_eligibility_has_no_year_or_month_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    NaturezaRepository(repository_settings()).list_naturezas("0101")

    normalized_query = " ".join(cursor.query.split()).upper()
    assert "E7_ANO" not in normalized_query
    assert "E7_MES" not in normalized_query
    assert "E7_EMISSAO" not in normalized_query
    assert "E7_VENCTO" not in normalized_query


def test_repository_requires_controlled_table_suffix() -> None:
    repository = NaturezaRepository(Settings(_env_file=None))

    with pytest.raises(DatabaseConfigurationError, match="suffix"):
        repository.list_naturezas("0101")


def test_repository_propagates_database_error_and_closes_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])

    def fail_execute(_query: str, *_parameters: object) -> None:
        raise DatabaseConnectionError("SQL Server is unavailable.")

    monkeypatch.setattr(cursor, "execute", fail_execute)

    with pytest.raises(DatabaseConnectionError, match="unavailable"):
        NaturezaRepository(repository_settings()).list_naturezas("0101")

    assert cursor.closed is True


def test_repository_does_not_contain_write_statements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    NaturezaRepository(repository_settings()).list_naturezas("0101")

    query_tokens = {token.upper() for token in cursor.query.split()}
    forbidden = {"INSERT", "UPDATE", "DELETE", "MERGE", "DROP", "ALTER", "TRUNCATE", "EXEC", "EXECUTE"}
    assert query_tokens.isdisjoint(forbidden)
    assert "SELECT *" not in cursor.query.upper()
    assert "NOLOCK" not in cursor.query.upper()


def test_blank_branch_is_rejected_before_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = install_fake_connection(monkeypatch, [])
    with pytest.raises(ValueError, match="filial"):
        NaturezaRepository(repository_settings()).list_naturezas("  ")
    assert cursor.query == ""
