import sqlite3
import unittest

from sate_cognitive.fixtures import generate_keypair, signed_signal
from sate_cognitive.shadow import ShadowAccumulator
from sate_factlog.log import FactLog
from sate_mt5_bridge.bridge import Bridge
from sate_mt5_bridge.terminal import MockTerminal

from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.regime import RegimeFilter
from sate_strategy_a.sim_cognitive import SimCognitiveShadow
from sate_strategy_a.sim_loop import run_sim_session


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


class SimShadowTests(unittest.TestCase):
    def test_sim_session_records_shadow_without_trading_advisory(self) -> None:
        private, public = generate_keypair()
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"strategy-a", "kernel-a", "cognitive-a"}),
            readers=frozenset({"strategy-a", "cognitive-a"}),
        )
        acc = ShadowAccumulator(week="2026-W43")
        shadow = SimCognitiveShadow(public_key=public, week="2026-W43", accumulator=acc, log=log)
        signal = signed_signal(private, signal_id="sim-1", q=0.2)
        bridge = _bridge()
        engine = StrategyEngine(
            account_mode="SIM",
            rung="SIM",
            kalman=KalmanTickFilter(innovation_threshold_sigma=0.03),
            regime=RegimeFilter(unstable_limit=10),
        )
        prices = [1.0850] + [1.1200] * 11
        run_sim_session(
            bridge=bridge,
            engine=engine,
            log=log,
            session_id="shadow-1",
            prices=prices,
            at="2026-10-23T12:00:00Z",
            cognitive_shadow=shadow,
            session_signal=signal,
        )
        run_sim_session(
            bridge=bridge,
            engine=engine,
            log=log,
            session_id="shadow-2",
            prices=[1.1200] + [1.0850] * 11,
            at="2026-10-23T12:00:00Z",
            cognitive_shadow=shadow,
            session_signal=signed_signal(private, signal_id="sim-2", q=-0.2),
        )
        bridge.close()
        self.assertEqual(acc.ingested, 2)
        report = acc.weekly_report()
        self.assertIsNotNone(report.rank_corr_vs_baseline)
        self.assertEqual(report.pnl_delta_vs_zero_baseline, 0.0)
        rows = log.poll(after_seq=0, group_scope="A", reader_id="cognitive-a")
        kinds = {row.payload.get("kind") for row in rows}
        self.assertIn("ingest", kinds)


if __name__ == "__main__":
    unittest.main()
