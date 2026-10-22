"""Every intent in the batch has a complete verdict in the fact log before a mock submit."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path

import jsonschema

from sate_factlog.log import FactLog

from sate_runtime.journal import (
    GateError,
    persist_credential_use,
    persist_lifecycle,
    persist_verdict,
    submit_persisted,
)

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

    def test_credential_use_records_the_action_and_refuses_a_password(self) -> None:
        log = _log()
        audit = {
            "action": "inject",
            "credential_id": "exness-sim",
            "key_id": "key-1",
            "previous_key_id": "",
            "mode": "SIM",
            "purpose": "startup",
        }
        persist_credential_use(
            log,
            audit,
            event_id="c-1",
            occurred_at=_NOW,
            recorded_at=_NOW,
            correlation_id="kernel-a",
        )
        stored = log.poll(after_seq=0, group_scope="A", reader_id="kernel-a")
        self.assertEqual(stored[0].event_type, "credential_use")
        self.assertNotIn("password", stored[0].payload)
        leaked = dict(audit)
        leaked["password"] = "s3cret-value"
        with self.assertRaises(GateError) as caught:
            persist_credential_use(
                log,
                leaked,
                event_id="c-2",
                occurred_at=_NOW,
                recorded_at=_NOW,
                correlation_id="kernel-a",
            )
        self.assertEqual(caught.exception.code, "secret")
        self.assertEqual(len(log.poll(after_seq=0, group_scope="A", reader_id="kernel-a")), 1)

    def test_a_partial_fill_is_stored_on_the_order_correlation(self) -> None:
        log = _log()
        event = {
            "intent_id": "i-1",
            "client_id": "i-1",
            "correlation_id": "A:i-1",
            "state": "Partial",
            "instrument": "EURUSD",
            "side": "BUY",
            "quantity": "1",
            "filled": "0.4",
            "remainder": "0.6",
            "broker_id": None,
            "kind": "partial",
        }
        persist_lifecycle(
            log,
            event,
            event_id="o-1",
            occurred_at=_NOW,
            recorded_at=_NOW,
            correlation_id="A:i-1",
        )
        stored = log.by_correlation(group_scope="A", correlation_id="A:i-1", reader_id="kernel-a")
        self.assertEqual(stored[0].event_type, "fills")
        self.assertEqual(stored[0].payload["remainder"], "0.6")
        with self.assertRaises(GateError) as caught:
            persist_lifecycle(
                log,
                {**event, "quantity": 0.4},
                event_id="o-2",
                occurred_at=_NOW,
                recorded_at=_NOW,
                correlation_id="A:i-1",
            )
        self.assertEqual(caught.exception.code, "record")
        with self.assertRaises(GateError) as text:
            persist_lifecycle(
                log,
                {**event, "quantity": "abc"},
                event_id="o-3",
                occurred_at=_NOW,
                recorded_at=_NOW,
                correlation_id="A:i-1",
            )
        self.assertEqual(text.exception.code, "record")


if __name__ == "__main__":
    unittest.main()
