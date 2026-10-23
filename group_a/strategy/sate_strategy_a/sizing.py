"""Risk-budget sizing **A-SZ-01–04**."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal


@dataclass(frozen=True)
class SizeResult:
    quantity: str
    rejected: bool
    reason: str = ""


def _d(text: str) -> Decimal:
    return Decimal(text)


def size_position(
    *,
    capital_base: str,
    max_risk_pct: str,
    vol_scaled_risk: str,
    ramp_factor: str,
    stop_distance: str,
    value_per_unit: str,
    lot_step: str,
    min_lot: str,
    notional_cap_size: str,
    leverage_cap_size: str,
    kelly_ceiling: str | None = None,
) -> SizeResult:
    cap = min(_d(capital_base), _d(capital_base))
    risk_pct = min(_d(max_risk_pct), _d(vol_scaled_risk))
    budget = cap * risk_pct / Decimal(100) * _d(ramp_factor)
    if kelly_ceiling is not None:
        budget = min(budget, _d(kelly_ceiling))
    stop = _d(stop_distance)
    vpu = _d(value_per_unit)
    if stop <= 0 or vpu <= 0:
        return SizeResult(quantity="0", rejected=True, reason="invalid_stop_or_vpu")
    raw = budget / (stop * vpu)
    capped = min(raw, _d(notional_cap_size), _d(leverage_cap_size))
    step = _d(lot_step)
    if step <= 0:
        return SizeResult(quantity="0", rejected=True, reason="invalid_lot_step")
    floored = (capped / step).to_integral_value(rounding=ROUND_DOWN) * step
    min_l = _d(min_lot)
    if floored < min_l:
        return SizeResult(quantity="0", rejected=True, reason="untradeable_at_this_capital")
    risk_at_size = floored * stop * vpu
    if risk_at_size > budget:
        return SizeResult(quantity="0", rejected=True, reason="untradeable_at_this_capital")
    qty = format(floored, "f")
    if "." in qty:
        qty = qty.rstrip("0").rstrip(".")
    return SizeResult(quantity=qty or "0", rejected=False)
