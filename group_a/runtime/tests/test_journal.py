"""Every intent in the batch has a complete verdict in the fact log before a mock submit."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path

import jsonschema

from sate_factlog.log import FactLog

from sate_runtime.journal import GateError, persist_verdict, submit_persisted

_NOW = "2026-10-22T21:00:00Z"
_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[3] / "shared" / "schemas" / "verdict.schema.json").read_text()
)


def _log() -> FactLog:
    return FactLog(sqlite3.connect(":memory:"), writers=frozenset({"kernel-a"}))


def _verdict(intent_id: str, decision: str) -> dict[str, object]:
    return {
        "intent_id": intent_id,
        "group": "A",
        "kernel_version": "0.1.0",
        "constitution_version": "1",
        "decision": decision,
        "approved_quantity": "1" if decision == "AllowWithSize" else None,
        "reject_reason": None if decision == "Allow" else "halt",
        "checks": [{"name": "halt_kill", "passed": decision != "Reject", "value": "", "limit": ""}],
        "halt_level": None,
        "kill_state": None,
        "latency_us": 12,
        "issued_at": _NOW,
    }


class JournalTests(unittest.TestCase):
    def test_each_intent_is_logged_and_only_an_allow_submits(self) -> None:
        log = _log()
        decisions = ("Allow", "Reject", "AllowWithSize")
        for index, decision in enumerate(decisions):
            persist_verdict(
                log,
                _verdict(f"i-{index}", decision),
                event_id=f"v-{index}",
                occurred_at=_NOW,
                recorded_at=_NOW,
                correlation_id="kernel-a",
            )
        stored = log.poll(after_seq=0, group_scope="A", reader_id="kernel-a")
        self.assertEqual([row.payload["intent_id"] for row in stored], ["i-0", "i-1", "i-2"])
        self.assertEqual(len(stored), 3)
        for row in stored:
            jsonschema.validate(row.payload, _SCHEMA)
            self.assertNotIn("group", row.payload)
        with self.assertRaises(GateError) as missing:
            submit_persisted(_verdict("i-0", "Allow"), persisted=False)
        self.assertEqual(missing.exception.code, "fact_log")
        self.assertEqual(submit_persisted(_verdict("i-0", "Allow"), persisted=True), "i-0")
        with self.assertRaises(GateError) as rejected:
            submit_persisted(_verdict("i-1", "Reject"), persisted=True)
        self.assertEqual(rejected.exception.code, "verdict")
        self.assertIsNone(log.verify(reader_id="kernel-a"))

    def test_an_incomplete_verdict_is_not_appended(self) -> None:
        log = _log()
        payload = _verdict("i-9", "Allow")
        del payload["kernel_version"]
        with self.assertRaises(GateError) as incomplete:
            persist_verdict(
                log,
                payload,
                event_id="v-9",
                occurred_at=_NOW,
                recorded_at=_NOW,
                correlation_id="kernel-a",
            )
        self.assertEqual(incomplete.exception.code, "record")
        self.assertEqual(log.poll(after_seq=0, group_scope="A", reader_id="kernel-a"), [])


if __name__ == "__main__":
    unittest.main()
