from decimal import ROUND_HALF_UP, Decimal
from typing import TypeAlias

from app.schemas.gestor import GestorRow


BaseGestorRow: TypeAlias = tuple[str, str, str, str, str, str, str]
PeriodFactors: TypeAlias = tuple[str, str, str, str, str]


def create_gestor_row(values: BaseGestorRow) -> GestorRow:
    (
        natureza_codigo,
        natureza_descricao,
        pc_aberto_raw,
        nf_entrada_raw,
        contingencia_ok_raw,
        contingencia_em_aprovacao_raw,
        limite_original_raw,
    ) = values
    pc_aberto = Decimal(pc_aberto_raw)
    nf_entrada = Decimal(nf_entrada_raw)
    contingencia_ok = Decimal(contingencia_ok_raw)
    contingencia_em_aprovacao = Decimal(contingencia_em_aprovacao_raw)
    limite_original = Decimal(limite_original_raw)
    return GestorRow(
        natureza_codigo=natureza_codigo,
        natureza_descricao=natureza_descricao,
        pc_aberto=pc_aberto,
        nf_entrada=nf_entrada,
        contingencia_ok=contingencia_ok,
        contingencia_em_aprovacao=contingencia_em_aprovacao,
        limite_original=limite_original,
        saldo_previsto=limite_original - pc_aberto - nf_entrada,
        saldo_real=limite_original - nf_entrada,
    )


SEPTEMBER_BASE_ROWS: tuple[BaseGestorRow, ...] = (
    ("4.000-010", "MATÉRIA-PRIMA", "40000", "30000", "10000", "0", "160000"),
    ("4.000-020", "MATERIAL DE CONSUMO", "0", "12000", "0", "5000", "35000"),
    ("4.000-030", "FERRAMENTAS", "5000", "0", "0", "0", "5000"),
    ("4.000-040", "ACESS P/ DISPOS ITENS NOVOS", "80000", "25000", "15000", "7500", "70000"),
    ("4.000-050", "MANUTENÇÃO INDUSTRIAL", "0", "95000", "10000", "0", "75000"),
    ("4.000-060", "MATERIAL DE ESCRITÓRIO", "120.5", "79.5", "0", "0", "200"),
    ("4.000-070", "SERVIÇOS DE TERCEIROS", "48000", "32000", "25000", "12000", "90000"),
    ("4.000-080", "FRETES", "18000", "42000", "0", "8000", "55000"),
    ("4.000-090", "EMBALAGENS", "67000", "52000", "20000", "0", "140000"),
    ("4.000-100", "EQUIPAMENTOS", "215000", "80000", "50000", "30000", "275000"),
    ("4.000-110", "INFORMÁTICA", "22000", "18000", "0", "0", "65000"),
    ("4.000-120", "EPI", "14500", "23500", "5000", "2500", "40000"),
    ("4.000-130", "LIMPEZA", "0", "0", "0", "0", "15000"),
    ("4.000-140", "LABORATÓRIO", "9500", "15500", "12000", "0", "28000"),
    ("4.000-150", "CALIBRAÇÃO", "6500", "11000", "0", "4000", "22000"),
    ("4.000-160", "MANUTENÇÃO PREDIAL", "36000", "49000", "10000", "15000", "70000"),
    ("4.000-170", "ENERGIA / UTILIDADES", "0", "198000", "0", "0", "210000"),
    ("4.000-180", "QUALIDADE", "17500", "9500", "7500", "3500", "45000"),
    ("4.000-190", "PRODUÇÃO", "320000", "145000", "80000", "45000", "420000"),
    ("4.000-200", "OUTROS MATERIAIS", "8750.25", "12450.75", "2500", "0", "24000"),
)

OCTOBER_ADDITIONAL_ROWS: tuple[BaseGestorRow, ...] = (
    ("4.000-210", "SEGURANÇA PATRIMONIAL", "18500", "26000", "5000", "2500", "52000"),
    ("4.000-220", "OBRAS E INSTALAÇÕES", "95000", "42000", "20000", "15000", "125000"),
)


def _scale(value: Decimal, factor: str) -> Decimal:
    return (value * Decimal(factor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _adjust_rows(
    rows: tuple[GestorRow, ...],
    factors: PeriodFactors,
) -> tuple[GestorRow, ...]:
    pc_factor, nf_factor, ok_factor, approval_factor, limit_factor = factors
    adjusted: list[GestorRow] = []

    for row in rows:
        adjusted.append(
            create_gestor_row(
                (
                    row.natureza_codigo,
                    row.natureza_descricao,
                    str(_scale(row.pc_aberto, pc_factor)),
                    str(_scale(row.nf_entrada, nf_factor)),
                    str(_scale(row.contingencia_ok, ok_factor)),
                    str(
                        _scale(
                            row.contingencia_em_aprovacao,
                            approval_factor,
                        )
                    ),
                    str(_scale(row.limite_original, limit_factor)),
                )
            )
        )

    return tuple(adjusted)


SEPTEMBER_ROWS = tuple(create_gestor_row(row) for row in SEPTEMBER_BASE_ROWS)
AUGUST_ROWS = _adjust_rows(
    SEPTEMBER_ROWS[:18],
    ("0.82", "0.9", "0.8", "0.75", "0.88"),
)
OCTOBER_ROWS = _adjust_rows(
    SEPTEMBER_ROWS
    + tuple(create_gestor_row(row) for row in OCTOBER_ADDITIONAL_ROWS),
    ("1.12", "1.08", "1.1", "1.2", "1.04"),
)

GESTOR_MOCKS: dict[tuple[int, int], tuple[GestorRow, ...]] = {
    (2025, 8): AUGUST_ROWS,
    (2025, 9): SEPTEMBER_ROWS,
    (2025, 10): OCTOBER_ROWS,
}
