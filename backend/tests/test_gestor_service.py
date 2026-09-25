from app.services.gestor_service import get_gestor


def test_service_returns_existing_period_with_derived_count() -> None:
    response = get_gestor(ano=2025, mes=8, filial="0101")
    assert response.quantidade == 18
    assert response.quantidade == len(response.linhas)


def test_service_returns_empty_period() -> None:
    response = get_gestor(ano=2025, mes=11, filial="0101")
    assert response.linhas == []
    assert response.quantidade == 0


def test_service_returns_empty_other_branch() -> None:
    response = get_gestor(ano=2025, mes=9, filial="9999")
    assert response.linhas == []
    assert response.quantidade == 0


def test_service_rows_keep_financial_formulas_consistent() -> None:
    for month in (8, 9, 10):
        response = get_gestor(ano=2025, mes=month, filial="0101")
        for row in response.linhas:
            assert row.saldo_previsto == (
                row.limite_original - row.pc_aberto - row.nf_entrada
            )
            assert row.saldo_real == row.limite_original - row.nf_entrada
