"""Phase 23 calendar gate report (**§4.5**)."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_adequacy.evidence import SimAdequacyEvidence
from sate_adequacy.evidence_ledger import period_start_from_log, rollup_from_log
from sate_adequacy.fact_extract import evidence_from_fact_log
from sate_adequacy.kalman_clock import (
    kalman_frozen_months_from_log,
    parameter_changes_last_3_months,
)
from sate_adequacy.ops_drills import SimOpsDrillSuite, drills_from_log
from sate_adequacy.report import build_adequacy_report
from sate_adequacy.sim_clock import SIM_MONTHS_REQUIRED, SimPeriod
from sate_adequacy.wall_clock import operator_wall_clock_elapsed

READER = "sim-ops-a"


def evidence_with_ledger(
    log: FactLog,
    *,
    as_of: str,
    period: SimPeriod,
) -> SimAdequacyEvidence:
    roll = rollup_from_log(log, reader_id=READER, as_of=as_of)
    frozen_months = kalman_frozen_months_from_log(log, reader_id=READER, as_of=as_of)
    base = evidence_from_fact_log(
        log,
        reader_id=READER,
        as_of=as_of,
        sim_months_continuous=period.months_elapsed,
    )
    return SimAdequacyEvidence(
        generated_at=base.generated_at,
        sim_months_continuous=period.months_elapsed,
        reconciliation_clean_rate=max(base.reconciliation_clean_rate, roll.reconciliation_clean_rate),
        net_sharpe_after_costs=base.net_sharpe_after_costs,
        monthly_returns_net=base.monthly_returns_net,
        trade_count=max(base.trade_count, roll.trade_count),
        bootstrap_excess_lower_bound=base.bootstrap_excess_lower_bound,
        l2_plus_unresolved_last_60d=roll.l2_plus_events,
        parameter_changes_last_3_months=parameter_changes_last_3_months(frozen_months),
        untradeable_session_rate=min(base.untradeable_session_rate, roll.untradeable_session_rate),
        strategy_version_frozen=base.strategy_version_frozen,
        benchmark_return_twr=base.benchmark_return_twr,
        portfolio_return_twr=base.portfolio_return_twr,
    )


def build_phase23_report(
    log: FactLog,
    *,
    as_of: str,
    period: SimPeriod,
    drills: SimOpsDrillSuite | None = None,
) -> dict[str, object]:
    drill_state = drills or drills_from_log(log, reader_id=READER, as_of=as_of)
    roll = rollup_from_log(log, reader_id=READER, as_of=as_of)
    evidence = evidence_with_ledger(log, as_of=as_of, period=period)
    adequacy = build_adequacy_report(evidence)
    sim06 = next(item for item in adequacy["criteria"] if item["id"] == "A-SIM-06")
    exit_met = (
        period.calendar_gate_met
        and drill_state.gate_met
        and sim06["status"] == "pass"
        and adequacy["software_ready"]
    )
    return {
        "phase": 23,
        "as_of": as_of,
        "sim_period": {
            "started_at": period.started_at,
            "months_elapsed": round(period.months_elapsed, 2),
            "months_required": SIM_MONTHS_REQUIRED,
            "calendar_gate_met": period.calendar_gate_met,
        },
        "ops_drills": {
            "gate_met": drill_state.gate_met,
            "completed": [item.drill_id for item in drill_state.results if item.ok],
        },
        "adequacy_report": adequacy,
        "ledger_rollup": {
            "days": roll.days,
            "reconciliation_clean_rate": round(roll.reconciliation_clean_rate, 4),
            "trade_count": roll.trade_count,
            "untradeable_session_rate": round(roll.untradeable_session_rate, 4),
            "l2_plus_events": roll.l2_plus_events,
        },
        "operator_wall_clock_elapsed": operator_wall_clock_elapsed(period=period),
        "phase23_exit_met": exit_met,
    }


def resolve_period(log: FactLog, *, as_of: str, env_start: str | None) -> SimPeriod:
    start = env_start or period_start_from_log(log, reader_id=READER, as_of=as_of)
    if not start:
        raise ValueError("SIM period start missing (fact log or SATE_SIM_PERIOD_START)")
    return SimPeriod(started_at=start, as_of=as_of)
