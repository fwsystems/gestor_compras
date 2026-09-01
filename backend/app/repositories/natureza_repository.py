import logging
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.core.database import DatabaseError, get_database_connection
from app.core.gestor import GESTOR_COMPRAS_PAINEL
from app.core.protheus_tables import get_protheus_table_name

logger = logging.getLogger(__name__)


class AmbiguousNaturezaError(DatabaseError):
    """Raised when SED returns duplicate normalized nature codes."""


@dataclass(frozen=True)
class NaturezaRecord:
    codigo: str
    descricao: str


class NaturezaRepository:
    """Read the eligible Gestor nature universe from SED and SE7."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def list_naturezas(self, filial: str) -> list[NaturezaRecord]:
        normalized_branch = filial.strip()
        if not normalized_branch:
            raise ValueError("filial must not be empty.")
        sed_table = get_protheus_table_name("SED", self._settings)
        se7_table = get_protheus_table_name("SE7", self._settings)

        query = f"""
            SELECT
                sed.ED_CODIGO,
                COALESCE(sed.ED_DESCRIC, '')
            FROM {sed_table} AS sed
            WHERE sed.ED_FILIAL = ?
              AND sed.D_E_L_E_T_ = ''
              AND sed.ED_ZPAINEL = ?
              AND NULLIF(LTRIM(RTRIM(sed.ED_CODIGO)), '') IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM {se7_table} AS se7
                  WHERE se7.E7_FILIAL = sed.ED_FILIAL
                    AND se7.E7_NATUREZ = sed.ED_CODIGO
                    AND se7.D_E_L_E_T_ = ''
              )
            ORDER BY sed.ED_CODIGO
        """

        logger.info("Natureza repository query started")
        with get_database_connection(self._settings) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, normalized_branch, GESTOR_COMPRAS_PAINEL)
                rows = cursor.fetchall()
            finally:
                cursor.close()

        records_by_code: dict[str, NaturezaRecord] = {}
        for row in rows:
            codigo = "" if row[0] is None else str(row[0]).strip()
            if not codigo:
                continue
            descricao = "" if row[1] is None else str(row[1]).strip()
            if codigo in records_by_code:
                raise AmbiguousNaturezaError(
                    "Multiple SED rows exist for the same normalized nature."
                )
            records_by_code[codigo] = NaturezaRecord(
                codigo=codigo, descricao=descricao
            )

        logger.info("Natureza repository query completed")
        return sorted(records_by_code.values(), key=lambda record: record.codigo)
