from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class GestorInterval:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("fim must not be earlier than inicio.")


def intersect_month(interval: GestorInterval, ano: int, mes: int) -> GestorInterval:
    month_start = date(ano, mes, 1)
    month_end = date(ano, mes, monthrange(ano, mes)[1])
    return GestorInterval(max(interval.start, month_start), min(interval.end, month_end))


def business_days(interval: GestorInterval) -> int:
    return sum(
        1
        for offset in range((interval.end - interval.start).days + 1)
        if interval.start.fromordinal(interval.start.toordinal() + offset).weekday() < 5
    )


def limit_factor(interval: GestorInterval | None, ano: int, mes: int) -> Decimal:
    if interval is None:
        return Decimal("1")
    month = GestorInterval(date(ano, mes, 1), date(ano, mes, monthrange(ano, mes)[1]))
    return Decimal(business_days(intersect_month(interval, ano, mes))) / Decimal(business_days(month))


def proportional_limit(value: Decimal, factor: Decimal) -> Decimal:
    return (value * factor).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
