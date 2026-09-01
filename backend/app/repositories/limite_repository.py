import logging
from dataclasses import dataclass
from decimal import Decimal

from app.core.config import Settings, get_settings
from app.core.database import DatabaseError, get_database_connection
from app.core.protheus_tables import get_protheus_table_name

logger = logging.getLogger(__name__)

MONTH_VALUE_COLUMNS: dict[int, str] = {
    1: "E7_VALJAN1",
    2: "E7_VALFEV1",
    3: "E7_VALMAR1",
    4: "E7_VALABR1",
    5: "E7_VALMAI1",
    6: "E7_VALJUN1",
    7: "E7_VALJUL1",
    8: "E7_VALAGO1",
    9: "E7_VALSET1",
    10: "E7_VALOUT1",
    11: "E7_VALNOV1",
    12: "E7_VALDEZ1",
}


class AmbiguousLimiteError(DatabaseError):
    """Raised when SE7 returns multiple applicable rows for one nature."""


@dataclass(frozen=True)
class LimiteRecord:
    natureza: str
    ano: int
    mes: int
    valor: Decimal


def _validate_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized


def _validate_period(ano: int, mes: int) -> str:
    if not 2000 <= ano <= 2100:
        raise ValueError("ano must be between 2000 and 2100.")
    if mes not in MONTH_VALUE_COLUMNS:
        raise ValueError("mes must be between 1 and 12.")
    return str(ano)


def _to_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class LimiteRepository:
    """Read original monthly budget values from SE7 without composing balances."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def list_limites(self, filial: str, ano: int, mes: int) -> list[LimiteRecord]:
        return self._fetch_limites(filial=filial, ano=ano, mes=mes)

    def get_limite(
        self,
        filial: str,
        natureza: str,
        ano: int,
        mes: int,
    ) -> LimiteRecord | None:
        records = self._fetch_limites(
            filial=filial,
            ano=ano,
            mes=mes,
            natureza=natureza,
        )
        return records[0] if records else None

    def _fetch_limites(
        self,
        filial: str,
        ano: int,
        mes: int,
        natureza: str | None = None,
    ) -> list[LimiteRecord]:
        normalized_branch = _validate_required_text(filial, "filial")
        physical_year = _validate_period(ano, mes)
        month_column = MONTH_VALUE_COLUMNS[mes]
        se7_table = get_protheus_table_name("SE7", self._settings)
        parameters = [normalized_branch, physical_year]
        nature_filter = ""

        if natureza is not None:
            normalized_nature = _validate_required_text(natureza, "natureza")
            nature_filter = "\n              AND se7.E7_NATUREZ = ?"
            parameters.append(normalized_nature)

        query = f"""
            SELECT
                se7.E7_NATUREZ,
                se7.{month_column}
            FROM {se7_table} AS se7
            WHERE se7.E7_FILIAL = ?
              AND se7.E7_ANO = ?
              AND se7.D_E_L_E_T_ = ''{nature_filter}
            ORDER BY se7.E7_NATUREZ
        """

        logger.info("Limite repository query started")
        with get_database_connection(self._settings) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, *parameters)
                rows = cursor.fetchall()
            finally:
                cursor.close()

        records_by_nature: dict[str, LimiteRecord] = {}
        for row in rows:
            normalized_nature = "" if row[0] is None else str(row[0]).strip()
            if not normalized_nature:
                continue
            if normalized_nature in records_by_nature:
                raise AmbiguousLimiteError(
                    "Multiple budget rows exist for the same nature and period."
                )
            records_by_nature[normalized_nature] = LimiteRecord(
                natureza=normalized_nature,
                ano=ano,
                mes=mes,
                valor=_to_decimal(row[1]),
            )

        logger.info("Limite repository query completed")
        return sorted(records_by_nature.values(), key=lambda record: record.natureza)
