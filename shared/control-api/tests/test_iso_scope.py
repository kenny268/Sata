"""Cross-group API denial (**ISO**, **A-IND-02**)."""

from __future__ import annotations

import sqlite3
import unittest

from sate_control.auth import Session
from sate_control.reporting import reject_global_risk_scope, tag_reporting_only
from sate_control.router import ControlApi
from sate_factlog.log import FactLog


class IsoScopeTests(unittest.TestCase):
    def test_b_session_cannot_read_a_state(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            api = ControlApi(
                log=FactLog(
                    conn,
                    writers=frozenset({"control-api"}),
                    readers=frozenset({"control-api"}),
                ),
                session=Session(principal="owner-b", group_scope="B"),
            )
            with self.assertRaises(PermissionError):
                api.dispatch("GET", "/state", {"scope": "A", "mode": "SIM"})
        finally:
            conn.close()

    def test_global_scope_blocked_for_ratify(self) -> None:
        with self.assertRaises(ValueError):
            reject_global_risk_scope("GLOBAL")

    def test_combined_reporting_is_tagged(self) -> None:
        tagged = tag_reporting_only({"combined_equity_display": "100"})
        self.assertTrue(tagged["reporting_only"])
        self.assertIn("not transferable", str(tagged["label"]))


if __name__ == "__main__":
    unittest.main()
