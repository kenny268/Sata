"""L1 reverse graduation (**A-LAD-01–03**). The 20% ramp drawdown stays unset."""

from __future__ import annotations

from decimal import Decimal


def floor_band(*, equity: str, floor: str) -> str:
    marked = Decimal(equity)
    base = Decimal(floor)
    if marked < base:
        return "breach"
    if marked <= base * Decimal("1.10"):
        return "warn"
    return "clear"


def manage_only(*, sessions_below_floor: int) -> bool:
    return sessions_below_floor >= 3


def reentry_blocked(*, days_since_breach: int) -> bool:
    return days_since_breach < 14


def live_reentry_allowed(
    *,
    sessions_below_floor: int,
    days_since_breach: int,
    preflight_passed: bool,
) -> bool:
    if manage_only(sessions_below_floor=sessions_below_floor):
        return False
    if reentry_blocked(days_since_breach=days_since_breach):
        return False
    return preflight_passed
