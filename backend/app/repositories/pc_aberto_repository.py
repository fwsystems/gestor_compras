import logging
from dataclasses import dataclass
from decimal import Decimal
from datetime import date

from app.core.config import Settings, get_settings
from app.core.database import get_database_connection
from app.core.protheus_tables import get_protheus_table_name

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PcAbertoRecord:
    natureza: str
    valor: Decimal


@dataclass(frozen=True)
class PcAbertoDetailRecord:
    pedido: str
    vencimento: str
    natureza: str
    valor: Decimal


def _validate_period(ano: int, mes: int) -> str:
    if not 2000 <= ano <= 2100:
        raise ValueError("ano must be between 2000 and 2100.")
    if not 1 <= mes <= 12:
        raise ValueError("mes must be between 1 and 12.")
    return f"{ano:04d}{mes:02d}%"


def _to_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class PcAbertoRepository:
    """Read open purchase-order commitments using the FWACOM04 rule."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def list_pc_aberto(
        self,
        filial: str,
        ano: int,
        mes: int,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> list[PcAbertoRecord]:
        normalized_branch = filial.strip()
        if not normalized_branch:
            raise ValueError("filial must not be empty.")

        period_pattern = _validate_period(ano, mes)
        date_filter, date_parameters = _date_filter("szn.ZN_VENCTO", inicio, fim)
        szn_table = get_protheus_table_name("SZN", self._settings)
        sc7_table = get_protheus_table_name("SC7", self._settings)
        filters = self._filters(sc7_table)
        query = f"""
            SELECT
                szn.ZN_NATUREZ,
                COALESCE(SUM(szn.ZN_SALDO), 0)
            FROM {szn_table} AS szn
            WHERE {filters}{date_filter}
            GROUP BY szn.ZN_NATUREZ
            ORDER BY szn.ZN_NATUREZ
        """

        logger.info("PC aberto repository query started")
        with get_database_connection(self._settings) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, normalized_branch, period_pattern, " ", *date_parameters)
                rows = cursor.fetchall()
            finally:
                cursor.close()

        records: list[PcAbertoRecord] = []
        for row in rows:
            natureza = "" if row[0] is None else str(row[0]).strip()
            if not natureza:
                continue
            records.append(PcAbertoRecord(natureza=natureza, valor=_to_decimal(row[1])))

        logger.info("PC aberto repository query completed")
        return records

    def list_pc_aberto_details(
        self,
        filial: str,
        ano: int,
        mes: int,
        natureza: str,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> list[PcAbertoDetailRecord]:
        normalized_branch = filial.strip()
        normalized_nature = natureza.strip()
        if not normalized_branch:
            raise ValueError("filial must not be empty.")
        if not normalized_nature:
            raise ValueError("natureza must not be empty.")

        period_pattern = _validate_period(ano, mes)
        szn_table = get_protheus_table_name("SZN", self._settings)
        sc7_table = get_protheus_table_name("SC7", self._settings)
        filters = self._filters(sc7_table)
        date_filter, date_parameters = _date_filter("szn.ZN_VENCTO", inicio, fim)
        query = f"""
            SELECT
                szn.ZN_NUMPED,
                szn.ZN_VENCTO,
                szn.ZN_NATUREZ,
                szn.ZN_SALDO
            FROM {szn_table} AS szn
            WHERE {filters}{date_filter}
              AND szn.ZN_NATUREZ = ?
            ORDER BY szn.ZN_NUMPED, szn.ZN_VENCTO
        """

        logger.info("PC aberto detail repository query started")
        with get_database_connection(self._settings) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    query,
                    normalized_branch,
                    period_pattern,
                    " ",
                    *date_parameters,
                    normalized_nature,
                )
                rows = cursor.fetchall()
            finally:
                cursor.close()

        records = [
            PcAbertoDetailRecord(
                pedido="" if row[0] is None else str(row[0]).strip(),
                vencimento="" if row[1] is None else str(row[1]).strip(),
                natureza="" if row[2] is None else str(row[2]).strip(),
                valor=_to_decimal(row[3]),
            )
            for row in rows
        ]
        logger.info("PC aberto detail repository query completed")
        return records

    @staticmethod
    def _filters(sc7_table: str) -> str:
        """Single source of truth for consolidated and detail eligibility."""
        return f"""szn.ZN_FILIAL = ?
              AND szn.ZN_VENCTO LIKE ?
              AND szn.D_E_L_E_T_ = ''
              AND EXISTS (
                  SELECT 1
                  FROM {sc7_table} AS sc7
                  WHERE sc7.C7_FILIAL = szn.ZN_FILIAL
                    AND sc7.C7_NUM = szn.ZN_NUMPED
                    AND NOT (sc7.C7_QUJE >= sc7.C7_QUANT)
                    AND sc7.C7_RESIDUO = ?
                    AND sc7.D_E_L_E_T_ = ''
              )"""


def _date_filter(column: str, inicio: date | None, fim: date | None) -> tuple[str, tuple[str, ...]]:
    if inicio is None and fim is None:
        return "", ()
    if inicio is None or fim is None or fim < inicio:
        raise ValueError("inicio and fim must form a valid interval.")
    return f"\n              AND {column} >= ? AND {column} <= ?", (inicio.strftime("%Y%m%d"), fim.strftime("%Y%m%d"))
