"""Four-week automated demo marathon (**Phase 20** exit orchestrator)."""

from __future__ import annotations

import sqlite3

from sate_factlog.log import FactLog
from sate_mt5_bridge.bridge import Bridge
from sate_mt5_bridge.terminal import MockTerminal

from sate_strategy_a.config import regime_unstable_limit
from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.evidence import SimWeekEvidence
from sate_strategy_a.journal_audit import journal_completeness_for_sessions
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.kalman_evidence import record_kalman_frozen
from sate_strategy_a.marathon_shadow import build_marathon_shadow, finalize_marathon_shadow
from sate_strategy_a.regime import RegimeFilter
from sate_strategy_a.sim_loop import run_sim_weeks


def _price_series(*, points: int = 200) -> list[float]:
    base = 1.0850
    series: list[float] = []
    for index in range(points):
        if index % 10 == 0:
            series.append(base + 0.0350)
        else:
            series.append(base + (index % 3) * 0.0001)
    return series


def _bridge() -> Bridge:
    terminal = MockTerminal(
        login="10001",
        server="Exness-MT5Trial",
        mode="SIM",
        bid="1.0850",
        ask="1.0852",
        server_time="2026-10-23T21:00:00Z",
        settlement="demo",
        min_lot="1.25",
        lot_step="0.01",
        stops_level="0",
    )
    bridge = Bridge(terminal)
    bridge.connect("10001", "Exness-MT5Trial", {"group": "A", "injected": True}, instrument="EURUSD")
    bridge.poll()
    return bridge


def run_demo_marathon(
    *,
    weeks: int = 4,
    sessions_per_week: int = 5,
    at: str,
    log: FactLog | None = None,
) -> SimWeekEvidence:
    fact = log or FactLog(
        sqlite3.connect(":memory:"),
        writers=frozenset({"strategy-a", "kernel-a", "cognitive-a"}),
        readers=frozenset({"strategy-a", "kernel-a", "cognitive-a"}),
    )
    total_sessions = weeks * sessions_per_week
    shadow, session_signals = build_marathon_shadow(week="2026-W43", sessions=total_sessions)
    shadow.log = fact
    bridge = _bridge()
    engine = StrategyEngine(
        account_mode="SIM",
        rung="SIM",
        kalman=KalmanTickFilter(innovation_threshold_sigma=0.03),
        regime=RegimeFilter(unstable_limit=regime_unstable_limit() or 10),
    )
    evidence = run_sim_weeks(
        bridge=bridge,
        engine=engine,
        log=fact,
        weeks=weeks,
        sessions_per_week=sessions_per_week,
        price_series=_price_series(),
        at=at,
        cognitive_shadow=shadow,
        session_signals=session_signals,
    )
    bridge.close()
    finalize_marathon_shadow(shadow, at=at, log=fact)
    if not evidence.gate_met(minimum_weeks=weeks, sessions_per_week=sessions_per_week):
        raise RuntimeError("demo marathon gate not met")
    session_ids = [
        session.session_id for week in evidence.weeks for session in week
    ]
    completeness = journal_completeness_for_sessions(fact, session_ids=session_ids, reader_id="strategy-a")
    if completeness < 1.0:
        raise RuntimeError("journal completeness below 100%")
    record_kalman_frozen(fact, at=at)
    fact.append(
        event_id=f"demo-marathon-{at}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="demo-marathon",
        writer_id="strategy-a",
        payload={
            "weeks": weeks,
            "sessions_per_week": sessions_per_week,
            "journal_completeness": completeness,
            "channel": "demo_bridge",
        },
    )
    return evidence


def main() -> None:
    run_demo_marathon(at="2026-10-23T21:00:00Z")
    print("demo marathon ok")


if __name__ == "__main__":
    main()
