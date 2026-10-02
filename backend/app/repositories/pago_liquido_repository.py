import logging
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import Settings, get_settings
from app.core.database import get_database_connection
from app.core.protheus_tables import get_protheus_table_name

logger = logging.getLogger(__name__)
MONEY_QUANTUM = Decimal("0.01")
ZERO = Decimal("0")


@dataclass(frozen=True)
class PagoLiquidoRecord:
    natureza: str
    pago: Decimal
    a_pagar: Decimal = ZERO
    total: Decimal = ZERO

    @property
    def valor(self) -> Decimal:
        """Compatibility alias for the former SE5-only repository contract."""
        return self.pago


def _validate_branch(filial: str) -> str:
    normalized = filial.strip()
    if not normalized:
        raise ValueError("filial must not be empty.")
    return normalized


def _period_bounds(
    ano: int,
    mes: int,
    inicio: date | None,
    fim: date | None,
) -> tuple[str, str]:
    if not 2000 <= ano <= 2100:
        raise ValueError("ano must be between 2000 and 2100.")
    if not 1 <= mes <= 12:
        raise ValueError("mes must be between 1 and 12.")
    if (inicio is None) != (fim is None):
        raise ValueError("inicio and fim must be provided together.")
    if inicio is None and fim is None:
        inicio = date(ano, mes, 1)
        fim = date(ano, mes, monthrange(ano, mes)[1])
    assert inicio is not None and fim is not None
    if fim < inicio or inicio.year != ano or inicio.month != mes or fim.year != ano or fim.month != mes:
        raise ValueError("interval must be contained in the requested month.")
    return inicio.strftime("%Y%m%d"), fim.strftime("%Y%m%d")


def _to_decimal(value: object) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _is_future_period(ano: int, mes: int) -> bool:
    current = date.today().replace(day=1)
    return date(ano, mes, 1) > current


class PagoLiquidoRepository:
    """Reproduce the Financeiro title/payment classification by Natureza."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def list_pago_liquido(
        self,
        filial: str,
        ano: int,
        mes: int,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> list[PagoLiquidoRecord]:
        normalized_branch = _validate_branch(filial)
        inicio_text, fim_text = _period_bounds(ano, mes, inicio, fim)
        future = _is_future_period(ano, mes)
        se2_table = get_protheus_table_name("SE2", self._settings)
        se5_table = get_protheus_table_name("SE5", self._settings)
        sev_table = get_protheus_table_name("SEV", self._settings)
        value_column = "E2_SALDO" if future else "E2_VALOR"
        tax_subtraction = (
            "COALESCE(se2.E2_PIS, 0) + COALESCE(se2.E2_COFINS, 0) "
            "+ COALESCE(se2.E2_CSLL, 0) "
            + ("+ COALESCE(se2.E2_ISS, 0)" if future else "+ COALESCE(se2.E2_DECRESC, 0)")
        )
        tax_addition = "" if future else "+ COALESCE(se2.E2_ACRESC, 0)"
        compensation_filter = "AND base.compensacao = 0" if future else ""
        query = f"""
            WITH movimentos AS (
                SELECT
                    e5.E5_FILIAL, e5.E5_PREFIXO, e5.E5_NUMERO,
                    e5.E5_PARCELA, e5.E5_CLIFOR, e5.E5_LOJA,
                    SUM(CASE
                        WHEN (e5.E5_MOTBX IS NULL OR e5.E5_MOTBX NOT IN ('CMP', 'CEC', 'DAC'))
                        THEN COALESCE(e5.E5_VALOR, 0) ELSE 0 END) AS valor_movimento,
                    MAX(CASE
                        WHEN (e5.E5_MOTBX IS NULL OR e5.E5_MOTBX NOT IN ('CMP', 'CEC', 'DAC'))
                        THEN 1 ELSE 0 END) AS possui_movimento,
                    MAX(CASE WHEN e5.E5_MOTBX IN ('CMP', 'CEC', 'DAC') THEN 1 ELSE 0 END) AS compensacao
                FROM {se5_table} AS e5
                WHERE e5.D_E_L_E_T_ = ''
                  AND NULLIF(LTRIM(RTRIM(e5.E5_DTCANBX)), '') IS NULL
                  AND e5.E5_TIPODOC NOT IN ('JR', 'DC')
                GROUP BY e5.E5_FILIAL, e5.E5_PREFIXO, e5.E5_NUMERO,
                         e5.E5_PARCELA, e5.E5_CLIFOR, e5.E5_LOJA
            ),
            base AS (
                SELECT
                    COALESCE(sev.EV_NATUREZ, se2.E2_NATUREZ) AS natureza,
                    se2.E2_TIPO AS tipo,
                    se2.E2_VENCREA AS vencimento_real,
                    se2.E2_BAIXA AS baixa,
                    CASE
                        WHEN se2.E2_TIPO <> 'PR' AND COALESCE(mov.possui_movimento, 0) = 1
                             OR NULLIF(LTRIM(RTRIM(se2.E2_BAIXA)), '') IS NOT NULL
                             OR COALESCE(se2.E2_SALDO, 0) = 0
                        THEN 1 ELSE 0
                    END AS pago,
                    COALESCE(mov.compensacao, 0) AS compensacao,
                    CASE
                        WHEN se2.E2_TIPO = 'PR' THEN COALESCE({value_column}, 0)
                        WHEN sev.EV_NATUREZ IS NOT NULL THEN
                            COALESCE(sev.EV_PERC, 0) * COALESCE(
                                mov.valor_movimento,
                                COALESCE({value_column}, 0) - ({tax_subtraction}) {tax_addition}
                            )
                        WHEN COALESCE(se2.E2_MULTNAT, 0) <> 1 THEN COALESCE(
                            mov.valor_movimento,
                            COALESCE({value_column}, 0) - ({tax_subtraction}) {tax_addition}
                        )
                        ELSE COALESCE({value_column}, 0)
                    END AS valor_liquido
                FROM {se2_table} AS se2
                LEFT JOIN {sev_table} AS sev
                  ON sev.EV_FILIAL = se2.E2_FILIAL
                 AND sev.EV_NUM = se2.E2_NUM
                 AND sev.EV_PREFIXO = se2.E2_PREFIXO
                 AND sev.EV_PARCELA = se2.E2_PARCELA
                 AND sev.EV_CLIFOR = se2.E2_FORNECE
                 AND sev.EV_LOJA = se2.E2_LOJA
                 AND sev.EV_SITUACA NOT IN ('E', 'X')
                 AND sev.EV_IDENT = '1'
                 AND sev.D_E_L_E_T_ = ''
                LEFT JOIN movimentos AS mov
                  ON mov.E5_FILIAL = se2.E2_FILIAL
                 AND mov.E5_PREFIXO = se2.E2_PREFIXO
                 AND mov.E5_NUMERO = se2.E2_NUM
                 AND mov.E5_PARCELA = se2.E2_PARCELA
                 AND mov.E5_CLIFOR = se2.E2_FORNECE
                 AND mov.E5_LOJA = se2.E2_LOJA
                WHERE se2.E2_FILIAL = ?
                  AND se2.D_E_L_E_T_ = ''
                  AND se2.E2_TIPO <> 'NDF'
                  AND NULLIF(LTRIM(RTRIM(se2.E2_STATLIB)), '') IS NOT NULL
                  AND NULLIF(LTRIM(RTRIM(se2.E2_DATALIB)), '') IS NOT NULL
            )
            SELECT
                base.natureza,
                COALESCE(SUM(CASE WHEN base.pago = 1 THEN base.valor_liquido ELSE 0 END), 0) AS pago,
                COALESCE(SUM(CASE WHEN base.pago = 0 THEN base.valor_liquido ELSE 0 END), 0) AS a_pagar,
                COALESCE(SUM(base.valor_liquido), 0) AS total
            FROM base
            WHERE (
                (base.tipo = 'PA' AND base.vencimento_real >= ? AND base.vencimento_real <= ?)
                OR
                (base.tipo <> 'PA' AND (
                    (base.pago = 1 AND base.baixa >= ? AND base.baixa <= ?)
                    OR
                    (base.pago = 0 AND base.vencimento_real >= ? AND base.vencimento_real <= ?)
                ))
            )
            {compensation_filter}
            GROUP BY base.natureza
            ORDER BY base.natureza
        """
        parameters = (
            normalized_branch, inicio_text, fim_text,
            inicio_text, fim_text, inicio_text, fim_text,
        )
        logger.info("Financeiro payment repository query started")
        with get_database_connection(self._settings) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, *parameters)
                rows = cursor.fetchall()
            finally:
                cursor.close()

        records: list[PagoLiquidoRecord] = []
        for row in rows:
            natureza = "" if row[0] is None else str(row[0]).strip()
            if not natureza:
                continue
            pago = _to_decimal(row[1])
            a_pagar = _to_decimal(row[2]) if len(row) > 2 else ZERO
            total = _to_decimal(row[3]) if len(row) > 3 else pago + a_pagar
            records.append(PagoLiquidoRecord(natureza, pago, a_pagar, total))
        logger.info("Financeiro payment repository query completed")
        return records
