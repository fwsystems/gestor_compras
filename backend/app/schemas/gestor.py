from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)
from pydantic.alias_generators import to_camel

from app.core.config import GestorDataEnvironment


Money = Annotated[
    Decimal,
    Field(allow_inf_nan=False),
    PlainSerializer(lambda value: float(value), return_type=float, when_used="json"),
]


class GestorSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        str_strip_whitespace=True,
    )


class GestorPeriod(GestorSchema):
    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)


class GestorRow(GestorSchema):
    natureza_codigo: str = Field(min_length=1)
    natureza_descricao: str = Field(min_length=1)
    pc_aberto: Money
    nf_entrada: Money
    contingencia_ok: Money
    contingencia_em_aprovacao: Money
    limite_original: Money
    limite_total: Money
    saldo_previsto: Money
    saldo_real: Money


class GestorResponse(GestorSchema):
    periodo: GestorPeriod
    filial: str = Field(min_length=1)
    linhas: list[GestorRow]
    quantidade: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_quantidade(self) -> "GestorResponse":
        if self.quantidade != len(self.linhas):
            raise ValueError("quantidade must match the number of linhas")
        return self


class GestorTimelinePoint(GestorSchema):
    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    limite_total: Money
    nf_entrada: Money
    saldo_previsto: Money


class GestorDetailType(str, Enum):
    PC_ABERTO = "pc_aberto"
    NF_ENTRADA = "nf_entrada"
    CONTINGENCIA_OK = "contingencia_ok"
    CONTINGENCIA_APROVACAO = "contingencia_aprovacao"


class GestorPcAbertoDetailRecord(GestorSchema):
    pedido: str
    vencimento: str
    valor: Money


class GestorNfEntradaDetailRecord(GestorSchema):
    documento: str
    prefixo: str
    parcela: str
    fornecedor: str
    fornecedor_nome: str
    loja: str
    emissao: str
    vencimento: str
    valor: Money


class GestorContingenciaDetailRecord(GestorSchema):
    pedido: str
    item: str
    vencimento: str
    usuario: str
    status: str
    valor: Money


GestorDetailRecord = (
    GestorPcAbertoDetailRecord
    | GestorNfEntradaDetailRecord
    | GestorContingenciaDetailRecord
)


class GestorDetailResponse(GestorSchema):
    ambiente: GestorDataEnvironment
    filial: str = Field(min_length=1)
    periodo: GestorPeriod
    natureza_codigo: str = Field(min_length=1)
    natureza_descricao: str = Field(min_length=1)
    tipo: GestorDetailType
    quantidade: int = Field(ge=0)
    total: Money
    registros: list[GestorDetailRecord]

    @model_validator(mode="after")
    def validate_details(self) -> "GestorDetailResponse":
        if self.quantidade != len(self.registros):
            raise ValueError("quantidade must match the number of registros")
        if self.total != sum((record.valor for record in self.registros), Decimal("0")):
            raise ValueError("total must match the sum of registros")
        return self


class GestorEnvironmentOption(GestorSchema):
    id: GestorDataEnvironment
    label: str
    available: bool


class GestorEnvironmentsResponse(GestorSchema):
    default: GestorDataEnvironment
    environments: list[GestorEnvironmentOption]
