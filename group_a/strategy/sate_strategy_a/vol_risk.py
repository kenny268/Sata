"""Vol-scaled risk **A-SZ-01**."""

from __future__ import annotations

from decimal import Decimal


def vol_scaled_risk_pct(*, base_pct: str, atr: str, baseline_atr: str) -> str:
    base = Decimal(base_pct)
    current = Decimal(atr)
    baseline = Decimal(baseline_atr)
    if baseline <= 0 or current <= 0:
        return str(base)
    scale = min(baseline / current, Decimal(1))
    scaled = base * scale
    return format(scaled.normalize(), "f")
