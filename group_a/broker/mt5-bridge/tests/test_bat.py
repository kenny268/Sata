import unittest

from sate_mt5_bridge import Bridge, MockTerminal
from sate_mt5_bridge.bat import run_protective_order_bat


class BatModuleTests(unittest.TestCase):
    def test_run_protective_order_bat_steps(self) -> None:
        terminal = MockTerminal(
            login="10001",
            server="Exness-MT5Trial",
            mode="SIM",
            bid="1.0850",
            ask="1.0852",
            server_time="2026-10-22T21:00:00Z",
            min_lot="1.25",
            lot_step="0.25",
            stops_level="8",
        )
        steps = run_protective_order_bat(
            Bridge(terminal),
            login="10001",
            server="Exness-MT5Trial",
            grant={"group": "A", "injected": True},
            instrument="EURUSD",
            stop="1.0700",
        )
        self.assertEqual(
            steps,
            [
                "place_market_with_stop",
                "broker_ack_stop_attached",
                "reject_entry_without_stop",
            ],
        )


if __name__ == "__main__":
    unittest.main()
