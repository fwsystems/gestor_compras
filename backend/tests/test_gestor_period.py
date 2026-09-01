from datetime import date
from decimal import Decimal

from app.services.gestor_period import GestorInterval, business_days, limit_factor, proportional_limit


def test_month_business_days_and_weekly_limit_proportion() -> None:
    august = GestorInterval(date(2026, 8, 1), date(2026, 8, 31))
    week = GestorInterval(date(2026, 8, 24), date(2026, 8, 30))
    assert business_days(august) == 21
    assert business_days(week) == 5
    assert limit_factor(week, 2026, 8) == Decimal(5) / Decimal(21)
    assert proportional_limit(Decimal("2100"), limit_factor(week, 2026, 8)) == Decimal("500.00")


def test_daily_business_day_and_weekend_limit() -> None:
    assert limit_factor(GestorInterval(date(2026, 8, 31), date(2026, 8, 31)), 2026, 8) == Decimal(1) / Decimal(21)
    assert proportional_limit(Decimal("2100"), limit_factor(GestorInterval(date(2026, 8, 30), date(2026, 8, 30)), 2026, 8)) == Decimal("0.00")


def test_cross_month_week_counts_only_days_inside_selected_month() -> None:
    effective_august = GestorInterval(date(2026, 8, 31), date(2026, 8, 31))
    assert business_days(effective_august) == 1
    assert proportional_limit(Decimal("2100"), limit_factor(effective_august, 2026, 8)) == Decimal("100.00")
