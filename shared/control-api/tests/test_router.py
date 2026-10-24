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
            },
            csrf_token=self._csrf(),
        )
        self.assertEqual(live["mode"], "LIVE-L1")

    def test_risk_increasing_paths_require_passkey(self) -> None:
        with self.assertRaises((PasskeyRequired, ValueError)):
            self.api.dispatch("POST", "/resume/A", {}, csrf_token=self._csrf())


if __name__ == "__main__":
    unittest.main()
