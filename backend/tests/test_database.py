from collections.abc import Iterator
from contextlib import contextmanager
import pyodbc
import pytest

from app.core import database
from app.core.config import Settings
from app.core.database import (
    DatabaseConfigurationError,
    DatabaseConnectionConfig,
    DatabaseConnectionError,
)


def complete_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "db_host": "sql-hml.example.invalid",
        "db_port": 1433,
        "db_name": "protheus_hml",
        "db_user": "readonly_user",
        "db_password": "private-password",
        "db_driver": "ODBC Driver Test",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


class FakeCursor:
    def __init__(self, result: tuple[int] | None = (1,)) -> None:
        self.result = result
        self.executed: list[str] = []
        self.closed = False

    def execute(self, statement: str) -> None:
        self.executed.append(statement)

    def fetchone(self) -> tuple[int] | None:
        return self.result

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor | None = None) -> None:
        self.timeout = 0
        self.closed = False
        self.fake_cursor = cursor or FakeCursor()

    def cursor(self) -> FakeCursor:
        return self.fake_cursor

    def close(self) -> None:
        self.closed = True


def test_incomplete_configuration_is_checked_only_when_requested() -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(DatabaseConfigurationError, match="incomplete"):
        database.get_database_config(settings)


def test_complete_configuration_preserves_driver_tls_and_timeouts() -> None:
    config = database.get_database_config(
        complete_settings(
            db_connect_timeout=7,
            db_query_timeout=45,
            db_encrypt=False,
            db_trust_server_certificate=True,
            db_application_intent_read_only=True,
        )
    )

    assert config.driver == "ODBC Driver Test"
    assert config.connect_timeout == 7
    assert config.query_timeout == 45
    assert config.encrypt is False
    assert config.trust_server_certificate is True
    assert config.application_intent_read_only is True


def test_password_is_hidden_from_config_representation() -> None:
    config = database.get_database_config(complete_settings())

    assert "private-password" not in repr(config)


def test_connection_string_uses_configured_options() -> None:
    config = DatabaseConnectionConfig(
        driver="ODBC Driver Test",
        host="sql-hml.example.invalid",
        port=1433,
        database="protheus_hml",
        user="readonly_user",
        password="private-password",
        encrypt=True,
        trust_server_certificate=False,
        application_intent_read_only=True,
    )

    connection_string = database.build_connection_string(config)

    assert "DRIVER={ODBC Driver Test}" in connection_string
    assert "SERVER={sql-hml.example.invalid,1433}" in connection_string
    assert "Encrypt=yes" in connection_string
    assert "TrustServerCertificate=no" in connection_string
    assert "ApplicationIntent=ReadOnly" in connection_string


def test_connection_applies_timeouts_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_connection = FakeConnection()
    received: dict[str, object] = {}

    def fake_connect(connection_string: str, **kwargs: object) -> FakeConnection:
        received["connection_string"] = connection_string
        received.update(kwargs)
        return fake_connection

    monkeypatch.setattr(database.pyodbc, "connect", fake_connect)

    with database.get_database_connection(
        complete_settings(db_connect_timeout=7, db_query_timeout=45)
    ) as connection:
        assert connection is fake_connection
        assert fake_connection.timeout == 45

    assert received["timeout"] == 7
    assert received["autocommit"] is True
    assert fake_connection.closed is True


def test_connection_is_closed_when_consumer_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_connection = FakeConnection()
    monkeypatch.setattr(database.pyodbc, "connect", lambda *_args, **_kwargs: fake_connection)

    with pytest.raises(RuntimeError, match="consumer failure"):
        with database.get_database_connection(complete_settings()):
            raise RuntimeError("consumer failure")

    assert fake_connection.closed is True


def test_connection_error_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_connect(*_args: object, **_kwargs: object) -> None:
        raise pyodbc.Error("private-password login failed")

    monkeypatch.setattr(database.pyodbc, "connect", fail_connect)

    with pytest.raises(DatabaseConnectionError) as captured:
        with database.get_database_connection(complete_settings()):
            pass

    assert "private-password" not in str(captured.value)


def test_technical_check_executes_only_select_one(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)

    @contextmanager
    def fake_connection_context(_settings: Settings | None = None) -> Iterator[object]:
        yield connection

    monkeypatch.setattr(database, "get_database_connection", fake_connection_context)

    database.check_database_connection(complete_settings())

    assert cursor.executed == ["SELECT 1"]
    assert cursor.closed is True
