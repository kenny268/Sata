import sqlite3
import unittest

from sate_factlog.log import FactLog
from sate_mt5_bridge.bridge import Bridge
from sate_mt5_bridge.terminal import MockTerminal

from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.evidence import SimWeekEvidence
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.regime import RegimeFilter
from sate_strategy_a.sim_loop import run_sim_weeks


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


class SimLoopTests(unittest.TestCase):
    def test_four_week_sim_harness(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"strategy-a", "kernel-a"}),
            readers=frozenset({"strategy-a", "kernel-a"}),
        )
        bridge = _bridge()
        engine = StrategyEngine(
            account_mode="SIM",
            rung="SIM",
            kalman=KalmanTickFilter(innovation_threshold_sigma=0.03),
            regime=RegimeFilter(unstable_limit=10),
        )
        base = 1.0850
        price_series = []
        for index in range(200):
            if index % 10 == 0:
                price_series.append(base + 0.0350)
            else:
                price_series.append(base + (index % 3) * 0.0001)
        evidence = run_sim_weeks(
            bridge=bridge,
            engine=engine,
            log=log,
            weeks=4,
            sessions_per_week=5,
            price_series=price_series,
            at="2026-10-23T21:00:00Z",
        )
        self.assertIsInstance(evidence, SimWeekEvidence)
        self.assertTrue(evidence.gate_met(minimum_weeks=4, sessions_per_week=5))
        bridge.close()


if __name__ == "__main__":
    unittest.main()
