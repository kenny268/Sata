"""Stored-fact inputs for reproducible adequacy (**A-P1-01**)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimAdequacyEvidence:
    """Snapshot assembled from fact log / ops exports at report time."""

    generated_at: str
    sim_months_continuous: float
    reconciliation_clean_rate: float
    net_sharpe_after_costs: float
    monthly_returns_net: tuple[float, ...]
    trade_count: int
    bootstrap_excess_lower_bound: float | None
    l2_plus_unresolved_last_60d: int
    parameter_changes_last_3_months: int
    untradeable_session_rate: float
    strategy_version_frozen: str
    benchmark_return_twr: float = 0.0
    portfolio_return_twr: float = 0.0
