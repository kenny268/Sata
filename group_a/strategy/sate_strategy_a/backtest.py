"""Vectorised backtest with costs **§5.5**."""

from __future__ import annotations

from dataclasses import dataclass

from sate_strategy_a.costs import CostModel
from sate_strategy_a.kalman import KalmanTickFilter


@dataclass
class BacktestResult:
    trades: int
    net_pnl: float
    abstains: int


def run_vectorised_backtest(prices: list[float], *, costs: CostModel, pip_value: float = 10.0) -> BacktestResult:
    kalman = KalmanTickFilter()
    trades = 0
    pnl = 0.0
    abstains = 0
    position = 0
    entry = 0.0
    for index, price in enumerate(prices):
        signal = kalman.update(price)
        if not signal.triggered:
            abstains += 1
            continue
        direction = signal.direction
        if position == 0 and direction != 0:
            position = direction
            entry = price
            trades += 1
        elif position != 0 and direction == -position:
            gross = (price - entry) * position * pip_value
            cost = costs.round_trip_cost(
                lots=1.0,
                pip_value=pip_value,
                hold_days=max(1, index // 24),
                exit_on_wednesday=index % 7 == 3,
            )
            pnl += gross - cost
            position = 0
    return BacktestResult(trades=trades, net_pnl=pnl, abstains=abstains)
