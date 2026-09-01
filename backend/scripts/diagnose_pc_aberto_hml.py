import argparse
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol

from app.core.config import AppEnvironment, Settings, get_settings
from app.core.database import DatabaseError, get_database_connection
from app.core.protheus_tables import get_protheus_table_name
from app.repositories.pc_aberto_repository import PcAbertoRecord, PcAbertoRepository


class PcAbertoDiagnosisError(RuntimeError):
    """Safe error raised by the HML-only PC diagnosis."""


class _PcRepository(Protocol):
    def list_pc_aberto(
        self, filial: str, ano: int, mes: int
    ) -> list[PcAbertoRecord]: ...


@dataclass(frozen=True)
class SznContribution:
    pedido: str
    item: str | None
    vencimento: str
    saldo: Decimal
    registros: int
    ativa: bool
    elegivel_web: bool
    motivo_exclusao: str | None


@dataclass(frozen=True)
class Sc7Item:
    pedido: str
    item: str | None
    natureza: str | None
    quantidade: Decimal | None
    quantidade_recebida: Decimal | None
    preco: Decimal | None
    total: Decimal | None
    residuo: str
    ativo: bool
    aberto: bool
    elegivel_web: bool


@dataclass(frozen=True)
class ExclusionTotal:
    motivo: str
    valor: Decimal


@dataclass(frozen=True)
class SznPeriodTotal:
    periodo: str
    ativo: bool
    valor: Decimal
    registros: int


@dataclass(frozen=True)
class PcAbertoDiagnosis:
    executed_at_utc: datetime
    filial: str
    ano: int
    mes: int
    natureza: str
    total_repository: Decimal
    total_szn_bruto: Decimal
    total_elegivel_diagnostico: Decimal
    total_sc7_aberto_calculado: Decimal
    contributions: tuple[SznContribution, ...]
    sc7_items: tuple[Sc7Item, ...]
    exclusions: tuple[ExclusionTotal, ...]
    period_totals: tuple[SznPeriodTotal, ...]


ConnectionFactory = Callable[[Settings], AbstractContextManager[Any]]


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def validate_diagnosis_input(
    filial: str, ano: int, mes: int, natureza: str
) -> tuple[str, str, str]:
    branch = filial.strip()
    code = natureza.strip()
    if not branch:
        raise ValueError("filial must not be empty.")
    if not code:
        raise ValueError("natureza must not be empty.")
    if not 2000 <= ano <= 2100:
        raise ValueError("ano must be between 2000 and 2100.")
    if not 1 <= mes <= 12:
        raise ValueError("mes must be between 1 and 12.")
    return branch, f"{ano:04d}{mes:02d}%", code


def _existing_columns(
    cursor: Any, table: str, candidates: tuple[str, ...]
) -> frozenset[str]:
    placeholders = ", ".join("?" for _ in candidates)
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME = ? AND COLUMN_NAME IN ({placeholders})",
        table,
        *candidates,
    )
    return frozenset(str(row[0]).strip().upper() for row in cursor.fetchall())


def _exclusion_reason(items: Sequence[Sc7Item]) -> str:
    if not items:
        return "pedido_nao_encontrado_na_sc7"
    active_items = [item for item in items if item.ativo]
    if not active_items:
        return "itens_sc7_logicamente_excluidos"
    open_items = [item for item in active_items if item.aberto]
    if not open_items:
        return "sem_item_aberto"
    if all(not item.elegivel_web for item in open_items):
        return "itens_abertos_marcados_como_residuo"
    return "sem_item_elegivel_motivo_misto"


def _repository_total(
    records: Sequence[PcAbertoRecord], natureza: str
) -> Decimal:
    return next(
        (record.valor for record in records if record.natureza.strip() == natureza),
        Decimal("0"),
    )


def run_diagnosis(
    *,
    settings: Settings,
    filial: str,
    ano: int,
    mes: int,
    natureza: str,
    repository: _PcRepository | None = None,
    connection_factory: ConnectionFactory = get_database_connection,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> PcAbertoDiagnosis:
    if settings.app_env is not AppEnvironment.HML:
        raise PcAbertoDiagnosisError("PC diagnosis is available only in HML.")
    return run_read_only_diagnosis(
        settings=settings,
        filial=filial,
        ano=ano,
        mes=mes,
        natureza=natureza,
        repository=repository,
        connection_factory=connection_factory,
        now=now,
    )


def run_read_only_diagnosis(
    *,
    settings: Settings,
    filial: str,
    ano: int,
    mes: int,
    natureza: str,
    repository: _PcRepository | None = None,
    connection_factory: ConnectionFactory = get_database_connection,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> PcAbertoDiagnosis:
    """Run the shared SELECT-only diagnosis after an environment-specific guard."""
    branch, period, code = validate_diagnosis_input(
        filial, ano, mes, natureza
    )
    pc_repository = repository or PcAbertoRepository(settings)
    total_repository = _repository_total(
        pc_repository.list_pc_aberto(branch, ano, mes), code
    )
    szn_table = get_protheus_table_name("SZN", settings)
    sc7_table = get_protheus_table_name("SC7", settings)

    with connection_factory(settings) as connection:
        cursor = connection.cursor()
        try:
            szn_columns = _existing_columns(
                cursor, szn_table, ("ZN_ITEPED",)
            )
            sc7_columns = _existing_columns(
                cursor,
                sc7_table,
                ("C7_ITEM", "C7_ZZNATUR", "C7_PRECO", "C7_TOTAL"),
            )

            szn_item_select = (
                "szn.ZN_ITEPED" if "ZN_ITEPED" in szn_columns else "NULL"
            )
            szn_item_group = (
                ", szn.ZN_ITEPED" if "ZN_ITEPED" in szn_columns else ""
            )
            szn_query = f"""
                SELECT szn.ZN_NUMPED, {szn_item_select} AS ZN_ITEPED,
                       szn.ZN_VENCTO, COALESCE(szn.ZN_SALDO, 0), COUNT(*),
                       CASE WHEN szn.D_E_L_E_T_ = '' THEN 1 ELSE 0 END
                FROM {szn_table} AS szn
                WHERE szn.ZN_FILIAL = ?
                  AND szn.ZN_NATUREZ = ?
                  AND szn.ZN_VENCTO LIKE ?
                GROUP BY szn.ZN_NUMPED{szn_item_group}, szn.ZN_VENCTO,
                         szn.ZN_SALDO, szn.D_E_L_E_T_
                ORDER BY szn.ZN_NUMPED, ZN_ITEPED, szn.ZN_VENCTO
            """
            cursor.execute(szn_query, branch, code, period)
            szn_rows = tuple(tuple(row) for row in cursor.fetchall())

            sc7_item_select = (
                "sc7.C7_ITEM" if "C7_ITEM" in sc7_columns else "NULL"
            )
            sc7_nature_select = (
                "sc7.C7_ZZNATUR"
                if "C7_ZZNATUR" in sc7_columns
                else "NULL"
            )
            sc7_price_select = (
                "sc7.C7_PRECO" if "C7_PRECO" in sc7_columns else "NULL"
            )
            sc7_total_select = (
                "sc7.C7_TOTAL" if "C7_TOTAL" in sc7_columns else "NULL"
            )
            sc7_query = f"""
                SELECT sc7.C7_NUM, {sc7_item_select} AS C7_ITEM,
                       {sc7_nature_select} AS C7_ZZNATUR,
                       sc7.C7_QUANT, sc7.C7_QUJE,
                       {sc7_price_select} AS C7_PRECO,
                       {sc7_total_select} AS C7_TOTAL, sc7.C7_RESIDUO,
                       CASE WHEN sc7.D_E_L_E_T_ = '' THEN 1 ELSE 0 END,
                       CASE WHEN sc7.D_E_L_E_T_ = ''
                                  AND NOT (sc7.C7_QUJE >= sc7.C7_QUANT)
                            THEN 1 ELSE 0 END,
                       CASE WHEN sc7.D_E_L_E_T_ = ''
                                  AND NOT (sc7.C7_QUJE >= sc7.C7_QUANT)
                                  AND sc7.C7_RESIDUO = ?
                            THEN 1 ELSE 0 END
                FROM {sc7_table} AS sc7
                WHERE sc7.C7_FILIAL = ?
                  AND EXISTS (
                      SELECT 1
                      FROM {szn_table} AS szn
                      WHERE szn.ZN_FILIAL = sc7.C7_FILIAL
                        AND szn.ZN_NUMPED = sc7.C7_NUM
                        AND szn.ZN_NATUREZ = ?
                        AND szn.ZN_VENCTO LIKE ?
                        AND szn.D_E_L_E_T_ = ''
                  )
                ORDER BY sc7.C7_NUM, C7_ITEM
            """
            cursor.execute(sc7_query, " ", branch, code, period)
            sc7_rows = tuple(tuple(row) for row in cursor.fetchall())

            period_totals_query = f"""
                SELECT LEFT(szn.ZN_VENCTO, 6),
                       CASE WHEN szn.D_E_L_E_T_ = '' THEN 1 ELSE 0 END,
                       COALESCE(SUM(szn.ZN_SALDO), 0), COUNT(*)
                FROM {szn_table} AS szn
                WHERE szn.ZN_FILIAL = ?
                  AND szn.ZN_NATUREZ = ?
                  AND szn.ZN_VENCTO LIKE ?
                GROUP BY LEFT(szn.ZN_VENCTO, 6), szn.D_E_L_E_T_
                ORDER BY LEFT(szn.ZN_VENCTO, 6), szn.D_E_L_E_T_
            """
            cursor.execute(period_totals_query, branch, code, f"{ano:04d}%")
            period_total_rows = tuple(tuple(row) for row in cursor.fetchall())
        finally:
            cursor.close()

    sc7_items = tuple(
        Sc7Item(
            pedido=str(row[0]).strip(),
            item=_optional_text(row[1]),
            natureza=_optional_text(row[2]),
            quantidade=None if row[3] is None else _to_decimal(row[3]),
            quantidade_recebida=(
                None if row[4] is None else _to_decimal(row[4])
            ),
            preco=None if row[5] is None else _to_decimal(row[5]),
            total=None if row[6] is None else _to_decimal(row[6]),
            residuo="" if row[7] is None else str(row[7]),
            ativo=bool(row[8]),
            aberto=bool(row[9]),
            elegivel_web=bool(row[10]),
        )
        for row in sc7_rows
    )
    items_by_order: dict[str, list[Sc7Item]] = {}
    for item in sc7_items:
        items_by_order.setdefault(item.pedido, []).append(item)

    contributions: list[SznContribution] = []
    excluded_totals: dict[str, Decimal] = {}
    for row in szn_rows:
        pedido = str(row[0]).strip()
        ativa = bool(row[5])
        related_items = items_by_order.get(pedido, [])
        eligible = ativa and any(item.elegivel_web for item in related_items)
        reason: str | None = None
        if not ativa:
            reason = "registro_szn_logicamente_excluido"
        elif not eligible:
            reason = _exclusion_reason(related_items)
        saldo = _to_decimal(row[3]) * int(row[4])
        if reason is not None:
            excluded_totals[reason] = excluded_totals.get(
                reason, Decimal("0")
            ) + saldo
        contributions.append(
            SznContribution(
                pedido=pedido,
                item=_optional_text(row[1]),
                vencimento=str(row[2]).strip(),
                saldo=saldo,
                registros=int(row[4]),
                ativa=ativa,
                elegivel_web=eligible,
                motivo_exclusao=reason,
            )
        )

    total_szn_bruto = sum(
        (entry.saldo for entry in contributions if entry.ativa), Decimal("0")
    )
    total_elegivel = sum(
        (entry.saldo for entry in contributions if entry.elegivel_web),
        Decimal("0"),
    )
    total_sc7_aberto_calculado = sum(
        (
            (item.quantidade - item.quantidade_recebida) * item.preco
            for item in sc7_items
            if item.elegivel_web
            and item.quantidade is not None
            and item.quantidade_recebida is not None
            and item.preco is not None
        ),
        Decimal("0"),
    )
    return PcAbertoDiagnosis(
        executed_at_utc=now(),
        filial=branch,
        ano=ano,
        mes=mes,
        natureza=code,
        total_repository=total_repository,
        total_szn_bruto=total_szn_bruto,
        total_elegivel_diagnostico=total_elegivel,
        total_sc7_aberto_calculado=total_sc7_aberto_calculado,
        contributions=tuple(contributions),
        sc7_items=sc7_items,
        exclusions=tuple(
            ExclusionTotal(reason, value)
            for reason, value in sorted(excluded_totals.items())
        ),
        period_totals=tuple(
            SznPeriodTotal(
                periodo=str(row[0]).strip(),
                ativo=bool(row[1]),
                valor=_to_decimal(row[2]),
                registros=int(row[3]),
            )
            for row in period_total_rows
        ),
    )


def format_diagnosis(
    diagnosis: PcAbertoDiagnosis, environment_label: str = "HML"
) -> str:
    lines = [
        f"Ambiente: {environment_label}",
        f"Executado em UTC: {diagnosis.executed_at_utc.isoformat()}",
        f"Filial: {diagnosis.filial}",
        f"Período: {diagnosis.ano:04d}/{diagnosis.mes:02d}",
        f"Natureza: {diagnosis.natureza}",
        f"Total PcAbertoRepository: {_money(diagnosis.total_repository)}",
        f"Total bruto SZN ativo: {_money(diagnosis.total_szn_bruto)}",
        "Total elegível diagnóstico: "
        f"{_money(diagnosis.total_elegivel_diagnostico)}",
        "Total aberto calculado dos itens SC7 elegíveis: "
        f"{_money(diagnosis.total_sc7_aberto_calculado)}",
        "Consistência repository/diagnóstico: "
        + (
            "OK"
            if diagnosis.total_repository == diagnosis.total_elegivel_diagnostico
            else "DIVERGENTE"
        ),
        "",
        "Contribuições SZN:",
    ]
    items_by_order: dict[str, list[Sc7Item]] = {}
    for item in diagnosis.sc7_items:
        items_by_order.setdefault(item.pedido, []).append(item)
    for entry in diagnosis.contributions:
        items = items_by_order.get(entry.pedido, [])
        naturezas = sorted(
            {item.natureza for item in items if item.natureza is not None}
        )
        status = "ELEGÍVEL" if entry.elegivel_web else entry.motivo_exclusao
        lines.append(
            f"Pedido={entry.pedido}; ItemSZN={entry.item or '-'}; "
            f"Vencimento={entry.vencimento}; Saldo={_money(entry.saldo)}; "
            f"RegistrosSZN={entry.registros}; Status={status}; "
            f"ItensSC7={len(items)}; Ativos={sum(i.ativo for i in items)}; "
            f"Abertos={sum(i.aberto for i in items)}; "
            f"Elegíveis={sum(i.elegivel_web for i in items)}; "
            f"C7_ZZNATUR={','.join(naturezas) if naturezas else '-'}"
        )
    lines.extend(("", "Itens SC7 relacionados:"))
    for item in diagnosis.sc7_items:
        calculated = (
            (item.quantidade - item.quantidade_recebida) * item.preco
            if item.quantidade is not None
            and item.quantidade_recebida is not None
            and item.preco is not None
            else None
        )
        lines.append(
            f"Pedido={item.pedido}; Item={item.item or '-'}; "
            f"C7_ZZNATUR={item.natureza or '-'}; Quant={item.quantidade}; "
            f"Recebida={item.quantidade_recebida}; Preço={item.preco}; "
            f"TotalItem={item.total}; "
            f"SaldoCalculado={_money(calculated) if calculated is not None else None}; "
            f"Ativo={item.ativo}; Aberto={item.aberto}; "
            f"ElegívelWeb={item.elegivel_web}"
        )
    lines.extend(("", "Totais excluídos por motivo:"))
    if diagnosis.exclusions:
        lines.extend(
            f"{entry.motivo}: {_money(entry.valor)}"
            for entry in diagnosis.exclusions
        )
    else:
        lines.append("Nenhum")
    lines.extend(("", f"Totais SZN da Natureza em {diagnosis.ano}:"))
    lines.extend(
        f"Período={entry.periodo}; "
        f"Status={'ativo' if entry.ativo else 'excluído'}; "
        f"Total={_money(entry.valor)}; Registros={entry.registros}"
        for entry in diagnosis.period_totals
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diagnose PC aberto safely with read-only HML queries."
    )
    parser.add_argument("--filial", required=True)
    parser.add_argument("--ano", required=True, type=int)
    parser.add_argument("--mes", required=True, type=int)
    parser.add_argument("--natureza", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        diagnosis = run_diagnosis(
            settings=get_settings(),
            filial=args.filial,
            ano=args.ano,
            mes=args.mes,
            natureza=args.natureza,
        )
    except (PcAbertoDiagnosisError, DatabaseError, ValueError) as error:
        print(f"Diagnóstico de PC aberto não executado: {error}")
        return 1
    print(format_diagnosis(diagnosis))
    return (
        0
        if diagnosis.total_repository == diagnosis.total_elegivel_diagnostico
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
