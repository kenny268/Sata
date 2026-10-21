import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sate_factlog.log import FactLog

from sate_identity.bootstrap import main
from sate_identity.registry import IdentityRegistry, open_registry
from sate_identity.sourced import apply_pending, submit_capital_state, submit_registration


class SourcedProjectionTests(unittest.TestCase):
    def test_projection_waits_for_the_log(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"identity"}))
        registry = IdentityRegistry(sqlite3.connect(":memory:"))
        submit_capital_state(
            log,
            {
                "projection_id": "p-1",
                "broker_id": "exness",
                "account_id": "1001",
                "account_mode": "SIM",
                "environment": "SIM",
            },
            event_id="e-1",
            occurred_at="2026-10-21T00:00:00Z",
            recorded_at="2026-10-21T00:00:01Z",
            correlation_id="corr-1",
        )
        pending = registry._conn.execute("SELECT COUNT(*) FROM risk_projections").fetchone()
        self.assertEqual(pending[0], 0)
        cursor = apply_pending(log, registry, 0)
        self.assertEqual(cursor, 1)
        stored = registry._conn.execute(
            "SELECT group_id, account_mode FROM risk_projections"
        ).fetchone()
        self.assertEqual(stored, ("A", "SIM"))

    def test_registration_is_applied_from_the_log(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"identity"}))
        registry = IdentityRegistry(sqlite3.connect(":memory:"))
        submit_registration(
            log,
            {
                "profile_id": "A-SIM",
                "broker_id": "exness",
                "account_login": "1001",
                "server": "Exness-MT5",
                "recorded_at": "2026-10-21T00:00:00Z",
            },
            event_id="e-reg",
            occurred_at="2026-10-21T00:00:00Z",
            recorded_at="2026-10-21T00:00:01Z",
            correlation_id="corr-reg",
        )
        self.assertIsNone(registry.current("A-SIM"))
        apply_pending(log, registry, 0)
        self.assertEqual(registry.current("A-SIM")["account_login"], "1001")

    def test_other_scope_transition_does_not_change_group_a(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"identity"}))
        registry = IdentityRegistry(sqlite3.connect(":memory:"))
        log.append(
            event_id="e-b",
            event_type="state_transition",
            group_scope="B",
            occurred_at="2026-10-21T00:00:00Z",
            recorded_at="2026-10-21T00:00:01Z",
            correlation_id="corr-b",
            writer_id="identity",
            payload={
                "profile_id": "A-SIM",
                "broker_id": "exness",
                "account_login": "9999",
                "server": "Other",
                "recorded_at": "2026-10-21T00:00:00Z",
            },
        )
        apply_pending(log, registry, 0)
        self.assertIsNone(registry.current("A-SIM"))

    def test_bootstrap_applies_events_from_the_log(self) -> None:
        with TemporaryDirectory() as tmp:
            fact = Path(tmp) / "fact.db"
            ident = Path(tmp) / "identity.db"
            log = FactLog(sqlite3.connect(fact), writers=frozenset({"identity"}))
            submit_capital_state(
                log,
                {
                    "projection_id": "p-1",
                    "broker_id": "exness",
                    "account_id": "1001",
                    "account_mode": "SIM",
                    "environment": "SIM",
                },
                event_id="e-1",
                occurred_at="2026-10-21T00:00:00Z",
                recorded_at="2026-10-21T00:00:01Z",
                correlation_id="corr-1",
            )
            os.environ["SATE_GROUP_SCOPE"] = "A"
            os.environ["SATE_IDENTITY_DB"] = str(ident)
            os.environ["SATE_FACTLOG_DB"] = str(fact)
            try:
                main()
                registry = open_registry(ident)
                self.assertTrue(registry.has_risk_projection("p-1"))
                self.assertEqual(registry.projection_cursor(), 1)
                main()
                reopened = open_registry(ident)
                self.assertEqual(reopened.projection_cursor(), 1)
            finally:
                os.environ.pop("SATE_GROUP_SCOPE", None)
                os.environ.pop("SATE_IDENTITY_DB", None)
                os.environ.pop("SATE_FACTLOG_DB", None)


if __name__ == "__main__":
    unittest.main()
