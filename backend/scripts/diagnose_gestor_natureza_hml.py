import argparse
from collections.abc import Callable, Iterator, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any

from app.core.config import AppEnvironment, Settings, get_settings
from app.core.database import DatabaseError, get_database_connection
from app.core.protheus_tables import get_protheus_table_name


class HmlDiagnosisError(RuntimeError):
    """Raised when the diagnostic runner cannot execute safely."""


@dataclass(frozen=True)
class DiagnosticSection:
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]


@dataclass(frozen=True)
class NatureDiagnosis:
    filial: str
    ano: int
    mes: int
    natureza: str
    sections: tuple[DiagnosticSection, ...]


ConnectionFactory = Callable[[Settings], AbstractContextManager[Any]]

OPTIONAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "SZN": ("ZN_ITEPED",),
    "SC7": ("C7_ITEM", "C7_PRODUTO", "C7_PRECO", "C7_TOTAL"),
    "SEV": ("EV_VENCTO",),
    "SE2": (
        "E2_NATUREZ",
        "E2_EMISSAO",
        "E2_VENCREA",
        "E2_VALOR",
        "E2_SALDO",
        "E2_BAIXA",
        "E2_TIPO",
    ),
}


def _validate_input(
    settings: Settings, filial: str, ano: int, mes: int, natureza: str
) -> tuple[str, str, str]:
    if settings.app_env is not AppEnvironment.HML:
        raise HmlDiagnosisError("Diagnostic runner is available only in HML.")
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


def _existing_optional_columns(cursor: Any, table: str, prefix: str) -> tuple[str, ...]:
    candidates = OPTIONAL_COLUMNS[prefix]
    placeholders = ", ".join("?" for _ in candidates)
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME = ? AND COLUMN_NAME IN ({placeholders})",
        table,
        *candidates,
    )
    existing = {str(row[0]).strip().upper() for row in cursor.fetchall()}
    return tuple(column for column in candidates if column in existing)


def _section(cursor: Any, title: str, query: str, parameters: tuple[object, ...]) -> DiagnosticSection:
    cursor.execute(query, *parameters)
    columns = tuple(str(description[0]) for description in cursor.description)
    return DiagnosticSection(title, columns, tuple(tuple(row) for row in cursor.fetchall()))


def run_diagnosis(
    settings: Settings,
    filial: str,
    ano: int,
    mes: int,
    natureza: str,
    connection_factory: ConnectionFactory = get_database_connection,
) -> NatureDiagnosis:
    branch, period, code = _validate_input(settings, filial, ano, mes, natureza)
    tables = {
        prefix: get_protheus_table_name(prefix, settings)
        for prefix in ("SZN", "SC7", "SEV", "SE2")
    }

    with connection_factory(settings) as connection:
        cursor = connection.cursor()
        try:
            optional = {
                prefix: _existing_optional_columns(cursor, table, prefix)
                for prefix, table in tables.items()
            }

            pc_optional = "".join(
                f", szn.{column}" for column in optional["SZN"]
            ) + "".join(f", sc7.{column}" for column in optional["SC7"])
            pc_query = f"""
                SELECT szn.ZN_FILIAL, szn.ZN_NUMPED, szn.ZN_NATUREZ,
                       szn.ZN_SALDO, szn.ZN_VENCTO, szn.D_E_L_E_T_,
                       sc7.C7_FILIAL, sc7.C7_NUM, sc7.C7_QUANT,
                       sc7.C7_QUJE, sc7.C7_RESIDUO, sc7.D_E_L_E_T_{pc_optional}
                FROM {tables['SZN']} AS szn
                LEFT JOIN {tables['SC7']} AS sc7
                  ON sc7.C7_FILIAL = szn.ZN_FILIAL
                 AND sc7.C7_NUM = szn.ZN_NUMPED
                WHERE szn.ZN_FILIAL = ?
                  AND szn.ZN_NATUREZ = ?
                  AND szn.ZN_VENCTO LIKE ?
                ORDER BY szn.ZN_NUMPED, szn.ZN_VENCTO
            """

            sev_optional = "".join(
                f", sev.{column}" for column in optional["SEV"]
            )
            se2_optional = "".join(
                f", se2.{column}" for column in optional["SE2"]
            )
            nf_select = f"""
                SELECT sev.EV_FILIAL, sev.EV_PREFIXO, sev.EV_NUM,
                       sev.EV_PARCELA, sev.EV_CLIFOR, sev.EV_LOJA,
                       sev.EV_NATUREZ, sev.EV_VALOR, sev.EV_SITUACA,
                       sev.EV_IDENT, sev.D_E_L_E_T_, se2.E2_FILIAL,
                       se2.E2_PREFIXO, se2.E2_NUM, se2.E2_PARCELA,
                       se2.E2_FORNECE, se2.E2_LOJA, se2.E2_VENCTO,
                       se2.D_E_L_E_T_{sev_optional}{se2_optional}
            """
            nf_exact_query = nf_select + f"""
                FROM {tables['SEV']} AS sev
                INNER JOIN {tables['SE2']} AS se2
                  ON se2.E2_FILIAL = sev.EV_FILIAL
                 AND se2.E2_NUM = sev.EV_NUM
                 AND se2.E2_PREFIXO = sev.EV_PREFIXO
                 AND se2.E2_PARCELA = sev.EV_PARCELA
                 AND se2.E2_FORNECE = sev.EV_CLIFOR
                 AND se2.E2_LOJA = sev.EV_LOJA
                 AND se2.D_E_L_E_T_ = ''
                WHERE sev.EV_FILIAL = ? AND sev.EV_NATUREZ = ?
                  AND se2.E2_VENCTO LIKE ?
                  AND sev.EV_SITUACA NOT IN (?, ?)
                  AND sev.EV_IDENT = ?
                  AND sev.D_E_L_E_T_ = ''
                ORDER BY sev.EV_NUM, sev.EV_PARCELA
            """
            date_candidates = ["se2.E2_VENCTO LIKE ?"]
            date_parameters: list[object] = [period]
            for column in ("E2_VENCREA", "E2_EMISSAO"):
                if column in optional["SE2"]:
                    date_candidates.append(f"se2.{column} LIKE ?")
                    date_parameters.append(period)
            if "EV_VENCTO" in optional["SEV"]:
                date_candidates.append("sev.EV_VENCTO LIKE ?")
                date_parameters.append(period)
            nf_candidates_query = nf_select + f"""
                FROM {tables['SEV']} AS sev
                INNER JOIN {tables['SE2']} AS se2
                  ON se2.E2_FILIAL = sev.EV_FILIAL
                 AND se2.E2_NUM = sev.EV_NUM
                 AND se2.E2_PREFIXO = sev.EV_PREFIXO
                 AND se2.E2_PARCELA = sev.EV_PARCELA
                 AND se2.E2_FORNECE = sev.EV_CLIFOR
                 AND se2.E2_LOJA = sev.EV_LOJA
                WHERE sev.EV_FILIAL = ? AND sev.EV_NATUREZ = ?
                  AND ({' OR '.join(date_candidates)})
                ORDER BY sev.EV_NUM, sev.EV_PARCELA
            """

            sections = (
                _section(cursor, "PC — SZN x SC7 por pedido", pc_query, (branch, code, period)),
                _section(cursor, "NF — critérios atuais do repository", nf_exact_query, (branch, code, period, "E", "X", "1")),
                _section(cursor, "NF — candidatos por datas de julho", nf_candidates_query, (branch, code, *date_parameters)),
            )
            summary_sections: list[DiagnosticSection] = []
            for date_column in ("E2_VENCTO", "E2_VENCREA", "E2_EMISSAO"):
                if date_column != "E2_VENCTO" and date_column not in optional["SE2"]:
                    continue
                summary_query = f"""
                    SELECT LEFT(se2.{date_column}, 6) AS PERIODO,
                           COALESCE(SUM(sev.EV_VALOR), 0) AS TOTAL,
                           COUNT(*) AS REGISTROS
                    FROM {tables['SEV']} AS sev
                    INNER JOIN {tables['SE2']} AS se2
                      ON se2.E2_FILIAL = sev.EV_FILIAL
                     AND se2.E2_NUM = sev.EV_NUM
                     AND se2.E2_PREFIXO = sev.EV_PREFIXO
                     AND se2.E2_PARCELA = sev.EV_PARCELA
                     AND se2.E2_FORNECE = sev.EV_CLIFOR
                     AND se2.E2_LOJA = sev.EV_LOJA
                     AND se2.D_E_L_E_T_ = ''
                    WHERE sev.EV_FILIAL = ? AND sev.EV_NATUREZ = ?
                      AND se2.{date_column} LIKE ?
                      AND sev.EV_SITUACA NOT IN (?, ?)
                      AND sev.EV_IDENT = ?
                      AND sev.D_E_L_E_T_ = ''
                    GROUP BY LEFT(se2.{date_column}, 6)
                    ORDER BY LEFT(se2.{date_column}, 6)
                """
                summary_sections.append(
                    _section(
                        cursor,
                        f"NF — totais 2026 por {date_column}",
                        summary_query,
                        (branch, code, f"{ano:04d}%", "E", "X", "1"),
                    )
                )
            sections = sections + tuple(summary_sections)
        finally:
            cursor.close()

    return NatureDiagnosis(branch, ano, mes, code, sections)


def format_diagnosis(diagnosis: NatureDiagnosis) -> str:
    lines = [
        "Ambiente: HML",
        f"Filial: {diagnosis.filial}",
        f"Período: {diagnosis.ano:04d}/{diagnosis.mes:02d}",
        f"Natureza: {diagnosis.natureza}",
    ]
    for section in diagnosis.sections:
        lines.extend(("", section.title, f"Registros: {len(section.rows)}"))
        lines.append(" | ".join(section.columns))
        lines.extend(" | ".join("" if value is None else str(value) for value in row) for row in section.rows)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose one Gestor nature in HML using SELECT-only queries.")
    parser.add_argument("--filial", required=True)
    parser.add_argument("--ano", required=True, type=int)
    parser.add_argument("--mes", required=True, type=int)
    parser.add_argument("--natureza", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        diagnosis = run_diagnosis(get_settings(), args.filial, args.ano, args.mes, args.natureza)
    except (HmlDiagnosisError, DatabaseError, ValueError) as error:
        print(f"Diagnóstico não executado: {error}")
        return 1
    print(format_diagnosis(diagnosis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
