from collections.abc import Callable
from typing import Protocol
from datetime import date

from app.core.config import GestorDataEnvironment, Settings
from app.core.gestor_environments import (
    GestorDataEnvironmentUnavailableError,
    get_gestor_data_settings,
)
from app.schemas.gestor import GestorDetailResponse, GestorDetailType, GestorResponse
from app.services.gestor_service import (
    get_gestor as get_mock_gestor,
    get_gestor_details as get_mock_gestor_details,
)
from app.services.gestor_sql_service import GestorSqlService


class GestorService(Protocol):
    def get_gestor(self, filial: str, ano: int, mes: int, inicio: date | None = None, fim: date | None = None) -> GestorResponse: ...

    def get_details(
        self,
        *,
        ambiente: GestorDataEnvironment,
        filial: str,
        ano: int,
        mes: int,
        natureza: str,
        tipo: GestorDetailType,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> GestorDetailResponse: ...


class MockGestorService:
    def get_gestor(self, filial: str, ano: int, mes: int, inicio: date | None = None, fim: date | None = None) -> GestorResponse:
        return get_mock_gestor(filial=filial, ano=ano, mes=mes, inicio=inicio, fim=fim)

    def get_details(
        self,
        *,
        ambiente: GestorDataEnvironment,
        filial: str,
        ano: int,
        mes: int,
        natureza: str,
        tipo: GestorDetailType,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> GestorDetailResponse:
        return get_mock_gestor_details(
            ambiente=ambiente,
            filial=filial,
            ano=ano,
            mes=mes,
            natureza=natureza,
            tipo=tipo,
            inicio=inicio,
            fim=fim,
        )


class GestorEnvironmentUnavailableError(RuntimeError):
    """Raised when the Gestor source is not enabled for an environment."""


def get_gestor_service(
    environment: GestorDataEnvironment,
    *,
    settings_resolver: Callable[[GestorDataEnvironment], Settings] = (
        get_gestor_data_settings
    ),
) -> GestorService:
    if environment is GestorDataEnvironment.DEV:
        return MockGestorService()
    try:
        settings = settings_resolver(environment)
    except GestorDataEnvironmentUnavailableError as error:
        raise GestorEnvironmentUnavailableError(
            "Gestor is not enabled for the requested environment."
        ) from error
    return GestorSqlService(settings=settings)
