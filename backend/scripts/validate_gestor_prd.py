import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter

from app.core.config import Settings, get_settings
from app.core.database import DatabaseError, check_database_connection
from app.schemas.gestor import GestorPeriod, GestorResponse, GestorRow
from app.services.gestor_sql_service import GestorCompositionError, GestorSqlService
from scripts.prd_read_only_guard import (
    PrdReadOnlyValidationError,
    validate_prd_read_only_settings,
)


@dataclass(frozen=True)
class PrdValidationResult:
    response: GestorResponse
    elapsed_seconds: float
    selected_natureza: GestorRow | None
    requested_natureza: str | None


def run_validation(
    *,
    settings: Settings,
    filial: str,
    ano: int,
    mes: int,
    natureza: str | None = None,
    health_check: Callable[[Settings], None] = check_database_connection,
    service_factory: Callable[[], GestorSqlService] = GestorSqlService,
    clock: Callable[[], float] = perf_counter,
) -> PrdValidationResult:
    normalized_branch = filial.strip()
    if not normalized_branch:
        raise ValueError("filial must not be empty.")
    GestorPeriod(ano=ano, mes=mes)
    selected_code = natureza.strip() if natureza is not None else None
    if natureza is not None and not selected_code:
        raise ValueError("natureza must not be empty when provided.")

    validate_prd_read_only_settings(settings)
    health_check(settings)
    started_at = clock()
    response = service_factory().get_gestor(normalized_branch, ano, mes)
    elapsed_seconds = max(clock() - started_at, 0)
    selected = next(
        (
            row
            for row in response.linhas
            if selected_code is not None and row.natureza_codigo == selected_code
        ),
        None,
    )
    return PrdValidationResult(
        response=response,
        elapsed_seconds=elapsed_seconds,
        selected_natureza=selected,
        requested_natureza=selected_code,
    )


def _masked_branch(filial: str) -> str:
    return "***" + filial[-2:] if len(filial) >= 2 else "***"


def format_result(result: PrdValidationResult) -> str:
    response = result.response
    lines = [
        "Ambiente: PRD (validação controlada somente leitura)",
        f"Período: {response.periodo.ano:04d}/{response.periodo.mes:02d}",
        f"Filial: {_masked_branch(response.filial)}",
        f"Quantidade de Naturezas: {response.quantidade}",
        "Naturezas com Lim Original diferente de zero: "
        f"{sum(row.limite_original != 0 for row in response.linhas)}",
        "Naturezas com PC aberto diferente de zero: "
        f"{sum(row.pc_aberto != 0 for row in response.linhas)}",
        "Naturezas com NF entrada diferente de zero: "
        f"{sum(row.nf_entrada != 0 for row in response.linhas)}",
        "Naturezas com Contingência OK diferente de zero: "
        f"{sum(row.contingencia_ok != 0 for row in response.linhas)}",
        "Naturezas com Contingência em aprovação diferente de zero: "
        f"{sum(row.contingencia_em_aprovacao != 0 for row in response.linhas)}",
        "Naturezas com Saldo previsto negativo: "
        f"{sum(row.saldo_previsto < 0 for row in response.linhas)}",
        "Naturezas com Saldo real negativo: "
        f"{sum(row.saldo_real < 0 for row in response.linhas)}",
        f"Tempo total aproximado: {result.elapsed_seconds:.3f}s",
    ]
    if result.requested_natureza is not None:
        row = result.selected_natureza
        if row is None:
            lines.append("Natureza solicitada não encontrada no resultado.")
        else:
            lines.extend(
                [
                    "Recorte controlado:",
                    f"Código: {row.natureza_codigo}",
                    f"Descrição: {row.natureza_descricao}",
                    f"PC aberto: {row.pc_aberto}",
                    f"NF entrada: {row.nf_entrada}",
                    f"Contingência OK: {row.contingencia_ok}",
                    "Contingência em aprovação: "
                    f"{row.contingencia_em_aprovacao}",
                    f"Lim Original: {row.limite_original}",
                    f"Lim Total: {row.limite_total}",
                    f"Saldo previsto: {row.saldo_previsto}",
                    f"Saldo real: {row.saldo_real}",
                ]
            )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Gestor safely in opt-in PRD read-only mode."
    )
    parser.add_argument("--filial", required=True)
    parser.add_argument("--ano", required=True, type=int)
    parser.add_argument("--mes", required=True, type=int)
    parser.add_argument("--natureza")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_validation(
            settings=get_settings(),
            filial=args.filial,
            ano=args.ano,
            mes=args.mes,
            natureza=args.natureza,
        )
    except (PrdReadOnlyValidationError, DatabaseError, ValueError) as error:
        print(f"Validação PRD não executada: {error}")
        return 1
    except GestorCompositionError as error:
        print(f"Composição PRD inconsistente: {error}")
        return 1
    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
