import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from datetime import date

from app.core.config import Settings, get_settings
from app.core.database import get_database_connection
from app.core.protheus_tables import get_protheus_table_name

logger = logging.getLogger(__name__)
MONEY_QUANTUM = Decimal("0.01")
APPROVED = "T"
NOT_APPROVED = "F"
REJECTED = "T"
NOT_REJECTED = "F"


@dataclass(frozen=True)
class ContingenciaRecord:
    natureza: str
    contingencia_ok: Decimal
    contingencia_em_aprovacao: Decimal


@dataclass(frozen=True)
class ContingenciaDetailRecord:
    pedido: str
    item: str
    vencimento: str
    usuario: str
    status: str
    natureza: str
    valor: Decimal


def _validate_branch(filial: str) -> str:
    normalized = filial.strip()
    if not normalized:
        raise ValueError("filial must not be empty.")
    return normalized


def _period_pattern(ano: int, mes: int) -> str:
    if not 2000 <= ano <= 2100:
        raise ValueError("ano must be between 2000 and 2100.")
    if not 1 <= mes <= 12:
        raise ValueError("mes must be between 1 and 12.")
    return f"{ano:04d}{mes:02d}%"


def _to_decimal(value: object) -> Decimal:
    if value is None:
        decimal_value = Decimal("0")
    elif isinstance(value, Decimal):
        decimal_value = value
    else:
        decimal_value = Decimal(str(value))
    return decimal_value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


class ContingenciaRepository:
    """Aggregate approved and pending contingencies using FWACOM04 rules."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def list_contingencias(
        self,
        filial: str,
        ano: int,
        mes: int,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> list[ContingenciaRecord]:
        normalized_branch = _validate_branch(filial)
        period_pattern = _period_pattern(ano, mes)
        szr_table = get_protheus_table_name("SZR", self._settings)

        date_filter, date_parameters = _date_filter("szr.ZR_VENCTO", inicio, fim)
        query = f"""
            SELECT
                szr.ZR_NATUREZ,
                COALESCE(SUM(CASE
                    WHEN szr.ZR_APROV = ? AND szr.ZR_REPROV <> ?
                    THEN szr.ZR_CONTING
                    ELSE 0
                END), 0),
                COALESCE(SUM(CASE
                    WHEN szr.ZR_APROV = ? AND szr.ZR_REPROV = ?
                    THEN szr.ZR_CONTING
                    ELSE 0
                END), 0)
            FROM {szr_table} AS szr
            WHERE szr.ZR_FILIAL = ?
              AND szr.ZR_VENCTO LIKE ?
              AND szr.D_E_L_E_T_ = ''{date_filter}
              AND (
                  (szr.ZR_APROV = ? AND szr.ZR_REPROV <> ?)
                  OR (szr.ZR_APROV = ? AND szr.ZR_REPROV = ?)
              )
            GROUP BY szr.ZR_NATUREZ
            ORDER BY szr.ZR_NATUREZ
        """
        parameters = (
            APPROVED,
            REJECTED,
            NOT_APPROVED,
            NOT_REJECTED,
            normalized_branch,
            period_pattern,
            *date_parameters,
            APPROVED,
            REJECTED,
            NOT_APPROVED,
            NOT_REJECTED,
        )

        logger.info("Contingencia repository query started")
        with get_database_connection(self._settings) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, *parameters)
                rows = cursor.fetchall()
            finally:
                cursor.close()

        records: list[ContingenciaRecord] = []
        for row in rows:
            natureza = "" if row[0] is None else str(row[0]).strip()
            if not natureza:
                continue
            records.append(
                ContingenciaRecord(
                    natureza=natureza,
                    contingencia_ok=_to_decimal(row[1]),
                    contingencia_em_aprovacao=_to_decimal(row[2]),
                )
            )

        logger.info("Contingencia repository query completed")
        return sorted(records, key=lambda record: record.natureza)

    def list_contingencia_ok_details(
        self,
        filial: str,
        ano: int,
        mes: int,
        natureza: str,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> list[ContingenciaDetailRecord]:
        return self._list_details(
            filial=filial,
            ano=ano,
            mes=mes,
            natureza=natureza,
            aprovacao=APPROVED,
            reprovacao=REJECTED,
            reprovacao_operator="<>",
            status="OK",
            inicio=inicio,
            fim=fim,
        )

    def list_contingencia_aprovacao_details(
        self,
        filial: str,
        ano: int,
        mes: int,
        natureza: str,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> list[ContingenciaDetailRecord]:
        return self._list_details(
            filial=filial,
            ano=ano,
            mes=mes,
            natureza=natureza,
            aprovacao=NOT_APPROVED,
            reprovacao=NOT_REJECTED,
            reprovacao_operator="=",
            status="Em aprovação",
            inicio=inicio,
            fim=fim,
        )

    def _list_details(
        self,
        *,
        filial: str,
        ano: int,
        mes: int,
        natureza: str,
        aprovacao: str,
        reprovacao: str,
        reprovacao_operator: str,
        status: str,
        inicio: date | None,
        fim: date | None,
    ) -> list[ContingenciaDetailRecord]:
        normalized_branch = _validate_branch(filial)
        normalized_nature = natureza.strip()
        if not normalized_nature:
            raise ValueError("natureza must not be empty.")
        if reprovacao_operator not in {"=", "<>"}:
            raise ValueError("Unsupported contingency status operator.")
        period_pattern = _period_pattern(ano, mes)
        szr_table = get_protheus_table_name("SZR", self._settings)
        date_filter, date_parameters = _date_filter("szr.ZR_VENCTO", inicio, fim)
        query = f"""
            SELECT
                szr.ZR_NUMPED,
                szr.ZR_ITEMPED,
                szr.ZR_VENCTO,
                szr.ZR_USER,
                szr.ZR_NATUREZ,
                szr.ZR_CONTING
            FROM {szr_table} AS szr
            WHERE szr.ZR_FILIAL = ?
              AND szr.ZR_VENCTO LIKE ?
              AND szr.ZR_NATUREZ = ?
              AND szr.D_E_L_E_T_ = ''{date_filter}
              AND szr.ZR_APROV = ?
              AND szr.ZR_REPROV {reprovacao_operator} ?
            ORDER BY
                szr.ZR_VENCTO,
                szr.ZR_NUMPED,
                szr.ZR_ITEMPED,
                szr.R_E_C_N_O_
        """
        parameters = (
            normalized_branch,
            period_pattern,
            normalized_nature,
            *date_parameters,
            aprovacao,
            reprovacao,
        )

        logger.info("Contingencia detail repository query started")
        with get_database_connection(self._settings) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, *parameters)
                rows = cursor.fetchall()
            finally:
                cursor.close()

        records = [
            ContingenciaDetailRecord(
                pedido="" if row[0] is None else str(row[0]).strip(),
                item="" if row[1] is None else str(row[1]).strip(),
                vencimento="" if row[2] is None else str(row[2]).strip(),
                usuario="" if row[3] is None else str(row[3]).strip(),
                status=status,
                natureza="" if row[4] is None else str(row[4]).strip(),
                valor=_to_decimal(row[5]),
            )
            for row in rows
        ]
        logger.info("Contingencia detail repository query completed")
        return records


def _date_filter(column: str, inicio: date | None, fim: date | None) -> tuple[str, tuple[str, ...]]:
    if inicio is None and fim is None:
        return "", ()
    if inicio is None or fim is None or fim < inicio:
        raise ValueError("inicio and fim must form a valid interval.")
    return f"\n              AND {column} >= ? AND {column} <= ?", (inicio.strftime("%Y%m%d"), fim.strftime("%Y%m%d"))
