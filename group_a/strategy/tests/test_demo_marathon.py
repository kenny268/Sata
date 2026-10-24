import sqlite3
import unittest

from sate_factlog.log import FactLog

from sate_strategy_a.demo_marathon import run_demo_marathon
from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.intent import build_intent
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.regime import RegimeFilter


class DemoMarathonTests(unittest.TestCase):
    def test_four_week_marathon_meets_exit_gate(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"strategy-a", "kernel-a", "cognitive-a"}),
            readers=frozenset({"strategy-a", "kernel-a", "cognitive-a"}),
        )
        evidence = run_demo_marathon(weeks=4, sessions_per_week=5, at="2026-10-23T21:00:00Z", log=log)
        self.assertTrue(evidence.gate_met(minimum_weeks=4, sessions_per_week=5))
        rows = log.poll(after_seq=0, group_scope="A", reader_id="strategy-a")
        marathon = [
            row for row in rows if row.event_type == "deployment" and row.payload.get("channel") == "demo_bridge"
        ]
        self.assertEqual(len(marathon), 1)
        self.assertEqual(marathon[0].payload.get("journal_completeness"), 1.0)

    def test_live_l1_mode_agnostic_intent(self) -> None:
        engine = StrategyEngine(
            account_mode="LIVE",
            rung="LIVE-L1",
            kalman=KalmanTickFilter(innovation_threshold_sigma=2.5),
            regime=RegimeFilter(unstable_limit=3),
        )
        self.assertEqual(engine.account_mode, "LIVE")
        intent = build_intent(
            intent_id="live-l1-1",
            account_mode="LIVE",
            instrument="EURUSD",
            side="BUY",
            quantity="1.25",
            protective_stop="1.0700",
            strategy_id=engine.strategy_id,
            created_at="2026-10-23T21:00:00Z",
        )
        self.assertEqual(intent["account_mode"], "LIVE")


if __name__ == "__main__":
    unittest.main()
