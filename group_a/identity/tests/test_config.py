import json
import tempfile
import unittest
from pathlib import Path

from sate_identity.registry import open_configured, open_registry


class ConfiguredStoreTests(unittest.TestCase):
    def test_staging_config_defaults_to_group_a(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        payload = json.loads((repo / "config" / "staging.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["group_scope"], "A")
        self.assertEqual(payload["profiles"], ["A-SIM", "A-LIVE"])

    def test_open_configured_creates_an_a_only_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "staging.db"
            config = Path(tmp) / "staging.json"
            config.write_text(
                json.dumps({"group_scope": "A", "database": str(database)}),
                encoding="utf-8",
            )
            registry = open_configured(config)
            registry.register(
                profile_id="A-SIM",
                broker_id="exness",
                account_login="1001",
                server="Exness-MT5",
                recorded_at="2026-10-21T00:00:00Z",
            )
            reopened = open_registry(database)
            self.assertEqual(reopened.current("A-SIM")["account_login"], "1001")
            self.assertEqual(reopened.scope, "A")

    def test_fact_projection_cannot_mutate_another_group(self) -> None:
        from sate_identity.errors import IsolationError
        from sate_identity.registry import consume_fact_event

        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "staging.db"
            registry = open_registry(database)
            saved = consume_fact_event(
                registry,
                {
                    "event_id": "e-1",
                    "group_scope": "A",
                    "occurred_at": "2026-10-21T00:00:00Z",
                    "category": "RISK_PROJECTION",
                    "payload": {
                        "projection_id": "p-1",
                        "broker_id": "exness",
                        "account_id": "1001",
                        "account_mode": "SIM",
                        "environment": "SIM",
                    },
                },
            )
            self.assertIsNotNone(saved)
            with self.assertRaises(IsolationError):
                consume_fact_event(
                    registry,
                    {
                        "event_id": "e-2",
                        "group_scope": "B",
                        "occurred_at": "2026-10-21T00:00:00Z",
                        "category": "RISK_PROJECTION",
                        "payload": {
                            "projection_id": "p-2",
                            "broker_id": "alpaca",
                            "account_id": "1",
                            "account_mode": "SIM",
                            "environment": "SIM",
                        },
                    },
                )
            reopened = open_registry(database)
            groups = {
                row[0]
                for row in reopened._conn.execute("SELECT group_id FROM risk_projections")
            }
            self.assertEqual(groups, {"A"})


if __name__ == "__main__":
    unittest.main()
