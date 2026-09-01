from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import gestor as gestor_route
from app.core.config import GestorDataEnvironment
from app.core.database import DatabaseConnectionError
from app.main import app
from app.repositories.limite_repository import AmbiguousLimiteError
from app.schemas.gestor import GestorResponse
from app.services.gestor_service import get_gestor as get_mock_gestor
from app.services.gestor_service_provider import (
    GestorEnvironmentUnavailableError,
    MockGestorService,
)
from app.services.gestor_sql_service import (
    DuplicateGestorNaturezaError,
    UnexpectedGestorNaturezaError,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def use_dev_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gestor_route,
        "get_gestor_service",
        lambda _environment: MockGestorService(),
    )
    monkeypatch.setattr(
        gestor_route,
        "is_gestor_data_environment_available",
        lambda _environment: True,
    )


@pytest.mark.parametrize(
    ("month", "expected_count"),
    [(8, 18), (9, 20), (10, 22)],
)
def test_gestor_returns_mock_periods(month: int, expected_count: int) -> None:
    response = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": month, "filial": "0101"},
    )

    assert response.status_code == 200
    assert response.json()["quantidade"] == expected_count
    assert len(response.json()["linhas"]) == expected_count


def test_gestor_returns_empty_response_for_period_without_mock() -> None:
    response = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": 11, "filial": "0101"},
    )

    assert response.status_code == 200
    assert response.json()["linhas"] == []
    assert response.json()["quantidade"] == 0


def test_gestor_returns_empty_response_for_other_branch() -> None:
    response = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": 9, "filial": "9999"},
    )

    assert response.status_code == 200
    assert response.json()["filial"] == "9999"
    assert response.json()["linhas"] == []
    assert response.json()["quantidade"] == 0


def test_timeline_returns_one_month_per_point_and_matches_monthly_gestor() -> None:
    response = client.get(
        "/api/gestor/timeline",
        params={"ano": 2025, "mes": 9, "filial": "0101", "ambiente": "dev"},
    )

    assert response.status_code == 200
    points = response.json()
    assert [point["mes"] for point in points] == list(range(1, 10))
    assert len(points) == 9
    monthly = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": 9, "filial": "0101", "ambiente": "dev"},
    ).json()
    assert points[-1]["limiteTotal"] == sum(row["limiteTotal"] for row in monthly["linhas"])
    assert points[-1]["nfEntrada"] == sum(row["nfEntrada"] for row in monthly["linhas"])
    assert points[-1]["saldoPrevisto"] == sum(row["saldoPrevisto"] for row in monthly["linhas"])


def test_timeline_january_returns_one_point() -> None:
    response = client.get(
        "/api/gestor/timeline",
        params={"ano": 2025, "mes": 1, "filial": "0101", "ambiente": "dev"},
    )
    assert response.status_code == 200
    assert [point["mes"] for point in response.json()] == [1]


@pytest.mark.parametrize(
    "params",
    [
        {"ano": 2025, "mes": 0, "filial": "0101"},
        {"ano": 2025, "mes": 13, "filial": "0101"},
        {"ano": 1999, "mes": 9, "filial": "0101"},
        {"ano": 2025, "mes": 9, "filial": "   "},
    ],
)
def test_timeline_rejects_invalid_parameters(params: dict[str, Any]) -> None:
    assert client.get("/api/gestor/timeline", params=params).status_code == 422


def test_timeline_failure_is_sanitized_and_keeps_requested_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected: list[GestorDataEnvironment] = []

    class FailingService:
        def get_gestor(self, *_args: object, **_kwargs: object) -> GestorResponse:
            raise DatabaseConnectionError("sensitive database detail")

    def select(environment: GestorDataEnvironment) -> FailingService:
        selected.append(environment)
        return FailingService()

    monkeypatch.setattr(gestor_route, "get_gestor_service", select)
    response = client.get(
        "/api/gestor/timeline",
        params={"ano": 2025, "mes": 9, "filial": "0101", "ambiente": "prd"},
    )
    assert selected == [GestorDataEnvironment.PRD]
    assert response.status_code == 503
    assert response.json() == {"detail": "Gestor timeline is unavailable."}
    assert "sensitive" not in response.text


@pytest.mark.parametrize(
    "params",
    [
        {"ano": 2025, "mes": 0, "filial": "0101"},
        {"ano": 2025, "mes": 13, "filial": "0101"},
        {"ano": 1999, "mes": 9, "filial": "0101"},
        {"ano": 2101, "mes": 9, "filial": "0101"},
    ],
)
def test_gestor_rejects_invalid_numeric_parameters(params: dict[str, Any]) -> None:
    response = client.get("/api/gestor", params=params)
    assert response.status_code == 422


@pytest.mark.parametrize("filial", ["", "   "])
def test_gestor_rejects_empty_branch(filial: str) -> None:
    response = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": 9, "filial": filial},
    )
    assert response.status_code == 422


def test_gestor_normalizes_external_branch_spaces() -> None:
    response = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": 9, "filial": " 0101 "},
    )
    assert response.status_code == 200
    assert response.json()["filial"] == "0101"
    assert response.json()["quantidade"] == 20


def test_gestor_public_json_and_known_calculations() -> None:
    response = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": 9, "filial": "0101"},
    )
    payload = response.json()
    row = next(
        item
        for item in payload["linhas"]
        if item["naturezaCodigo"] == "4.000-040"
    )
    expected_keys = {
        "naturezaCodigo",
        "naturezaDescricao",
        "pcAberto",
        "nfEntrada",
        "contingenciaOk",
        "contingenciaEmAprovacao",
        "limiteOriginal",
        "limiteTotal",
        "saldoPrevisto",
        "saldoReal",
    }

    assert set(row) == expected_keys
    assert payload["quantidade"] == len(payload["linhas"])
    assert row["limiteTotal"] == row["limiteOriginal"] + row["contingenciaOk"]
    assert row["saldoPrevisto"] == (
        row["limiteTotal"] - row["pcAberto"] - row["nfEntrada"]
    )
    assert row["saldoReal"] == row["limiteTotal"] - row["nfEntrada"]
    assert row["saldoPrevisto"] < 0
    assert all(
        isinstance(row[field], (int, float))
        for field in expected_keys - {"naturezaCodigo", "naturezaDescricao"}
    )
    assert not any("_" in key for key in row)
    assert not any(
        key.startswith(("C7_", "E2_", "EV_", "ZN_", "ZR_", "E7_"))
        for key in row
    )


def test_gestor_preserves_exactly_committed_reference_row() -> None:
    response = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": 9, "filial": "0101"},
    )
    row = next(
        item
        for item in response.json()["linhas"]
        if item["naturezaCodigo"] == "4.000-030"
    )

    assert row["pcAberto"] + row["nfEntrada"] == row["limiteTotal"]
    assert row["saldoPrevisto"] == 0


def test_hml_service_receives_query_and_returns_same_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSqlService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int]] = []

        def get_gestor(self, filial: str, ano: int, mes: int) -> GestorResponse:
            self.calls.append((filial, ano, mes))
            return get_mock_gestor(filial=filial, ano=ano, mes=mes)

    service = FakeSqlService()
    selected: list[GestorDataEnvironment] = []

    def select_service(environment: GestorDataEnvironment) -> FakeSqlService:
        selected.append(environment)
        return service

    monkeypatch.setattr(gestor_route, "get_gestor_service", select_service)

    response = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": 9, "filial": " 0101 "},
    )

    assert response.status_code == 200
    assert selected == [GestorDataEnvironment.HML]
    assert service.calls == [("0101", 2025, 9)]
    assert response.json()["quantidade"] == 20
    assert set(response.json()) == {"periodo", "filial", "linhas", "quantidade"}


@pytest.mark.parametrize(
    "error",
    [
        DatabaseConnectionError("sensitive driver detail"),
        UnexpectedGestorNaturezaError("repository", "999"),
        DuplicateGestorNaturezaError("repository", "001"),
        AmbiguousLimiteError("sensitive table detail"),
    ],
)
def test_hml_failures_are_sanitized_without_mock_fallback(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    class FailingSqlService:
        def get_gestor(self, filial: str, ano: int, mes: int) -> GestorResponse:
            raise error

    monkeypatch.setattr(
        gestor_route,
        "get_gestor_service",
        lambda _environment: FailingSqlService(),
    )
    response = client.get(
        "/api/gestor",
        params={"ano": 2025, "mes": 9, "filial": "0101"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Gestor data source is unavailable."}
    assert "sensitive" not in response.text
    assert "linhas" not in response.json()


def test_prd_block_is_sanitized_and_does_not_return_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(environment: GestorDataEnvironment) -> MockGestorService:
        assert environment is GestorDataEnvironment.PRD
        raise GestorEnvironmentUnavailableError("sensitive configuration detail")

    monkeypatch.setattr(
        gestor_route,
        "get_gestor_service",
        unavailable,
    )
    response = client.get(
        "/api/gestor",
        params={
            "ano": 2025,
            "mes": 9,
            "filial": "0101",
            "ambiente": "prd",
        },
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Gestor data source is unavailable."}


def test_prd_enabled_uses_sql_service_and_keeps_public_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePrdSqlService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int]] = []

        def get_gestor(self, filial: str, ano: int, mes: int) -> GestorResponse:
            self.calls.append((filial, ano, mes))
            return get_mock_gestor(filial=filial, ano=ano, mes=mes)

    service = FakePrdSqlService()

    def select_service(environment: GestorDataEnvironment) -> FakePrdSqlService:
        assert environment is GestorDataEnvironment.PRD
        return service

    monkeypatch.setattr(
        gestor_route,
        "get_gestor_service",
        select_service,
    )

    response = client.get(
        "/api/gestor",
        params={
            "ano": 2025,
            "mes": 9,
            "filial": " 0101 ",
            "ambiente": "prd",
        },
    )

    assert response.status_code == 200
    assert service.calls == [("0101", 2025, 9)]
    assert set(response.json()) == {"periodo", "filial", "linhas", "quantidade"}


def test_gestor_rejects_invalid_data_environment() -> None:
    response = client.get(
        "/api/gestor",
        params={
            "ano": 2025,
            "mes": 9,
            "filial": "0101",
            "ambiente": "production",
        },
    )

    assert response.status_code == 422


def test_environment_capabilities_are_sanitized() -> None:
    response = client.get("/api/gestor/environments")

    assert response.status_code == 200
    assert response.json() == {
        "default": "prd",
        "environments": [
            {"id": "dev", "label": "DEV", "available": True},
            {"id": "hml", "label": "HML", "available": True},
            {"id": "prd", "label": "PRD", "available": True},
        ],
    }
    assert not any(
        sensitive in response.text.lower()
        for sensitive in ("password", "server", "database", "driver", "user")
    )


def test_environment_capabilities_report_unavailable_prd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gestor_route,
        "is_gestor_data_environment_available",
        lambda environment: environment is not GestorDataEnvironment.PRD,
    )

    response = client.get("/api/gestor/environments")

    assert response.status_code == 200
    assert response.json()["environments"][2] == {
        "id": "prd",
        "label": "PRD",
        "available": False,
    }
    assert response.json()["default"] == "hml"


def test_environment_capabilities_use_dev_when_sql_sources_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gestor_route,
        "is_gestor_data_environment_available",
        lambda environment: environment is GestorDataEnvironment.DEV,
    )

    response = client.get("/api/gestor/environments")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default"] == "dev"
    assert next(
        option for option in payload["environments"] if option["id"] == "dev"
    )["available"] is True


def test_environment_capabilities_default_is_always_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    available = {GestorDataEnvironment.DEV, GestorDataEnvironment.HML}
    monkeypatch.setattr(
        gestor_route,
        "is_gestor_data_environment_available",
        lambda environment: environment in available,
    )

    payload = client.get("/api/gestor/environments").json()
    selected = next(
        option
        for option in payload["environments"]
        if option["id"] == payload["default"]
    )

    assert selected["available"] is True


def test_openapi_keeps_gestor_response_contract() -> None:
    operation = client.get("/openapi.json").json()["paths"]["/api/gestor"]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response_schema["$ref"].endswith("/GestorResponse")


@pytest.mark.parametrize(
    ("tipo", "natureza", "expected_total", "expected_count"),
    [
        ("pc_aberto", "4.000-010", 40000, 2),
        ("nf_entrada", "4.000-010", 30000, 1),
        ("contingencia_ok", "4.000-010", 10000, 2),
        ("contingencia_aprovacao", "4.000-020", 5000, 2),
        ("pc_aberto", "4.000-020", 0, 0),
        ("contingencia_ok", "4.000-020", 0, 0),
    ],
)
def test_dev_detail_matches_consolidated_total(
    tipo: str, natureza: str, expected_total: float, expected_count: int
) -> None:
    response = client.get(
        "/api/gestor/details",
        params={
            "ambiente": "dev", "filial": "0101", "ano": 2025, "mes": 9,
            "natureza": natureza, "tipo": tipo,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ambiente"] == "dev"
    assert payload["tipo"] == tipo
    assert payload["quantidade"] == expected_count == len(payload["registros"])
    assert payload["total"] == expected_total
    assert sum(record["valor"] for record in payload["registros"]) == expected_total
    if tipo == "nf_entrada" and payload["registros"]:
        record = payload["registros"][0]
        assert record["fornecedor"] == "000001"
        assert record["fornecedorNome"] == "Fornecedor Exemplo DEV"
        assert record["emissao"] == "20250905"
    if tipo.startswith("contingencia_") and payload["registros"]:
        assert set(payload["registros"][0]) == {
            "pedido", "item", "vencimento", "usuario", "status", "valor"
        }
        expected_status = "OK" if tipo == "contingencia_ok" else "Em aprovação"
        assert {record["status"] for record in payload["registros"]} == {
            expected_status
        }


@pytest.mark.parametrize("tipo", ["pc", "nf", "limite", ""])
def test_detail_rejects_invalid_type(tipo: str) -> None:
    response = client.get(
        "/api/gestor/details",
        params={
            "ambiente": "dev", "filial": "0101", "ano": 2025, "mes": 9,
            "natureza": "4.000-010", "tipo": tipo,
        },
    )
    assert response.status_code == 422


def test_detail_requires_explicit_environment() -> None:
    response = client.get(
        "/api/gestor/details",
        params={
            "filial": "0101", "ano": 2025, "mes": 9,
            "natureza": "4.000-010", "tipo": "pc_aberto",
        },
    )
    assert response.status_code == 422


def test_openapi_exposes_typed_detail_contract() -> None:
    operation = client.get("/openapi.json").json()["paths"]["/api/gestor/details"]["get"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/GestorDetailResponse")
