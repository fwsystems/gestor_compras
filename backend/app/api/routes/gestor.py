from typing import Annotated
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import AfterValidator

from app.core.config import GestorDataEnvironment
from app.core.database import DatabaseError
from app.core.gestor_environments import is_gestor_data_environment_available
from app.schemas.gestor import (
    GestorEnvironmentOption,
    GestorEnvironmentsResponse,
    GestorDetailResponse,
    GestorDetailType,
    GestorResponse,
    GestorTimelinePoint,
)
from app.services.gestor_service_provider import (
    GestorEnvironmentUnavailableError,
    get_gestor_service,
)
from app.services.gestor_sql_service import GestorCompositionError

router = APIRouter(tags=["gestor"])

GESTOR_ENVIRONMENT_LABELS = {
    GestorDataEnvironment.DEV: "DEV",
    GestorDataEnvironment.HML: "HML",
    GestorDataEnvironment.PRD: "PRD",
}
GESTOR_INITIAL_ENVIRONMENT_ORDER = (
    GestorDataEnvironment.PRD,
    GestorDataEnvironment.HML,
    GestorDataEnvironment.DEV,
)


def select_default_gestor_environment(
    availability: dict[GestorDataEnvironment, bool],
) -> GestorDataEnvironment:
    return next(
        environment
        for environment in GESTOR_INITIAL_ENVIRONMENT_ORDER
        if availability.get(environment, False)
    )


def normalize_filial(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("filial cannot be empty")
    return normalized


@router.get(
    "/gestor/environments",
    response_model=GestorEnvironmentsResponse,
    summary="Listar ambientes de dados do Gestor",
)
def gestor_environments() -> GestorEnvironmentsResponse:
    availability = {
        environment: is_gestor_data_environment_available(environment)
        for environment in GestorDataEnvironment
    }
    return GestorEnvironmentsResponse(
        default=select_default_gestor_environment(availability),
        environments=[
            GestorEnvironmentOption(
                id=environment,
                label=GESTOR_ENVIRONMENT_LABELS[environment],
                available=availability[environment],
            )
            for environment in GestorDataEnvironment
        ],
    )


@router.get(
    "/gestor/details",
    response_model=GestorDetailResponse,
    summary="Detalhar componentes financeiros por natureza",
    description="Consulta somente leitura, sob demanda, no ambiente informado.",
)
def gestor_details(
    ano: Annotated[int, Query(ge=2000, le=2100)],
    mes: Annotated[int, Query(ge=1, le=12)],
    filial: Annotated[str, Query(min_length=1), AfterValidator(normalize_filial)],
    natureza: Annotated[str, Query(min_length=1)],
    tipo: GestorDetailType,
    ambiente: GestorDataEnvironment,
    inicio: date | None = None,
    fim: date | None = None,
) -> GestorDetailResponse:
    try:
        service = get_gestor_service(ambiente)
        arguments = dict(
            ambiente=ambiente,
            filial=filial,
            ano=ano,
            mes=mes,
            natureza=natureza,
            tipo=tipo,
        )
        if inicio is not None or fim is not None:
            arguments.update(inicio=inicio, fim=fim)
        return service.get_details(**arguments)
    except (DatabaseError, GestorCompositionError, GestorEnvironmentUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gestor detail is unavailable or inconsistent.",
        ) from None


@router.get(
    "/gestor/timeline",
    response_model=list[GestorTimelinePoint],
    summary="Consultar evolução mensal do Gestor",
    description="Compõe cada mês com a mesma regra mensal do Gestor, em modo somente leitura.",
)
def gestor_timeline(
    ano: Annotated[int, Query(ge=2000, le=2100)],
    mes: Annotated[int, Query(ge=1, le=12)],
    filial: Annotated[str, Query(min_length=1), AfterValidator(normalize_filial)],
    ambiente: GestorDataEnvironment = GestorDataEnvironment.HML,
) -> list[GestorTimelinePoint]:
    try:
        service = get_gestor_service(ambiente)
        points: list[GestorTimelinePoint] = []
        for current_month in range(1, mes + 1):
            gestor_month = service.get_gestor(filial=filial, ano=ano, mes=current_month)
            points.append(
                GestorTimelinePoint(
                    ano=ano,
                    mes=current_month,
                    limite_total=sum((row.limite_total for row in gestor_month.linhas), 0),
                    nf_entrada=sum((row.nf_entrada for row in gestor_month.linhas), 0),
                    saldo_previsto=sum((row.saldo_previsto for row in gestor_month.linhas), 0),
                )
            )
        return points
    except (DatabaseError, GestorCompositionError, GestorEnvironmentUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gestor timeline is unavailable.",
        ) from None


@router.get(
    "/gestor",
    response_model=GestorResponse,
    summary="Consultar o Gestor de Compras",
    description="Retorna o Gestor pela fonte habilitada para o ambiente.",
)
def gestor(
    ano: Annotated[int, Query(ge=2000, le=2100)],
    mes: Annotated[int, Query(ge=1, le=12)],
    filial: Annotated[
        str,
        Query(min_length=1),
        AfterValidator(normalize_filial),
    ],
    ambiente: GestorDataEnvironment = GestorDataEnvironment.HML,
    inicio: date | None = None,
    fim: date | None = None,
) -> GestorResponse:
    try:
        service = get_gestor_service(ambiente)
        arguments = dict(filial=filial, ano=ano, mes=mes)
        if inicio is not None or fim is not None:
            arguments.update(inicio=inicio, fim=fim)
        return service.get_gestor(**arguments)
    except (DatabaseError, GestorCompositionError, GestorEnvironmentUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gestor data source is unavailable.",
        ) from None
