"""Full cost model for backtests **A-EXE-01** (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    spread_pips: float
    commission_per_lot: float
    swap_per_day: float
    slippage_pips: float
    wednesday_triple: bool = True

    def round_trip_cost(self, *, lots: float, pip_value: float, hold_days: int, exit_on_wednesday: bool) -> float:
        spread = self.spread_pips * pip_value * lots
        commission = self.commission_per_lot * lots * 2
        swap_days = hold_days
        if self.wednesday_triple and exit_on_wednesday:
            swap_days += 2
        swap = self.swap_per_day * lots * swap_days
        slippage = self.slippage_pips * pip_value * lots * 2
        return spread + commission + swap + slippage


EURUSD_COSTS = CostModel(spread_pips=0.1, commission_per_lot=3.5, swap_per_day=-0.2, slippage_pips=0.5)
