from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


client = TestClient(app)


def test_application_info_uses_configured_environment() -> None:
    response = client.get("/api/info")

    assert response.status_code == 200
    assert response.json() == {
        "application": "gestor-compras-web",
        "environment": get_settings().app_env.value,
        "version": "0.1.0",
    }


def test_public_endpoints_do_not_expose_sensitive_configuration() -> None:
    forbidden_keys = {
        "db_host",
        "db_port",
        "db_name",
        "db_user",
        "db_password",
        "db_driver",
        "connection_string",
        "token",
        "secret",
    }

    for path in ("/health", "/api/info"):
        response = client.get(path)
        assert response.status_code == 200
        assert forbidden_keys.isdisjoint(response.json())
