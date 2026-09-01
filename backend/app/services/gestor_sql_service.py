from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Protocol, TypeVar

from app.core.config import Settings
from app.repositories.contingencia_repository import (
    ContingenciaDetailRecord,
    ContingenciaRecord,
    ContingenciaRepository,
)
from app.repositories.limite_repository import LimiteRecord, LimiteRepository
from app.repositories.natureza_repository import NaturezaRecord, NaturezaRepository
from app.repositories.nf_entrada_repository import (
    NfEntradaDetailRecord,
    NfEntradaRecord,
    NfEntradaRepository,
)
from app.repositories.pc_aberto_repository import (
    PcAbertoDetailRecord,
    PcAbertoRecord,
    PcAbertoRepository,
)
from app.schemas.gestor import (
    GestorContingenciaDetailRecord,
    GestorDetailResponse,
    GestorDetailType,
    GestorNfEntradaDetailRecord,
    GestorPcAbertoDetailRecord,
    GestorPeriod,
    GestorResponse,
    GestorRow,
)
from app.core.config import GestorDataEnvironment
from app.services.gestor_period import GestorInterval, limit_factor, proportional_limit

ZERO = Decimal("0")


class _NaturezaKeyed(Protocol):
    natureza: str


RecordT = TypeVar("RecordT", bound=_NaturezaKeyed)


class GestorCompositionError(RuntimeError):
    """Base error for inconsistent repository results."""


class UnexpectedGestorNaturezaError(GestorCompositionError):
    def __init__(self, source: str, natureza: str) -> None:
        self.source = source
        self.natureza = natureza
        super().__init__(
            "Financial nature is missing from the nature catalog "
            f"source={source} natureza={natureza or '<empty>'}."
        )


class DuplicateGestorNaturezaError(GestorCompositionError):
    def __init__(self, source: str, natureza: str) -> None:
        self.source = source
        self.natureza = natureza
        super().__init__(f"Duplicate nature from {source}: {natureza or '<empty>'}.")


class GestorDetailInconsistencyError(GestorCompositionError):
    def __init__(self, tipo: GestorDetailType, natureza: str) -> None:
        self.tipo = tipo
        self.natureza = natureza
        super().__init__(
            f"Detail does not match consolidated total: {tipo.value} {natureza}."
        )


def _index_financial_records(
    records: Iterable[RecordT],
    source: str,
) -> dict[str, RecordT]:
    indexed: dict[str, RecordT] = {}
    for record in records:
        natureza = record.natureza.strip()
        if not natureza:
            raise UnexpectedGestorNaturezaError(source, natureza)
        if natureza in indexed:
            raise DuplicateGestorNaturezaError(source, natureza)
        indexed[natureza] = record
    return indexed


@dataclass(frozen=True)
class GestorSqlRepositories:
    natureza: NaturezaRepository
    limite: LimiteRepository
    pc_aberto: PcAbertoRepository
    nf_entrada: NfEntradaRepository
    contingencia: ContingenciaRepository


class GestorSqlService:
    """Compose Gestor rows from the five read-only batch repositories."""

    def __init__(
        self,
        settings: Settings | None = None,
        natureza_repository: NaturezaRepository | None = None,
        limite_repository: LimiteRepository | None = None,
        pc_aberto_repository: PcAbertoRepository | None = None,
        nf_entrada_repository: NfEntradaRepository | None = None,
        contingencia_repository: ContingenciaRepository | None = None,
    ) -> None:
        self._repositories = GestorSqlRepositories(
            natureza=natureza_repository or NaturezaRepository(settings),
            limite=limite_repository or LimiteRepository(settings),
            pc_aberto=pc_aberto_repository or PcAbertoRepository(settings),
            nf_entrada=nf_entrada_repository or NfEntradaRepository(settings),
            contingencia=contingencia_repository or ContingenciaRepository(settings),
        )

    def get_gestor(
        self,
        filial: str,
        ano: int,
        mes: int,
        inicio: date | None = None,
        fim: date | None = None,
    ) -> GestorResponse:
        normalized_branch = filial.strip()
        if not normalized_branch:
            raise ValueError("filial must not be empty.")
        period = GestorPeriod(ano=ano, mes=mes)
        interval = self._interval(inicio, fim, ano, mes)
        factor = limit_factor(interval, ano, mes)

        naturezas = self._repositories.natureza.list_naturezas(normalized_branch)
        limites = self._repositories.limite.list_limites(
            normalized_branch, ano, mes
        )
        pcs = self._repositories.pc_aberto.list_pc_aberto(
            normalized_branch, ano, mes, **self._interval_kwargs(interval)
        )
        nfs = self._repositories.nf_entrada.list_nf_entrada(
            normalized_branch, ano, mes, **self._interval_kwargs(interval)
        )
        contingencias = self._repositories.contingencia.list_contingencias(
            normalized_branch, ano, mes, **self._interval_kwargs(interval)
        )

        catalog_by_code: dict[str, NaturezaRecord] = {}
        for natureza in naturezas:
            codigo = natureza.codigo.strip()
            if not codigo:
                raise UnexpectedGestorNaturezaError("NaturezaRepository", codigo)
            if codigo in catalog_by_code:
                raise DuplicateGestorNaturezaError("NaturezaRepository", codigo)
            catalog_by_code[codigo] = natureza
        limites_by_natureza = _index_financial_records(
            limites, "LimiteRepository"
        )
        pcs_by_natureza = _index_financial_records(
            pcs, "PcAbertoRepository"
        )
        nfs_by_natureza = _index_financial_records(
            nfs, "NfEntradaRepository"
        )
        contingencias_by_natureza = _index_financial_records(
            contingencias, "ContingenciaRepository"
        )

        financial_codes = (
            limites_by_natureza.keys()
            | pcs_by_natureza.keys()
            | nfs_by_natureza.keys()
            | contingencias_by_natureza.keys()
        )
        relevant_codes = catalog_by_code.keys() & financial_codes

        linhas: list[GestorRow] = []
        for codigo in sorted(relevant_codes):
            natureza = catalog_by_code[codigo]
            limite = limites_by_natureza.get(codigo)
            pc = pcs_by_natureza.get(codigo)
            nf = nfs_by_natureza.get(codigo)
            contingencia = contingencias_by_natureza.get(codigo)

            limite_original = proportional_limit(
                limite.valor if limite is not None else ZERO,
                factor,
            )
            pc_aberto = pc.valor if pc is not None else ZERO
            nf_entrada = nf.valor if nf is not None else ZERO
            contingencia_ok = (
                contingencia.contingencia_ok if contingencia is not None else ZERO
            )
            contingencia_em_aprovacao = (
                contingencia.contingencia_em_aprovacao
                if contingencia is not None
                else ZERO
            )
            limite_total = limite_original + contingencia_ok

            linhas.append(
                GestorRow(
                    natureza_codigo=codigo,
                    natureza_descricao=natureza.descricao,
                    pc_aberto=pc_aberto,
                    nf_entrada=nf_entrada,
                    contingencia_ok=contingencia_ok,
                    contingencia_em_aprovacao=contingencia_em_aprovacao,
                    limite_original=limite_original,
                    limite_total=limite_total,
                    saldo_previsto=limite_total - pc_aberto - nf_entrada,
                    saldo_real=limite_total - nf_entrada,
                )
            )

        return GestorResponse(
            periodo=period,
            filial=normalized_branch,
            linhas=linhas,
            quantidade=len(linhas),
        )

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
        normalized_branch = filial.strip()
        normalized_nature = natureza.strip()
        if not normalized_branch:
            raise ValueError("filial must not be empty.")
        if not normalized_nature:
            raise ValueError("natureza must not be empty.")
        period = GestorPeriod(ano=ano, mes=mes)
        interval = self._interval(inicio, fim, ano, mes)
        interval_kwargs = self._interval_kwargs(interval)

        catalog = {
            item.codigo.strip(): item
            for item in self._repositories.natureza.list_naturezas(normalized_branch)
        }
        catalog_record = catalog.get(normalized_nature)
        if catalog_record is None:
            raise UnexpectedGestorNaturezaError("NaturezaRepository", normalized_nature)

        if tipo is GestorDetailType.PC_ABERTO:
            consolidated = self._find_consolidated_total(
                self._repositories.pc_aberto.list_pc_aberto(
                    normalized_branch, ano, mes, **interval_kwargs
                ),
                normalized_nature,
            )
            source_records = self._repositories.pc_aberto.list_pc_aberto_details(
                normalized_branch, ano, mes, normalized_nature, **interval_kwargs
            )
            self._validate_detail_records(
                source_records, consolidated, tipo, normalized_nature
            )
            records = [
                GestorPcAbertoDetailRecord(
                    pedido=record.pedido,
                    vencimento=record.vencimento,
                    valor=record.valor,
                )
                for record in source_records
            ]
        elif tipo is GestorDetailType.NF_ENTRADA:
            consolidated = self._find_consolidated_total(
                self._repositories.nf_entrada.list_nf_entrada(
                    normalized_branch, ano, mes, **interval_kwargs
                ),
                normalized_nature,
            )
            source_records = self._repositories.nf_entrada.list_nf_entrada_details(
                normalized_branch, ano, mes, normalized_nature, **interval_kwargs
            )
            self._validate_detail_records(
                source_records, consolidated, tipo, normalized_nature
            )
            records = [
                GestorNfEntradaDetailRecord(
                    documento=record.documento,
                    prefixo=record.prefixo,
                    parcela=record.parcela,
                    fornecedor=record.fornecedor,
                    fornecedor_nome=record.fornecedor_nome,
                    loja=record.loja,
                    emissao=record.emissao,
                    vencimento=record.vencimento,
                    valor=record.valor,
                )
                for record in source_records
            ]
        else:
            contingencias = self._repositories.contingencia.list_contingencias(
                normalized_branch, ano, mes, **interval_kwargs
            )
            consolidated_record = next(
                (
                    record
                    for record in contingencias
                    if record.natureza.strip() == normalized_nature
                ),
                None,
            )
            if tipo is GestorDetailType.CONTINGENCIA_OK:
                consolidated = (
                    consolidated_record.contingencia_ok
                    if consolidated_record is not None
                    else ZERO
                )
                source_records = (
                    self._repositories.contingencia.list_contingencia_ok_details(
                        normalized_branch, ano, mes, normalized_nature, **interval_kwargs
                    )
                )
            else:
                consolidated = (
                    consolidated_record.contingencia_em_aprovacao
                    if consolidated_record is not None
                    else ZERO
                )
                source_records = (
                    self._repositories.contingencia.list_contingencia_aprovacao_details(
                        normalized_branch, ano, mes, normalized_nature, **interval_kwargs
                    )
                )
            self._validate_detail_records(
                source_records, consolidated, tipo, normalized_nature
            )
            records = [
                GestorContingenciaDetailRecord(
                    pedido=record.pedido,
                    item=record.item,
                    vencimento=record.vencimento,
                    usuario=record.usuario,
                    status=record.status,
                    valor=record.valor,
                )
                for record in source_records
            ]

        return GestorDetailResponse(
            ambiente=ambiente,
            filial=normalized_branch,
            periodo=period,
            natureza_codigo=normalized_nature,
            natureza_descricao=catalog_record.descricao,
            tipo=tipo,
            quantidade=len(records),
            total=consolidated,
            registros=records,
        )

    @staticmethod
    def _find_consolidated_total(
        records: Iterable[PcAbertoRecord | NfEntradaRecord],
        natureza: str,
    ) -> Decimal:
        return next(
            (record.valor for record in records if record.natureza.strip() == natureza),
            ZERO,
        )

    @staticmethod
    def _validate_detail_records(
        records: Iterable[
            PcAbertoDetailRecord | NfEntradaDetailRecord | ContingenciaDetailRecord
        ],
        consolidated: Decimal,
        tipo: GestorDetailType,
        natureza: str,
    ) -> None:
        materialized = list(records)
        total = sum((record.valor for record in materialized), ZERO)
        has_wrong_nature = any(record.natureza.strip() != natureza for record in materialized)
        if total != consolidated or has_wrong_nature or (consolidated != ZERO and not materialized):
            raise GestorDetailInconsistencyError(tipo, natureza)

    @staticmethod
    def _interval(
        inicio: date | None,
        fim: date | None,
        ano: int,
        mes: int,
    ) -> GestorInterval | None:
        if inicio is None and fim is None:
            return None
        if inicio is None or fim is None:
            raise ValueError("inicio and fim must be provided together.")
        interval = GestorInterval(inicio, fim)
        if inicio.year != ano or inicio.month != mes or fim.year != ano or fim.month != mes:
            raise ValueError("interval must be contained in the requested month.")
        return interval

    @staticmethod
    def _interval_kwargs(interval: GestorInterval | None) -> dict[str, date]:
        return {} if interval is None else {"inicio": interval.start, "fim": interval.end}
