from fastapi.testclient import TestClient
import pytest

from app.api.routes import database as database_route
from app.core.database import DatabaseConfigurationError, DatabaseConnectionError
from app.main import app

client = TestClient(app)


def test_database_health_returns_ok_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(database_route, "check_database_connection", lambda: None)

    response = client.get("/api/database/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "sqlserver"}


@pytest.mark.parametrize(
    "error",
    [
        DatabaseConfigurationError("configuration detail"),
        DatabaseConnectionError("connection detail"),
    ],
)
def test_database_health_returns_sanitized_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    def fail() -> None:
        raise error

    monkeypatch.setattr(database_route, "check_database_connection", fail)

    response = client.get("/api/database/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "sqlserver"}
    forbidden = {"host", "user", "password", "driver", "connection_string"}
    assert forbidden.isdisjoint(response.json())
