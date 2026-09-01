import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from datetime import date

from app.core.config import Settings, get_settings
from app.core.database import get_database_connection
from app.core.protheus_tables import get_protheus_table_name

logger = logging.getLogger(__name__)
MONEY_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class NfEntradaRecord:
    natureza: str
    valor: Decimal


@dataclass(frozen=True)
class NfEntradaDetailRecord:
    documento: str
    prefixo: str
    parcela: str
    fornecedor: str
    fornecedor_nome: str
    loja: str
    emissao: str
    vencimento: str
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
    # EV_VALOR is SQL Server FLOAT in the confirmed Protheus schema. Normalize
    # its binary representation to the currency precision before invariance
    # checks so aggregate and row-wise sums share one exact Decimal domain.
    return decimal_value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


class NfEntradaRepository:
    """Aggregate SEV allocations for titles due in the requested month."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def list_nf_entrada(
        self,
        filial: str,
        ano: int,
        mes: int,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> list[NfEntradaRecord]:
        normalized_branch = _validate_branch(filial)
        period_pattern = _period_pattern(ano, mes)
        se2_table = get_protheus_table_name("SE2", self._settings)
        sev_table = get_protheus_table_name("SEV", self._settings)

        join = self._join()
        filters = self._filters()
        date_filter, date_parameters = _date_filter("se2.E2_VENCTO", inicio, fim)
        query = f"""
            SELECT
                sev.EV_NATUREZ,
                COALESCE(SUM(sev.EV_VALOR), 0)
            FROM {se2_table} AS se2
            INNER JOIN {sev_table} AS sev ON {join}
            WHERE {filters}{date_filter}
            GROUP BY sev.EV_NATUREZ
            ORDER BY sev.EV_NATUREZ
        """
        parameters = ("E", "X", "1", normalized_branch, period_pattern, *date_parameters)

        logger.info("NF entrada repository query started")
        with get_database_connection(self._settings) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, *parameters)
                rows = cursor.fetchall()
            finally:
                cursor.close()

        records: list[NfEntradaRecord] = []
        for row in rows:
            natureza = "" if row[0] is None else str(row[0]).strip()
            if not natureza:
                continue
            records.append(
                NfEntradaRecord(natureza=natureza, valor=_to_decimal(row[1]))
            )

        logger.info("NF entrada repository query completed")
        return sorted(records, key=lambda record: record.natureza)

    def list_nf_entrada_details(
        self,
        filial: str,
        ano: int,
        mes: int,
        natureza: str,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> list[NfEntradaDetailRecord]:
        normalized_branch = _validate_branch(filial)
        normalized_nature = natureza.strip()
        if not normalized_nature:
            raise ValueError("natureza must not be empty.")
        period_pattern = _period_pattern(ano, mes)
        se2_table = get_protheus_table_name("SE2", self._settings)
        sev_table = get_protheus_table_name("SEV", self._settings)
        sa2_table = get_protheus_table_name("SA2", self._settings)
        join = self._join()
        filters = self._filters()
        date_filter, date_parameters = _date_filter("se2.E2_VENCTO", inicio, fim)
        query = f"""
            SELECT
                se2.E2_NUM,
                se2.E2_PREFIXO,
                se2.E2_PARCELA,
                se2.E2_FORNECE,
                sa2.A2_NOME,
                se2.E2_LOJA,
                se2.E2_EMISSAO,
                se2.E2_VENCTO,
                sev.EV_NATUREZ,
                sev.EV_VALOR
            FROM {se2_table} AS se2
            INNER JOIN {sev_table} AS sev ON {join}
            LEFT JOIN {sa2_table} AS sa2
              ON sa2.A2_FILIAL = LEFT(se2.E2_FILIAL, 2)
             AND sa2.A2_COD = se2.E2_FORNECE
             AND sa2.A2_LOJA = se2.E2_LOJA
             AND sa2.D_E_L_E_T_ = ''
            WHERE {filters}{date_filter}
              AND sev.EV_NATUREZ = ?
            ORDER BY
                se2.E2_VENCTO,
                se2.E2_NUM,
                se2.E2_PREFIXO,
                se2.E2_PARCELA,
                se2.E2_FORNECE,
                se2.E2_LOJA
        """
        parameters = (
            "E", "X", "1", normalized_branch, period_pattern, *date_parameters, normalized_nature
        )

        logger.info("NF entrada detail repository query started")
        with get_database_connection(self._settings) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, *parameters)
                rows = cursor.fetchall()
            finally:
                cursor.close()

        records = [
            NfEntradaDetailRecord(
                documento="" if row[0] is None else str(row[0]).strip(),
                prefixo="" if row[1] is None else str(row[1]).strip(),
                parcela="" if row[2] is None else str(row[2]).strip(),
                fornecedor="" if row[3] is None else str(row[3]).strip(),
                fornecedor_nome="" if row[4] is None else str(row[4]).strip(),
                loja="" if row[5] is None else str(row[5]).strip(),
                emissao="" if row[6] is None else str(row[6]).strip(),
                vencimento="" if row[7] is None else str(row[7]).strip(),
                natureza="" if row[8] is None else str(row[8]).strip(),
                valor=_to_decimal(row[9]),
            )
            for row in rows
        ]
        logger.info("NF entrada detail repository query completed")
        return records

    @staticmethod
    def _join() -> str:
        return """sev.EV_FILIAL = se2.E2_FILIAL
               AND sev.EV_NUM = se2.E2_NUM
               AND sev.EV_PREFIXO = se2.E2_PREFIXO
               AND sev.EV_PARCELA = se2.E2_PARCELA
               AND sev.EV_CLIFOR = se2.E2_FORNECE
               AND sev.EV_LOJA = se2.E2_LOJA
               AND sev.EV_SITUACA NOT IN (?, ?)
               AND sev.EV_IDENT = ?
               AND sev.D_E_L_E_T_ = ''"""

    @staticmethod
    def _filters() -> str:
        """Single source of truth for consolidated and detail eligibility."""
        return """se2.E2_FILIAL = ?
              AND se2.E2_VENCTO LIKE ?
              AND se2.D_E_L_E_T_ = ''"""


def _date_filter(column: str, inicio: date | None, fim: date | None) -> tuple[str, tuple[str, ...]]:
    if inicio is None and fim is None:
        return "", ()
    if inicio is None or fim is None or fim < inicio:
        raise ValueError("inicio and fim must form a valid interval.")
    return f"\n              AND {column} >= ? AND {column} <= ?", (inicio.strftime("%Y%m%d"), fim.strftime("%Y%m%d"))
