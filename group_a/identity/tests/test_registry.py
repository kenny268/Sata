import sqlite3
import unittest

from sate_identity.errors import IsolationError
from sate_identity.fingerprint import parse_fingerprint
from sate_identity.registry import IdentityRegistry


def _registry() -> IdentityRegistry:
    return IdentityRegistry(sqlite3.connect(":memory:"))


class FingerprintTests(unittest.TestCase):
    def test_login_and_server_are_required(self) -> None:
        with self.assertRaises(IsolationError):
            parse_fingerprint("  ", "Exness-MT5")
        with self.assertRaises(IsolationError):
            parse_fingerprint("1001", "Exness MT5")

    def test_match_compares_login_and_server(self) -> None:
        left = parse_fingerprint("1001", "Exness-MT5")
        right = parse_fingerprint("1001", "Exness-MT5")
        other = parse_fingerprint("1002", "Exness-MT5")
        self.assertTrue(left.matches(right))
        self.assertFalse(left.matches(other))


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _registry()
        self.registry.register(
            profile_id="A-SIM",
            broker_id="exness",
            account_login="1001",
            server="Exness-MT5",
            recorded_at="2026-10-21T00:00:00Z",
        )

    def test_history_is_append_only(self) -> None:
        self.registry.change_fingerprint(
            profile_id="A-SIM",
            account_login="1002",
            server="Exness-MT5",
            recorded_at="2026-10-22T00:00:00Z",
        )
        history = self.registry.history("A-SIM")
        self.assertEqual([row["account_login"] for row in history], ["1001", "1002"])
        self.assertEqual(self.registry.current("A-SIM")["account_login"], "1002")
        with self.assertRaises(sqlite3.IntegrityError):
            self.registry._conn.execute("DELETE FROM fingerprint_history")

    def test_observe_reports_mismatch_without_mutating(self) -> None:
        self.assertTrue(self.registry.observe("A-SIM", "1001", "Exness-MT5"))
        self.assertFalse(self.registry.observe("A-SIM", "9999", "Exness-MT5"))
        self.assertEqual(len(self.registry.history("A-SIM")), 1)

    def test_live_profile_cannot_use_sim_mode(self) -> None:
        self.registry.register(
            profile_id="A-LIVE",
            broker_id="exness",
            account_login="2001",
            server="Exness-MT5Real",
            recorded_at="2026-10-21T00:00:00Z",
        )
        current = self.registry.current("A-LIVE")
        self.assertIsNotNone(current)
        row = self.registry._conn.execute(
            "SELECT environment, account_mode FROM profiles WHERE profile_id = 'A-LIVE'"
        ).fetchone()
        self.assertEqual(row, ("LIVE", "LIVE"))


class IsolationTests(unittest.TestCase):
    def test_registry_refuses_a_non_a_scope(self) -> None:
        with self.assertRaises(IsolationError):
            IdentityRegistry(sqlite3.connect(":memory:"), scope="B")
        with self.assertRaises(IsolationError):
            IdentityRegistry(sqlite3.connect(":memory:"), scope="GLOBAL")

    def test_unknown_profile_is_rejected(self) -> None:
        registry = _registry()
        with self.assertRaises(IsolationError):
            registry.register(
                profile_id="B-SIM",
                broker_id="alpaca",
                account_login="1",
                server="paper",
                recorded_at="2026-10-21T00:00:00Z",
            )

    def test_risk_projection_rejects_other_groups_and_pooled_fields(self) -> None:
        registry = _registry()
        saved = registry.project_risk(
            {
                "projection_id": "p-1",
                "group_id": "A",
                "broker_id": "exness",
                "account_id": "1001",
                "account_mode": "SIM",
                "environment": "SIM",
            }
        )
        self.assertEqual(saved["group_id"], "A")
        self.assertEqual(saved["account_mode"], "SIM")
        with self.assertRaises(IsolationError):
            registry.project_risk(
                {
                    "projection_id": "p-2",
                    "group_id": "B",
                    "broker_id": "alpaca",
                    "account_id": "1",
                    "account_mode": "SIM",
                    "environment": "SIM",
                }
            )
        with self.assertRaises(IsolationError):
            registry.project_risk(
                {
                    "projection_id": "p-3",
                    "group_id": "A",
                    "broker_id": "exness",
                    "account_id": "1001",
                    "account_mode": "SIM",
                    "environment": "SIM",
                    "combined_rcb": "700",
                }
            )
        with self.assertRaises(sqlite3.IntegrityError):
            registry._conn.execute("UPDATE risk_projections SET group_id = 'B'")

    def test_store_has_no_pooled_table(self) -> None:
        registry = _registry()
        names = {
            row[0]
            for row in registry._conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertTrue(names.isdisjoint({"portfolio_total", "combined_equity", "combined_rcb"}))


if __name__ == "__main__":
    unittest.main()
