"""Performance dashboard panels net-of-cost (**A-P1-07**)."""

from __future__ import annotations

from dataclasses import dataclass

from sate_adequacy.perf import PerformanceSnapshot


@dataclass(frozen=True)
class PerformancePanel:
    title: str
    ok: bool
    detail: str


def build_performance_panels(snapshot: PerformanceSnapshot) -> list[PerformancePanel]:
    return [
        PerformancePanel(
            title="Net excess (TWR)",
            ok=snapshot.net_excess_twr > 0.0,
            detail=f"{snapshot.net_excess_twr:.2%} vs benchmark {snapshot.benchmark_twr:.2%}",
        ),
        PerformancePanel(
            title="Net Sharpe",
            ok=snapshot.net_sharpe >= 1.2,
            detail=f"{snapshot.net_sharpe:.2f} (A-SIM-03 floor 1.2)",
        ),
        PerformancePanel(
            title="Retirement gate",
            ok=not snapshot.retire_to_cash,
            detail="bootstrap 95% lower bound on excess > 0" if not snapshot.retire_to_cash else "retire to cash",
        ),
    ]
