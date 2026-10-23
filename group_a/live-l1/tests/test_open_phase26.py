import sqlite3
import unittest

from sate_control.auth import Session
from sate_control.router import ControlApi
from sate_factlog.log import FactLog
from sate_live_readiness.live_ops_wire import seed_staging_live_readiness
from sate_mt5_bridge import Bridge, MockTerminal

from sate_live_l1.live_session import run_first_live_session
from sate_live_l1.phase26_gate import build_phase26_report

_PASSKEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"


class OpenPhase26Tests(unittest.TestCase):
    def test_c4_confirm_and_first_session(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset(
                {
                    "control-api",
                    "live-l1-a",
                    "live-readiness-a",
                    "compliance-a",
                    "sim-ops-a",
                    "strategy-a",
                    "kernel-a",
                }
            ),
            readers=frozenset({"control-api", "live-l1-a", "test", "sim-ops-a"}),
        )
        at = "2026-10-23T22:00:00Z"
        seed_staging_live_readiness(log, at=at)
        api = ControlApi(log=log, session=Session(principal="owner", group_scope="A"), now=at)
        token = api.issue_csrf()["csrf_token"]
        api.dispatch(
            "POST",
            "/mode/A/arm",
            {"passkey_assertion": _PASSKEY, "otp": "999999", "as_of": at},
            csrf_token=token,
        )
        live = api.dispatch(
            "POST",
            "/mode/A/confirm",
            {
                "passkey_assertion": _PASSKEY,
                "code": "999999",
                "live_l1_staging": True,
                "flat_confirmed": True,
                "first_session_id": "live-l1-test-1",
            },
            csrf_token=api.issue_csrf()["csrf_token"],
        )
        self.assertEqual(live["mode"], "LIVE-L1")
        self.assertEqual(live["ramp_factor"], "0.25")
        terminal = MockTerminal(
            login="10001",
            server="Exness-MT5Trial",
            mode="SIM",
            bid="1.0850",
            ask="1.0852",
            server_time=at,
            min_lot="1.25",
            lot_step="0.01",
            stops_level="0",
        )
        bridge = Bridge(terminal)
        bridge.connect("10001", "Exness-MT5Trial", {"group": "A", "injected": True}, instrument="EURUSD")
        session = run_first_live_session(
            bridge=bridge,
            log=log,
            at=at,
            session_id="live-l1-test-1",
        )
        bridge.close()
        self.assertTrue(session["stops_verified"])
        report = build_phase26_report(log, as_of=at)
        self.assertTrue(report["phase26_exit_met"])


if __name__ == "__main__":
    unittest.main()
