"""Phase 17 control-api routes and fact-log audit."""

from __future__ import annotations

import sqlite3
import unittest

from sate_control.auth import Session
from sate_control.passkey import PasskeyRequired
from sate_control.router import ControlApi
from sate_factlog.log import FactLog

_PASSKEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"


class ControlApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._conn = sqlite3.connect(":memory:")
        self.log = FactLog(
            self._conn,
            writers=frozenset({"control-api", "live-l1-a"}),
            readers=frozenset({"control-api", "compliance-a", "live-l1-a", "test"}),
        )
        self.api = ControlApi(
            log=self.log,
            session=Session(principal="owner", group_scope="A"),
        )

    def tearDown(self) -> None:
        self._conn.close()

    def _csrf(self) -> str:
        return self.api.issue_csrf()["csrf_token"]

    def test_sim_operations_without_telegram_and_audit_trail(self) -> None:
        state = self.api.dispatch("GET", "/state", {"scope": "A", "mode": "SIM"})
        self.assertEqual(state["mode_badge"]["tag"], "A-SIM")
        token = self._csrf()
        self.api.dispatch(
            "POST",
            "/checkin",
            {"channel": "web_passkey", "passkey_assertion": _PASSKEY},
            csrf_token=token,
        )
        self.api.dispatch(
            "POST",
            "/mode/A/sim",
            {"passkey_assertion": _PASSKEY},
            csrf_token=self._csrf(),
        )
        rows = self.log.poll(after_seq=0, group_scope="A", reader_id="test")
        actions = [row.payload["action"] for row in rows if row.event_type == "owner_action"]
        self.assertIn("checkin", actions)
        self.assertIn("mode_sim", actions)

    def test_arm_preflight_failure_returns_reason_codes(self) -> None:
        result = self.api.dispatch(
            "POST",
            "/mode/A/arm",
            {
                "passkey_assertion": _PASSKEY,
                "clean_recon": False,
                "mode": "SIM",
            },
            csrf_token=self._csrf(),
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("recon_not_clean", result["reasons"])

    def test_confirm_requires_passkey_and_otp(self) -> None:
        self.api.dispatch(
            "POST",
            "/mode/A/arm",
            {
                "passkey_assertion": _PASSKEY,
                "otp": "999999",
                "broker_verification_complete": True,
                "live_readiness_complete": True,
            },
            csrf_token=self._csrf(),
        )
        live = self.api.dispatch(
            "POST",
            "/mode/A/confirm",
            {
                "passkey_assertion": _PASSKEY,
                "code": "999999",
                "live_l1_staging": True,
                "flat_confirmed": True,
            },
            csrf_token=self._csrf(),
        )
        self.assertEqual(live["mode"], "LIVE-L1")

    def test_risk_increasing_paths_require_passkey(self) -> None:
        with self.assertRaises((PasskeyRequired, ValueError)):
            self.api.dispatch("POST", "/resume/A", {}, csrf_token=self._csrf())

    def test_state_ignores_a_client_supplied_mode(self) -> None:
        lied = self.api.dispatch("GET", "/state", {"scope": "A", "mode": "LIVE-L1"})
        self.assertEqual(lied["mode"], "SIM")
        self.assertEqual(lied["mode_badge"]["tag"], "A-SIM")
        self.api.dispatch(
            "POST",
            "/kill",
            {"scope": "A", "kill_level": "K1", "channel": "web"},
            csrf_token=self._csrf(),
        )
        state = self.api.dispatch("GET", "/state", {"scope": "A", "kill_state": "K3"})
        self.assertEqual(state["kill_state"], "K1")
        self.assertEqual(state["capital"]["equity"], "unknown")
        self.assertIn("capital_unloaded", state["attention"])
        self.assertIn("session_ttl_unset", state["attention"])
        self.assertIn("kill_K1", state["attention"])
        self.assertFalse(state["risk"]["partial_halt"])
        self.assertEqual(state["risk"]["halt_command"], "HALT_REQUESTED")
        self.api.note_capital_book({"equity": "500", "withdrawable": "100", "reserved": "20"})
        self.api.note_reporting_equity("B", "200.50")
        reported = self.api.dispatch(
            "GET",
            "/reporting/combined",
            {"a_equity": "1", "b_equity": "1"},
        )
        self.assertEqual(reported["a_equity"], "500")
        self.assertEqual(reported["b_equity"], "200.50")
        self.assertEqual(reported["combined_equity_display"], "700.5")
        self.assertTrue(reported["reporting_only"])
        self.api.note_reporting_equity("B", "nope")
        broken = self.api.dispatch("GET", "/reporting/combined", {})
        self.assertEqual(broken["combined_equity_display"], "unknown")
        constitution = self.api.dispatch("GET", "/constitution", {"scope": "A"})
        self.assertEqual(constitution["time_lock"], "unset")
        self.assertIsNone(constitution["active_version"])
        resumed = self.api.dispatch(
            "POST",
            "/resume/A",
            {"passkey_assertion": _PASSKEY},
            csrf_token=self._csrf(),
        )
        self.assertEqual(resumed["status"], "resume_blocked")
        self.assertIn("fact_log", resumed["steps"])
        self.assertIn("cool_off_unset", resumed["steps"])
        self.api.session = Session(
            principal="owner",
            group_scope="A",
            expires_at="2026-10-22T00:00:00Z",
        )
        with self.assertRaises(PermissionError):
            self.api.dispatch("GET", "/state", {"scope": "A"})

    def test_k3_seals_and_constitution_hours_stay_unset(self) -> None:
        self.api.dispatch(
            "POST",
            "/kill",
            {"scope": "A", "kill_level": "K3", "channel": "web"},
            csrf_token=self._csrf(),
        )
        state = self.api.dispatch("GET", "/state", {"scope": "A"})
        self.assertTrue(state["risk"]["trading_revoked"])
        self.assertEqual(state["risk"]["halt_command"], "HALT_REQUESTED")
        with self.assertRaises(ValueError):
            self.api.dispatch(
                "POST",
                "/kill",
                {"scope": "A", "kill_level": "K1", "channel": "web"},
                csrf_token=self._csrf(),
            )
        self.api.note_constitution(
            {
                "read_only": True,
                "active_version": 1,
                "pending": [{"version": 2, "lock_state": "awaiting_owner_hours", "reason": "limits"}],
            }
        )
        view = self.api.dispatch("GET", "/constitution", {"scope": "A"})
        self.assertEqual(view["active_version"], 1)
        self.assertEqual(view["time_lock"], "unset")
        self.assertTrue(view["read_only"])

    def test_resume_stays_blocked_until_the_owner_sets_a_cool_off(self) -> None:
        blocked = self.api.dispatch(
            "POST",
            "/resume/A",
            {
                "passkey_assertion": _PASSKEY,
                "kill_level": "K1",
                "fact_logged": True,
                "recon_clean": True,
                "preflight_passed": True,
                "broker_positions": [],
                "system_positions": [],
            },
            csrf_token=self._csrf(),
        )
        self.assertEqual(blocked["status"], "resume_blocked")
        self.assertIn("cool_off_unset", blocked["steps"])

    def test_dashboard_reads_and_kernel_ack(self) -> None:
        empty = self.api.dispatch("GET", "/positions", {"scope": "A"})
        self.assertFalse(empty["loaded"])
        self.api.note_positions(
            [{"instrument": "EURUSD", "quantity": "1", "stop": "1.0800", "slippage": "0.00001"}]
        )
        self.api.note_performance("SIM", {"net_of_cost": "0.04", "drawdown": "0.01"})
        self.api.note_risk(exposure="100", margin="25", distance_to_limits="unknown")
        self.api.note_treasury(
            {"cash_floor": "50", "reimbursement_owed": "10", "cases": [], "withdrawals": []}
        )
        positions = self.api.dispatch("GET", "/positions", {"scope": "A"})
        self.assertEqual(positions["positions"][0]["instrument"], "EURUSD")
        performance = self.api.dispatch("GET", "/performance", {"scope": "A"})
        self.assertEqual(performance["books"]["SIM"]["net_of_cost"], "0.04")
        self.assertEqual(performance["books"]["LIVE"]["net_of_cost"], "unknown")
        self.assertTrue(performance["books_stay_separate"])
        eligibility = self.api.dispatch("GET", "/eligibility", {"scope": "A"})
        self.assertIn("live_final_gate", eligibility["reason_codes"])
        self.assertFalse(eligibility["final_live_gate"])
        killed = self.api.dispatch(
            "POST",
            "/kill",
            {"scope": "A", "kill_level": "K1", "channel": "web"},
            csrf_token=self._csrf(),
        )
        self.assertEqual(killed["halt_state"], "HALT_REQUESTED")
        journal = self.api.dispatch("GET", "/journal", {"scope": "A"})
        self.assertTrue(journal["why_from_log_only"])
        self.assertIn("K1", journal["entries"][-1]["why"])
        confirmed = self.api.ack_kernel(str(killed["command_id"]))
        self.assertEqual(confirmed, "HALT_CONFIRMED_A")
        state = self.api.dispatch("GET", "/state", {"scope": "A"})
        self.assertEqual(state["risk"]["halt_command"], "HALT_CONFIRMED_A")
        self.assertEqual(state["risk"]["exposure"], "100")
        self.assertEqual(state["risk"]["margin"], "25")
        treasury = self.api.dispatch("GET", "/treasury", {"scope": "A"})
        self.assertEqual(treasury["cash_floor"], "50")
        self.assertEqual(treasury["reimbursement_owed"], "10")
        health = self.api.dispatch("GET", "/health", {"scope": "A"})
        self.assertEqual(health["hash_chain"], "intact")
        self.assertGreater(health["replay_events"], 0)


if __name__ == "__main__":
    unittest.main()
