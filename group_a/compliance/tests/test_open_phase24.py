import os
import sqlite3
import unittest

from sate_control.auth import Session
from sate_control.router import ControlApi
from sate_factlog.log import FactLog
from sate_mt5_bridge import Bridge, MockTerminal

from sate_compliance.broker_ops_wire import gate_for_arm, seed_staging_verification
from sate_compliance.mt5_bat import run_demo_protective_bat
from sate_compliance.phase24_gate import build_phase24_report
from sate_compliance.relay_policy import relay_policy_from_env
from sate_compliance.staging import incomplete_gate

_PASSKEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"


class OpenPhase24Tests(unittest.TestCase):
    def test_gate_from_fact_log_allows_arm(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"compliance-a"}),
            readers=frozenset({"compliance-a", "control-api"}),
        )
        at = "2026-10-23T21:00:00Z"
        seed_staging_verification(log, at=at)
        gate = gate_for_arm(log, as_of=at)
        self.assertFalse(gate.block_reasons())

    def test_router_arm_uses_fact_log_without_staging_flag(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"compliance-a", "control-api"}),
            readers=frozenset({"compliance-a", "control-api", "test"}),
        )
        at = "2026-10-23T21:00:00Z"
        seed_staging_verification(log, at=at)
        api = ControlApi(
            log=log,
            session=Session(principal="owner", group_scope="A"),
            now=at,
        )
        result = api.dispatch(
            "POST",
            "/mode/A/arm",
            {"passkey_assertion": _PASSKEY, "otp": "999999", "as_of": at},
            csrf_token=api.issue_csrf()["csrf_token"],
        )
        self.assertEqual(result["status"], "arming")

    def test_relay_enable_requires_full_policy(self) -> None:
        os.environ["SATE_SEC_RELAY_ENABLED"] = "true"
        try:
            relay = relay_policy_from_env()
            self.assertFalse(relay.sec_ok())
            reasons = incomplete_gate().block_reasons()
            self.assertNotIn("a_dec_08_relay_policy_invalid", reasons)
            gate = gate_for_arm(None, as_of="2026-10-23T21:00:00Z")
            gate_with_relay = type(gate)(
                package=gate.package,
                blockers=gate.blockers,
                sign_off=gate.sign_off,
                tax_memo=gate.tax_memo,
                relay=relay,
                bat_protective_ok=gate.bat_protective_ok,
            )
            self.assertIn("a_dec_08_relay_policy_invalid", gate_with_relay.block_reasons())
        finally:
            os.environ.pop("SATE_SEC_RELAY_ENABLED", None)

    def test_mt5_bat_records_steps_and_persists(self) -> None:
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
        bat = run_demo_protective_bat(Bridge(terminal))
        self.assertTrue(bat.gate_met())
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"compliance-a"}),
            readers=frozenset({"compliance-a"}),
        )
        from sate_compliance.broker_ops_wire import persist_mt5_bat_result

        at = "2026-10-23T21:00:00Z"
        persist_mt5_bat_result(log, bat, at=at)
        from sate_compliance.fact_load import load_broker_state

        state = load_broker_state(log, as_of=at)
        self.assertTrue(state.bat_protective_ok)

    def test_phase24_report_from_seeded_log(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"compliance-a"}),
            readers=frozenset({"compliance-a"}),
        )
        at = "2026-10-23T21:00:00Z"
        seed_staging_verification(log, at=at)
        report = build_phase24_report(log, as_of=at)
        self.assertTrue(report["live_arm_allowed"])
        self.assertFalse(report["operator_written_verification_on_file"])
        os.environ["SATE_BROKER_WRITTEN_VERIFICATION"] = "true"
        report2 = build_phase24_report(log, as_of=at)
        self.assertTrue(report2["phase24_exit_met"])
        os.environ.pop("SATE_BROKER_WRITTEN_VERIFICATION", None)


if __name__ == "__main__":
    unittest.main()
