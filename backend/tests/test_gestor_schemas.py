import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.gestor import GestorPeriod, GestorResponse, GestorRow


def make_row(**overrides: object) -> GestorRow:
    values: dict[str, object] = {
        "natureza_codigo": "4.000-010",
        "natureza_descricao": "MATÉRIA-PRIMA",
        "pc_aberto": Decimal("0.00"),
        "nf_entrada": Decimal("0.00"),
        "contingencia_ok": Decimal("0.00"),
        "contingencia_em_aprovacao": Decimal("0.00"),
        "limite_original": Decimal("0.00"),
        "saldo_previsto": Decimal("0.00"),
        "saldo_real": Decimal("0.00"),
    }
    values.update(overrides)
    return GestorRow(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("month", [1, 12])
def test_period_accepts_boundary_months(month: int) -> None:
    period = GestorPeriod(ano=2025, mes=month)
    assert period.mes == month


@pytest.mark.parametrize("month", [0, 13])
def test_period_rejects_month_outside_calendar(month: int) -> None:
    with pytest.raises(ValidationError):
        GestorPeriod(ano=2025, mes=month)


def test_row_accepts_zero_financial_values() -> None:
    row = make_row()
    assert row.pc_aberto == Decimal("0.00")
    assert row.limite_original == Decimal("0.00")


def test_row_accepts_negative_saldo_previsto() -> None:
    row = make_row(saldo_previsto=Decimal("-20.00"))
    assert row.saldo_previsto == Decimal("-20.00")


def test_row_accepts_negative_saldo_real() -> None:
    row = make_row(saldo_real=Decimal("-10.00"))
    assert row.saldo_real == Decimal("-10.00")


def test_response_accepts_empty_rows() -> None:
    response = GestorResponse(
        periodo=GestorPeriod(ano=2025, mes=9),
        filial="0101",
        linhas=[],
        quantidade=0,
    )
    assert response.linhas == []
    assert response.quantidade == 0


def test_response_requires_count_to_match_rows() -> None:
    with pytest.raises(ValidationError, match="quantidade"):
        GestorResponse(
            periodo=GestorPeriod(ano=2025, mes=9),
            filial="0101",
            linhas=[make_row()],
            quantidade=0,
        )


def test_financial_values_are_serialized_as_json_numbers() -> None:
    response = GestorResponse(
        periodo=GestorPeriod(ano=2025, mes=9),
        filial="0101",
        linhas=[make_row(pc_aberto=Decimal("40000.25"))],
        quantidade=1,
    )

    payload = json.loads(response.model_dump_json())

    assert payload["linhas"][0]["pcAberto"] == 40000.25
    assert isinstance(payload["linhas"][0]["pcAberto"], (int, float))
    assert payload["quantidade"] == len(payload["linhas"])
