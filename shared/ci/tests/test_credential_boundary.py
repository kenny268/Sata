"""Penetration-style check: the control plane cannot read trade credentials.

The cases are the report. A failure means a control-plane tree can see the vault.
"""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from sate_factlog.log import FactLog

ROOT = Path(__file__).resolve().parents[3]
PLANES = (
    ROOT / "shared" / "control-api",
    ROOT / "shared" / "notifier-bot",
    ROOT / "shared" / "web",
    ROOT / "group_a" / "broker" / "mt5-bridge",
    ROOT / "group_a" / "strategy",
)
NEEDLES = (
    "sate-a-credentials",
    "sate_a_credentials",
    "SATE_CREDENTIAL",
    "inject_at_startup",
    "TradeSecret",
)


def _sources(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    suffixes = {".py", ".rs", ".toml", ".json", ".yml", ".yaml", ".md"}
    return [path for path in folder.rglob("*") if path.is_file() and path.suffix in suffixes]


class CredentialBoundaryTests(unittest.TestCase):
    def test_control_plane_cannot_name_the_vault(self) -> None:
        for folder in PLANES:
            self.assertTrue(folder.exists(), str(folder))
            for path in _sources(folder):
                text = path.read_text(encoding="utf-8")
                for needle in NEEDLES:
                    self.assertNotIn(needle, text, f"{path} contains {needle}")

    def test_compose_does_not_inject_trade_credentials(self) -> None:
        text = (ROOT / "group_a" / "infra" / "compose.yaml").read_text(encoding="utf-8")
        self.assertNotIn("SATE_CREDENTIAL", text)
        self.assertNotIn("sate-a-credentials", text)
        self.assertNotIn("kernel-a", text)

    def test_control_api_cannot_write_or_smuggle_a_credential_event(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"kernel-a", "control-api"}))
        audit = {
            "action": "inject",
            "credential_id": "exness-sim",
            "key_id": "key-1",
            "previous_key_id": "",
            "mode": "SIM",
            "purpose": "startup",
        }
        with self.assertRaises(ValueError):
            _append(log, "c-control", "control-api", audit)
        leaked = dict(audit)
        leaked["password"] = "s3cret-value"
        with self.assertRaises(ValueError):
            _append(log, "c-secret", "kernel-a", leaked)
        _append(log, "c-kernel", "kernel-a", audit)
        stored = log.poll(after_seq=0, group_scope="A", reader_id="kernel-a")
        self.assertEqual([row.event_id for row in stored], ["c-kernel"])
        self.assertNotIn("password", stored[0].payload)
        self.assertEqual(set(stored[0].payload), set(audit))


def _append(log: FactLog, event_id: str, writer_id: str, payload: dict[str, object]) -> None:
    log.append(
        event_id=event_id,
        event_type="credential_use",
        group_scope="A",
        occurred_at="2026-10-22T21:00:00Z",
        recorded_at="2026-10-22T21:00:00Z",
        correlation_id="kernel-a",
        writer_id=writer_id,
        payload=payload,
    )


if __name__ == "__main__":
    unittest.main()
