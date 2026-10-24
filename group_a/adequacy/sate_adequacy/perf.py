"""Net-of-cost performance helpers (**A-PERF-01–02**, **A-P1-07**)."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceSnapshot:
    portfolio_twr: float
    benchmark_twr: float
    net_excess_twr: float
    net_sharpe: float
    retire_to_cash: bool


def time_weighted_return(period_returns: list[float]) -> float:
    acc = 1.0
    for value in period_returns:
        acc *= 1.0 + value
    return acc - 1.0


def sharpe_ratio(period_returns: list[float], *, periods_per_year: int = 12) -> float:
    if len(period_returns) < 2:
        return 0.0
    mean = sum(period_returns) / len(period_returns)
    var = sum((value - mean) ** 2 for value in period_returns) / (len(period_returns) - 1)
    if var <= 0.0:
        return 0.0
    std = var**0.5
    return (mean / std) * (periods_per_year**0.5)


def bootstrap_excess_lower_bound(
    portfolio: list[float],
    benchmark: list[float],
    *,
    samples: int = 1000,
    seed: int = 42,
) -> float:
    if len(portfolio) != len(benchmark) or len(portfolio) < 2:
        return 0.0
    excess = [p - b for p, b in zip(portfolio, benchmark, strict=True)]
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(samples):
        draw = [rng.choice(excess) for _ in range(len(excess))]
        draws.append(sum(draw))
    draws.sort()
    index = int(0.05 * (len(draws) - 1))
    return draws[index]


def performance_snapshot(
    *,
    portfolio_monthly: list[float],
    benchmark_monthly: list[float],
    min_sample_months: int = 12,
) -> PerformanceSnapshot:
    portfolio_twr = time_weighted_return(portfolio_monthly)
    benchmark_twr = time_weighted_return(benchmark_monthly)
    net_excess = portfolio_twr - benchmark_twr
    net_sharpe = sharpe_ratio(portfolio_monthly)
    lower = bootstrap_excess_lower_bound(portfolio_monthly, benchmark_monthly)
    retire = len(portfolio_monthly) >= min_sample_months and lower <= 0.0
    return PerformanceSnapshot(
        portfolio_twr=portfolio_twr,
        benchmark_twr=benchmark_twr,
        net_excess_twr=net_excess,
        net_sharpe=net_sharpe,
        retire_to_cash=retire,
    )
