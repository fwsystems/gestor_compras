from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from app.core.config import AppEnvironment, Settings
from scripts.diagnose_gestor_natureza_hml import (
    HmlDiagnosisError,
    build_parser,
    format_diagnosis,
    run_diagnosis,
)


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.description = [("FIELD",)]
        self.closed = False

    def execute(self, query: str, *parameters: object) -> None:
        self.executions.append((query, parameters))
        self.description = [("COLUMN_NAME",)] if "INFORMATION_SCHEMA" in query else [("FIELD",)]

    def fetchall(self) -> list[tuple[object, ...]]:
        return []

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


def fake_factory(cursor: FakeCursor):
    @contextmanager
    def connection(_settings: Settings) -> Iterator[FakeConnection]:
        yield FakeConnection(cursor)

    return connection


@pytest.mark.parametrize("environment", [AppEnvironment.DEV, AppEnvironment.PRD])
def test_runner_blocks_non_hml_before_connection(environment: AppEnvironment) -> None:
    called = False

    @contextmanager
    def connection(_settings: Settings) -> Iterator[FakeConnection]:
        nonlocal called
        called = True
        yield FakeConnection(FakeCursor())

    with pytest.raises(HmlDiagnosisError, match="only in HML"):
        run_diagnosis(settings(environment), "0101", 2026, 7, "4.000-460", connection)
    assert called is False


@pytest.mark.parametrize(
    ("filial", "ano", "mes", "natureza"),
    [("", 2026, 7, "4.000-460"), ("0101", 1999, 7, "4.000-460"), ("0101", 2026, 13, "4.000-460"), ("0101", 2026, 7, "")],
)
def test_runner_requires_valid_inputs(
    filial: str, ano: int, mes: int, natureza: str
) -> None:
    with pytest.raises(ValueError):
        run_diagnosis(settings(), filial, ano, mes, natureza)


def test_parser_requires_every_diagnostic_argument() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_hml_queries_are_select_only_parameterized_and_close_cursor() -> None:
    cursor = FakeCursor()
    diagnosis = run_diagnosis(
        settings(),
        " 0101 ",
        2026,
        7,
        " 4.000-460 ",
        fake_factory(cursor),
    )

    assert diagnosis.filial == "0101"
    assert diagnosis.natureza == "4.000-460"
    assert cursor.closed is True
    assert len(cursor.executions) == 8
    forbidden = {"INSERT", "UPDATE", "DELETE", "MERGE", "CREATE", "ALTER", "DROP", "TRUNCATE", "EXEC", "EXECUTE"}
    for query, _parameters in cursor.executions:
        normalized = " ".join(query.split()).upper()
        assert normalized.startswith("SELECT")
        assert "SELECT *" not in normalized
        assert "NOLOCK" not in normalized
        assert set(normalized.replace("(", " ").replace(")", " ").split()).isdisjoint(forbidden)

    operational = cursor.executions[4:7]
    assert operational[0][1] == ("0101", "4.000-460", "202607%")
    assert operational[1][1] == ("0101", "4.000-460", "202607%", "E", "X", "1")
    assert operational[2][1][:2] == ("0101", "4.000-460")
    assert all(value == "202607%" for value in operational[2][1][2:])
    assert "4.000-460" not in " ".join(query for query, _ in operational)


def test_output_does_not_expose_database_configuration_or_secrets() -> None:
    cursor = FakeCursor()
    diagnosis = run_diagnosis(
        settings(), "0101", 2026, 7, "4.000-460", fake_factory(cursor)
    )
    output = format_diagnosis(diagnosis)
    for secret in ("password", "connection string", "db_host", "db_user"):
        assert secret not in output.lower()
