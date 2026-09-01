import argparse
from collections.abc import Callable, Sequence
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.database import DatabaseError, check_database_connection
from scripts.diagnose_pc_aberto_hml import (
    ConnectionFactory,
    PcAbertoDiagnosis,
    _PcRepository,
    format_diagnosis,
    run_read_only_diagnosis,
    validate_diagnosis_input,
)
from scripts.prd_read_only_guard import (
    PrdReadOnlyValidationError,
    validate_prd_read_only_settings,
)


def run_diagnosis(
    *,
    settings: Settings,
    filial: str,
    ano: int,
    mes: int,
    natureza: str,
    health_check: Callable[[Settings], None] = check_database_connection,
    diagnosis_runner: Callable[..., PcAbertoDiagnosis] = run_read_only_diagnosis,
    repository: _PcRepository | None = None,
    connection_factory: ConnectionFactory | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> PcAbertoDiagnosis:
    validate_diagnosis_input(filial, ano, mes, natureza)
    validate_prd_read_only_settings(settings)
    health_check(settings)
    arguments = {
        "settings": settings,
        "filial": filial,
        "ano": ano,
        "mes": mes,
        "natureza": natureza,
        "repository": repository,
        "now": now,
    }
    if connection_factory is not None:
        arguments["connection_factory"] = connection_factory
    return diagnosis_runner(**arguments)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diagnose PC aberto in opt-in PRD read-only mode."
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
    except (PrdReadOnlyValidationError, DatabaseError, ValueError) as error:
        print(f"Diagnóstico PRD de PC aberto não executado: {error}")
        return 1
    print(
        format_diagnosis(
            diagnosis, "PRD (validação controlada somente leitura)"
        )
    )
    return (
        0
        if diagnosis.total_repository == diagnosis.total_elegivel_diagnostico
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
