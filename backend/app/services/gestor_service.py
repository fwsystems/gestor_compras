from app.mocks.gestor import GESTOR_MOCKS
from decimal import Decimal
from datetime import date

from app.core.config import GestorDataEnvironment
from app.schemas.gestor import (
    GestorContingenciaDetailRecord,
    GestorDetailResponse,
    GestorDetailType,
    GestorNfEntradaDetailRecord,
    GestorPcAbertoDetailRecord,
    GestorPeriod,
    GestorRow,
    GestorResponse,
)
from app.services.gestor_period import GestorInterval, limit_factor, proportional_limit


MOCK_FILIAL = "0101"


def get_gestor(
    ano: int,
    mes: int,
    filial: str,
    inicio: date | None = None,
    fim: date | None = None,
) -> GestorResponse:
    """Return deterministic mock rows for a valid Gestor query."""
    mock_rows = GESTOR_MOCKS.get((ano, mes), ()) if filial == MOCK_FILIAL else ()
    linhas = [row.model_copy(deep=True) for row in mock_rows]
    if inicio is not None or fim is not None:
        if inicio is None or fim is None or fim < inicio:
            raise ValueError("inicio and fim must form a valid interval.")
        if inicio.year != ano or inicio.month != mes or fim.year != ano or fim.month != mes:
            raise ValueError("interval must be contained in the requested month.")
        interval = GestorInterval(inicio, fim)
        factor = limit_factor(interval, ano, mes)
        filtered_rows: list[GestorRow] = []
        for row in linhas:
            totals = {}
            for tipo in GestorDetailType:
                detail = get_gestor_details(
                    ambiente=GestorDataEnvironment.DEV,
                    filial=filial,
                    ano=ano,
                    mes=mes,
                    natureza=row.natureza_codigo,
                    tipo=tipo,
                    inicio=inicio,
                    fim=fim,
                )
                totals[tipo] = detail.total
            limite_original = proportional_limit(row.limite_original, factor)
            contingencia_ok = totals[GestorDetailType.CONTINGENCIA_OK]
            filtered_rows.append(
                GestorRow(
                    natureza_codigo=row.natureza_codigo,
                    natureza_descricao=row.natureza_descricao,
                    pc_aberto=totals[GestorDetailType.PC_ABERTO],
                    nf_entrada=totals[GestorDetailType.NF_ENTRADA],
                    contingencia_ok=contingencia_ok,
                    contingencia_em_aprovacao=totals[GestorDetailType.CONTINGENCIA_APROVACAO],
                    limite_original=limite_original,
                    saldo_previsto=limite_original - totals[GestorDetailType.PC_ABERTO] - totals[GestorDetailType.NF_ENTRADA],
                    saldo_real=limite_original - totals[GestorDetailType.NF_ENTRADA],
                )
            )
        linhas = filtered_rows

    return GestorResponse(
        periodo=GestorPeriod(ano=ano, mes=mes),
        filial=filial,
        linhas=linhas,
        quantidade=len(linhas),
    )


def get_gestor_details(
    *,
    ambiente: GestorDataEnvironment,
    filial: str,
    ano: int,
    mes: int,
    natureza: str,
    tipo: GestorDetailType,
    inicio: date | None = None,
    fim: date | None = None,
) -> GestorDetailResponse:
    gestor = get_gestor(ano=ano, mes=mes, filial=filial)
    normalized_nature = natureza.strip()
    row = next(
        (item for item in gestor.linhas if item.natureza_codigo == normalized_nature),
        None,
    )
    description = row.natureza_descricao if row else normalized_nature
    consolidated_by_type = {
        GestorDetailType.PC_ABERTO: row.pc_aberto if row else Decimal("0"),
        GestorDetailType.NF_ENTRADA: row.nf_entrada if row else Decimal("0"),
        GestorDetailType.CONTINGENCIA_OK: (
            row.contingencia_ok if row else Decimal("0")
        ),
        GestorDetailType.CONTINGENCIA_APROVACAO: (
            row.contingencia_em_aprovacao if row else Decimal("0")
        ),
    }
    consolidated = consolidated_by_type[tipo]

    if consolidated == 0:
        records: list[
            GestorPcAbertoDetailRecord
            | GestorNfEntradaDetailRecord
            | GestorContingenciaDetailRecord
        ] = []
    elif tipo is GestorDetailType.PC_ABERTO:
        first = (consolidated / 2).quantize(Decimal("0.01"))
        records = [
            GestorPcAbertoDetailRecord(
                pedido=f"DEV-{normalized_nature}-01",
                fornecedor="000001",
                fornecedor_nome="Fornecedor Exemplo DEV",
                vencimento=f"{ano:04d}{mes:02d}10",
                valor=first,
            ),
            GestorPcAbertoDetailRecord(
                pedido=f"DEV-{normalized_nature}-02",
                fornecedor="000001",
                fornecedor_nome="Fornecedor Exemplo DEV",
                vencimento=f"{ano:04d}{mes:02d}20",
                valor=consolidated - first,
            ),
        ]
    elif tipo is GestorDetailType.NF_ENTRADA:
        records = [
            GestorNfEntradaDetailRecord(
                documento=f"DEV-{normalized_nature}",
                prefixo="NF",
                parcela="1",
                fornecedor="000001",
                fornecedor_nome="Fornecedor Exemplo DEV",
                loja="01",
                emissao=f"{ano:04d}{mes:02d}05",
                vencimento=f"{ano:04d}{mes:02d}15",
                valor=consolidated,
            )
        ]
    else:
        first = (consolidated / 2).quantize(Decimal("0.01"))
        status = (
            "OK"
            if tipo is GestorDetailType.CONTINGENCIA_OK
            else "Em aprovação"
        )
        records = [
            GestorContingenciaDetailRecord(
                pedido=f"DEV-CONT-{normalized_nature}-01",
                item="0001",
                vencimento=f"{ano:04d}{mes:02d}12",
                usuario="USUARIODEV",
                status=status,
                valor=first,
            ),
            GestorContingenciaDetailRecord(
                pedido=f"DEV-CONT-{normalized_nature}-02",
                item="0002",
                vencimento=f"{ano:04d}{mes:02d}22",
                usuario="USUARIODEV",
                status=status,
                valor=consolidated - first,
            ),
        ]

    if inicio is not None or fim is not None:
        if inicio is None or fim is None or fim < inicio:
            raise ValueError("inicio and fim must form a valid interval.")
        start = inicio.strftime("%Y%m%d")
        end = fim.strftime("%Y%m%d")
        records = [record for record in records if start <= record.vencimento <= end]
        consolidated = sum((record.valor for record in records), Decimal("0"))

    return GestorDetailResponse(
        ambiente=ambiente,
        filial=filial,
        periodo=gestor.periodo,
        natureza_codigo=normalized_nature,
        natureza_descricao=description,
        tipo=tipo,
        quantidade=len(records),
        total=consolidated,
        registros=records,
    )
