"""Compose smoke: one SIM session with journal + intent schema."""

from __future__ import annotations

import sqlite3

from sate_factlog.log import FactLog
from sate_mt5_bridge.bridge import Bridge
from sate_mt5_bridge.terminal import MockTerminal

from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.regime import RegimeFilter
from sate_strategy_a.sim_loop import run_sim_session


def main() -> None:
    log = FactLog(
        sqlite3.connect(":memory:"),
        writers=frozenset({"strategy-a", "kernel-a"}),
        readers=frozenset({"strategy-a", "kernel-a"}),
    )
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
    engine = StrategyEngine(
        account_mode="SIM",
        rung="SIM",
        kalman=KalmanTickFilter(),
        regime=RegimeFilter(unstable_limit=5),
    )
    prices = [1.0850 + (index * 0.0003) for index in range(20)]
    record = run_sim_session(
        bridge=bridge,
        engine=engine,
        log=log,
        session_id="bootstrap-1",
        prices=prices,
        at="2026-10-23T21:00:00Z",
    )
    if not record.journal_logged:
        raise SystemExit("journal missing")
    bridge.close()
    print("strategy-a ok")


if __name__ == "__main__":
    main()
