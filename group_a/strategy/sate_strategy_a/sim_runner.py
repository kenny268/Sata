"""Continuous SIM loop runner (cron / sidecar)."""

from __future__ import annotations

import os
import sqlite3

from sate_adequacy.sim_ops_wire import record_sim_session, sim_ops_writers
from sate_factlog.log import FactLog
from sate_mt5_bridge.bridge import Bridge
from sate_mt5_bridge.terminal import MockTerminal

from sate_strategy_a.config import regime_unstable_limit
from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.regime import RegimeFilter
from sate_strategy_a.sim_loop import run_sim_session


def _fact_log() -> FactLog:
    db_path = os.environ.get("SATE_SIM_OPS_FACTLOG", os.environ.get("SATE_STRATEGY_DB", ":memory:"))
    conn = sqlite3.connect(db_path) if db_path != ":memory:" else sqlite3.connect(":memory:")
    return FactLog(
        conn,
        writers=sim_ops_writers(),
        readers=frozenset(sim_ops_writers()),
    )


def run_continuous_session(*, at: str) -> dict[str, object]:
    log = _fact_log()
    terminal = MockTerminal(
        login="10001",
        server="Exness-MT5Trial",
        mode="SIM",
        bid="1.0850",
        ask="1.0852",
        server_time=at,
        settlement="demo",
        min_lot="1.25",
        lot_step="0.01",
        stops_level="0",
    )
    bridge = Bridge(terminal)
    bridge.connect("10001", "Exness-MT5Trial", {"group": "A", "injected": True}, instrument="EURUSD")
    bridge.poll()
    engine = StrategyEngine(
        account_mode="SIM",
        rung="SIM",
        kalman=KalmanTickFilter(innovation_threshold_sigma=0.03),
        regime=RegimeFilter(unstable_limit=regime_unstable_limit() or 10),
    )
    prices = [1.0850, 1.0850, 1.1200, 1.1200]
    record = run_sim_session(
        bridge=bridge,
        engine=engine,
        log=log,
        session_id=f"runner-{at}",
        prices=prices,
        at=at,
    )
    bridge.close()
    record_sim_session(
        log,
        session_id=record.session_id,
        journal_logged=record.journal_logged,
        order_placed=record.order_placed,
        verdict=record.verdict,
        at=at,
    )
    return {
        "session_id": record.session_id,
        "journal_logged": record.journal_logged,
        "verdict": record.verdict,
        "order_placed": record.order_placed,
    }


def main() -> None:
    at = os.environ.get("SATE_STRATEGY_NOW", "2026-10-23T21:00:00Z")
    result = run_continuous_session(at=at)
    if not result["journal_logged"]:
        raise SystemExit("SIM runner did not journal")
    print("sim runner ok", result["verdict"])


if __name__ == "__main__":
    main()
