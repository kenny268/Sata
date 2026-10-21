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


if __name__ == "__main__":
    unittest.main()
