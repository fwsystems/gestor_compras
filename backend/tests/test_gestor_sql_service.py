from decimal import Decimal

import pytest

from app.core.config import GestorDataEnvironment
from app.core.database import DatabaseConnectionError
from app.repositories.contingencia_repository import (
    ContingenciaDetailRecord,
    ContingenciaRecord,
)
from app.repositories.limite_repository import AmbiguousLimiteError, LimiteRecord
from app.repositories.natureza_repository import NaturezaRecord
from app.repositories.nf_entrada_repository import NfEntradaDetailRecord, NfEntradaRecord
from app.repositories.pc_aberto_repository import PcAbertoDetailRecord, PcAbertoRecord
from app.schemas.gestor import GestorDetailType
from app.services.gestor_sql_service import (
    DuplicateGestorNaturezaError,
    GestorDetailInconsistencyError,
    GestorSqlService,
    UnexpectedGestorNaturezaError,
)


class FakeRepository:
    def __init__(
        self,
        records: list[object],
        error: Exception | None = None,
        detail_records: list[object] | None = None,
    ) -> None:
        self.records = records
        self.detail_records = detail_records or []
        self.error = error
        self.calls: list[tuple[object, ...]] = []

    def _return(self, args: tuple[object, ...]) -> list[object]:
        self.calls.append(args)
        if self.error is not None:
            raise self.error
        return self.records

    def list_naturezas(self, filial: str) -> list[object]:
        return self._return((filial,))

    def list_limites(self, filial: str, ano: int, mes: int) -> list[object]:
        return self._return((filial, ano, mes))

    def list_pc_aberto(self, filial: str, ano: int, mes: int) -> list[object]:
        return self._return((filial, ano, mes))

    def list_nf_entrada(self, filial: str, ano: int, mes: int) -> list[object]:
        return self._return((filial, ano, mes))

    def list_contingencias(self, filial: str, ano: int, mes: int) -> list[object]:
        return self._return((filial, ano, mes))

    def list_pc_aberto_details(
        self, filial: str, ano: int, mes: int, natureza: str
    ) -> list[object]:
        self.calls.append((filial, ano, mes, natureza))
        return self.detail_records

    def list_nf_entrada_details(
        self, filial: str, ano: int, mes: int, natureza: str
    ) -> list[object]:
        self.calls.append((filial, ano, mes, natureza))
        return self.detail_records

    def list_contingencia_ok_details(
        self, filial: str, ano: int, mes: int, natureza: str
    ) -> list[object]:
        self.calls.append((filial, ano, mes, natureza, "ok"))
        return self.detail_records

    def list_contingencia_aprovacao_details(
        self, filial: str, ano: int, mes: int, natureza: str
    ) -> list[object]:
        self.calls.append((filial, ano, mes, natureza, "approval"))
        return self.detail_records


def build_service(
    naturezas: list[object] | None = None,
    limites: list[object] | None = None,
    pcs: list[object] | None = None,
    nfs: list[object] | None = None,
    contingencias: list[object] | None = None,
    errors: dict[str, Exception] | None = None,
) -> tuple[GestorSqlService, dict[str, FakeRepository]]:
    errors = errors or {}
    repositories = {
        "natureza": FakeRepository(naturezas or [], errors.get("natureza")),
        "limite": FakeRepository(limites or [], errors.get("limite")),
        "pc": FakeRepository(pcs or [], errors.get("pc")),
        "nf": FakeRepository(nfs or [], errors.get("nf")),
        "contingencia": FakeRepository(
            contingencias or [], errors.get("contingencia")
        ),
    }
    service = GestorSqlService(
        natureza_repository=repositories["natureza"],  # type: ignore[arg-type]
        limite_repository=repositories["limite"],  # type: ignore[arg-type]
        pc_aberto_repository=repositories["pc"],  # type: ignore[arg-type]
        nf_entrada_repository=repositories["nf"],  # type: ignore[arg-type]
        contingencia_repository=repositories["contingencia"],  # type: ignore[arg-type]
    )
    return service, repositories


def test_each_repository_is_called_once_with_the_same_query() -> None:
    service, repositories = build_service()
    response = service.get_gestor(" 0101 ", 2026, 7)
    assert repositories["natureza"].calls == [("0101",)]
    for source in ("limite", "pc", "nf", "contingencia"):
        assert repositories[source].calls == [("0101", 2026, 7)]
    assert response.filial == "0101"
    assert (response.periodo.ano, response.periodo.mes) == (2026, 7)


def test_complete_deterministic_composition_and_pending_is_informational() -> None:
    service, _ = build_service(
        naturezas=[NaturezaRecord("0010", "NATUREZA TESTE")],
        limites=[LimiteRecord("0010", 2025, 9, Decimal("1000.00"))],
        pcs=[PcAbertoRecord("0010", Decimal("250.00"))],
        nfs=[NfEntradaRecord("0010", Decimal("100.00"))],
        contingencias=[
            ContingenciaRecord("0010", Decimal("200.00"), Decimal("500.00"))
        ],
    )
    response = service.get_gestor("0101", 2025, 9)
    row = response.linhas[0]
    assert row.natureza_codigo == "0010"
    assert row.natureza_descricao == "NATUREZA TESTE"
    assert row.limite_total == Decimal("1200.00")
    assert row.saldo_previsto == Decimal("850.00")
    assert row.saldo_real == Decimal("1100.00")
    assert row.contingencia_em_aprovacao == Decimal("500.00")
    assert response.quantidade == 1


def test_financial_union_is_sorted_and_sed_only_nature_is_omitted() -> None:
    service, _ = build_service(
        naturezas=[
            NaturezaRecord("003", "SOMENTE CADASTRO"),
            NaturezaRecord("002", "SEGUNDA"),
            NaturezaRecord("001", "PRIMEIRA"),
        ],
        limites=[LimiteRecord("002", 2025, 9, Decimal("0"))],
        pcs=[PcAbertoRecord("001", Decimal("-2.50"))],
    )
    response = service.get_gestor("0101", 2025, 9)
    assert [row.natureza_codigo for row in response.linhas] == ["001", "002"]
    first, second = response.linhas
    for value in (
        second.pc_aberto,
        second.nf_entrada,
        second.contingencia_ok,
        second.contingencia_em_aprovacao,
    ):
        assert value == Decimal("0") and isinstance(value, Decimal)
    assert first.pc_aberto == Decimal("-2.50")
    assert first.saldo_previsto == Decimal("2.50")


def test_catalog_without_financial_records_produces_empty_response() -> None:
    service, _ = build_service(naturezas=[NaturezaRecord("001", "CADASTRO")])
    response = service.get_gestor("0101", 2025, 9)
    assert response.linhas == []
    assert response.quantidade == 0


@pytest.mark.parametrize(
    ("source", "records"),
    [
        ("limite", [LimiteRecord("999", 2025, 9, Decimal("1"))]),
        ("pc", [PcAbertoRecord("999", Decimal("1"))]),
        ("nf", [NfEntradaRecord("999", Decimal("1"))]),
        ("contingencia", [ContingenciaRecord("999", Decimal("1"), Decimal("2"))]),
    ],
)
def test_financial_nature_outside_panel_is_ignored(
    source: str, records: list[object]
) -> None:
    kwargs = {source + ("s" if source in {"limite", "pc", "nf"} else "s"): records}
    service, _ = build_service(
        naturezas=[NaturezaRecord("001", "BASE")],
        **kwargs,  # type: ignore[arg-type]
    )
    response = service.get_gestor("0101", 2025, 9)
    assert response.linhas == []
    assert response.quantidade == 0


@pytest.mark.parametrize(
    ("source", "records", "expected_field"),
    [
        ("limites", [LimiteRecord("001", 2025, 9, Decimal("10"))], "limite_original"),
        ("pcs", [PcAbertoRecord("001", Decimal("10"))], "pc_aberto"),
        ("nfs", [NfEntradaRecord("001", Decimal("10"))], "nf_entrada"),
        (
            "contingencias",
            [ContingenciaRecord("001", Decimal("10"), Decimal("20"))],
            "contingencia_ok",
        ),
    ],
)
def test_each_financial_source_can_make_catalog_nature_relevant(
    source: str, records: list[object], expected_field: str
) -> None:
    service, _ = build_service(
        naturezas=[NaturezaRecord("001", "DESCRIÇÃO SED")],
        **{source: records},  # type: ignore[arg-type]
    )
    response = service.get_gestor("0101", 2025, 9)
    assert response.quantidade == 1
    assert response.linhas[0].natureza_descricao == "DESCRIÇÃO SED"
    assert getattr(response.linhas[0], expected_field) == Decimal("10")


def test_real_hml_regression_nf_outside_panel_does_not_create_row() -> None:
    service, _ = build_service(
        nfs=[NfEntradaRecord("5.000-350", Decimal("1000.00"))],
    )
    response = service.get_gestor("0101", 2025, 9)
    assert response.linhas == []
    assert response.quantidade == 0


def test_panel_nature_with_historical_se7_and_no_current_limit_is_valid() -> None:
    service, _ = build_service(
        naturezas=[NaturezaRecord("5.000-400", "NATUREZA DO PAINEL")],
        nfs=[NfEntradaRecord("5.000-400", Decimal("220.00"))],
    )
    response = service.get_gestor("0101", 2025, 9)
    row = response.linhas[0]
    assert row.natureza_codigo == "5.000-400"
    assert row.natureza_descricao == "NATUREZA DO PAINEL"
    assert row.limite_original == Decimal("0")
    assert row.nf_entrada == Decimal("220.00")
    assert row.saldo_previsto == Decimal("-220.00")


@pytest.mark.parametrize(
    ("source", "records"),
    [
        ("limites", [LimiteRecord("001", 2025, 9, Decimal("1"))] * 2),
        ("pcs", [PcAbertoRecord("001", Decimal("1"))] * 2),
        ("nfs", [NfEntradaRecord("001", Decimal("1"))] * 2),
        (
            "contingencias",
            [ContingenciaRecord("001", Decimal("1"), Decimal("2"))] * 2,
        ),
    ],
)
def test_duplicate_financial_nature_raises(
    source: str, records: list[object]
) -> None:
    service, _ = build_service(
        naturezas=[NaturezaRecord("001", "BASE")],
        **{source: records},  # type: ignore[arg-type]
    )
    with pytest.raises(DuplicateGestorNaturezaError) as captured:
        service.get_gestor("0101", 2025, 9)
    assert captured.value.natureza == "001"


def test_empty_financial_nature_is_an_inconsistency() -> None:
    service, _ = build_service(
        naturezas=[NaturezaRecord("001", "BASE")],
        pcs=[PcAbertoRecord(" ", Decimal("1"))],
    )
    with pytest.raises(UnexpectedGestorNaturezaError) as captured:
        service.get_gestor("0101", 2025, 9)
    assert captured.value.natureza == ""


@pytest.mark.parametrize(
    "source", ["natureza", "limite", "pc", "nf", "contingencia"]
)
def test_repository_errors_are_propagated(source: str) -> None:
    error: Exception
    if source == "limite":
        error = AmbiguousLimiteError("ambiguous")
    else:
        error = DatabaseConnectionError("unavailable")
    service, _ = build_service(errors={source: error})
    with pytest.raises(type(error), match=str(error)):
        service.get_gestor("0101", 2025, 9)


@pytest.mark.parametrize(("filial", "ano", "mes"), [(" ", 2025, 9), ("0101", 1999, 9), ("0101", 2025, 13)])
def test_invalid_input_is_rejected_before_repositories(
    filial: str, ano: int, mes: int
) -> None:
    service, repositories = build_service()
    with pytest.raises(ValueError):
        service.get_gestor(filial, ano, mes)
    assert all(repository.calls == [] for repository in repositories.values())


def test_pc_detail_matches_consolidated_and_uses_catalog_description() -> None:
    service, repositories = build_service(
        naturezas=[NaturezaRecord("001", "NATUREZA TESTE")],
        pcs=[PcAbertoRecord("001", Decimal("100"))],
    )
    repositories["pc"].detail_records = [
        PcAbertoDetailRecord("10", "20250910", "001", Decimal("40")),
        PcAbertoDetailRecord("11", "20250920", "001", Decimal("60")),
    ]
    response = service.get_details(
        ambiente=GestorDataEnvironment.PRD,
        filial=" 0101 ", ano=2025, mes=9, natureza=" 001 ",
        tipo=GestorDetailType.PC_ABERTO,
    )
    assert response.ambiente is GestorDataEnvironment.PRD
    assert response.natureza_descricao == "NATUREZA TESTE"
    assert response.total == Decimal("100")
    assert response.quantidade == 2
    assert repositories["pc"].calls == [
        ("0101", 2025, 9), ("0101", 2025, 9, "001")
    ]
    assert repositories["nf"].calls == []


def test_nf_detail_exposes_enriched_confirmed_fields() -> None:
    service, repositories = build_service(
        naturezas=[NaturezaRecord("001", "NATUREZA TESTE")],
        nfs=[NfEntradaRecord("001", Decimal("75.50"))],
    )
    repositories["nf"].detail_records = [
        NfEntradaDetailRecord(
            "123", "NF", "1", "000001", "FORNECEDOR TESTE", "01",
            "20250901", "20250925", "001", Decimal("75.50"),
        )
    ]
    response = service.get_details(
        ambiente=GestorDataEnvironment.HML,
        filial="0101", ano=2025, mes=9, natureza="001",
        tipo=GestorDetailType.NF_ENTRADA,
    )
    record = response.registros[0].model_dump(by_alias=True)
    assert set(record) == {
        "documento", "prefixo", "parcela", "fornecedor", "fornecedorNome",
        "loja", "emissao", "vencimento", "valor"
    }
    assert record["fornecedor"] == "000001"
    assert record["fornecedorNome"] == "FORNECEDOR TESTE"
    assert record["emissao"] == "20250901"
    assert response.total == Decimal("75.50")


@pytest.mark.parametrize(
    "details",
    [
        [],
        [PcAbertoDetailRecord("10", "20250910", "001", Decimal("99"))],
        [PcAbertoDetailRecord("10", "20250910", "999", Decimal("100"))],
    ],
)
def test_pc_detail_inconsistency_is_rejected(details: list[PcAbertoDetailRecord]) -> None:
    service, repositories = build_service(
        naturezas=[NaturezaRecord("001", "NATUREZA TESTE")],
        pcs=[PcAbertoRecord("001", Decimal("100"))],
    )
    repositories["pc"].detail_records = details
    with pytest.raises(GestorDetailInconsistencyError):
        service.get_details(
            ambiente=GestorDataEnvironment.HML,
            filial="0101", ano=2025, mes=9, natureza="001",
            tipo=GestorDetailType.PC_ABERTO,
        )


def test_zero_consolidated_accepts_empty_detail() -> None:
    service, _ = build_service(naturezas=[NaturezaRecord("001", "ZERO")])
    response = service.get_details(
        ambiente=GestorDataEnvironment.HML,
        filial="0101", ano=2025, mes=9, natureza="001",
        tipo=GestorDetailType.PC_ABERTO,
    )
    assert response.total == 0
    assert response.quantidade == 0


@pytest.mark.parametrize(
    ("tipo", "expected_total", "status", "call_suffix"),
    [
        (GestorDetailType.CONTINGENCIA_OK, Decimal("100"), "OK", "ok"),
        (
            GestorDetailType.CONTINGENCIA_APROVACAO,
            Decimal("60"),
            "Em aprovação",
            "approval",
        ),
    ],
)
def test_contingency_detail_is_independent_and_matches_consolidated(
    tipo: GestorDetailType,
    expected_total: Decimal,
    status: str,
    call_suffix: str,
) -> None:
    service, repositories = build_service(
        naturezas=[NaturezaRecord("001", "CONTINGÊNCIA TESTE")],
        contingencias=[ContingenciaRecord("001", Decimal("100"), Decimal("60"))],
    )
    repositories["contingencia"].detail_records = [
        ContingenciaDetailRecord(
            "10", "01", "20250910", "USR1", status, "001",
            expected_total / 2,
        ),
        ContingenciaDetailRecord(
            "11", "02", "20250920", "USR2", status, "001",
            expected_total / 2,
        ),
    ]

    response = service.get_details(
        ambiente=GestorDataEnvironment.PRD,
        filial="0101", ano=2025, mes=9, natureza="001", tipo=tipo,
    )

    assert response.total == expected_total
    assert response.quantidade == 2
    assert {record.status for record in response.registros} == {status}  # type: ignore[union-attr]
    assert repositories["contingencia"].calls == [
        ("0101", 2025, 9),
        ("0101", 2025, 9, "001", call_suffix),
    ]
    assert repositories["pc"].calls == []
    assert repositories["nf"].calls == []


@pytest.mark.parametrize(
    "tipo",
    [
        GestorDetailType.CONTINGENCIA_OK,
        GestorDetailType.CONTINGENCIA_APROVACAO,
    ],
)
def test_contingency_detail_inconsistency_is_rejected(
    tipo: GestorDetailType,
) -> None:
    service, repositories = build_service(
        naturezas=[NaturezaRecord("001", "CONTINGÊNCIA TESTE")],
        contingencias=[ContingenciaRecord("001", Decimal("100"), Decimal("60"))],
    )
    repositories["contingencia"].detail_records = [
        ContingenciaDetailRecord(
            "10", "01", "20250910", "USR", "STATUS", "001", Decimal("1")
        )
    ]
    with pytest.raises(GestorDetailInconsistencyError):
        service.get_details(
            ambiente=GestorDataEnvironment.HML,
            filial="0101", ano=2025, mes=9, natureza="001", tipo=tipo,
        )
