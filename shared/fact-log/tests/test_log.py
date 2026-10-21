import json
import sqlite3
import unittest
from pathlib import Path

from sate_factlog.errors import FactLogWriteError, Unauthorized
from sate_factlog.log import EVENT_TYPES, FactLog, open_log, validate_envelope


def _log() -> FactLog:
    return FactLog(sqlite3.connect(":memory:"), writers=frozenset({"identity", "kernel-a"}))


def _append(
    log: FactLog,
    event_id: str,
    event_type: str = "alert",
    occurred_at: str = "2026-10-21T00:00:00Z",
    **payload: object,
):
    return log.append(
        event_id=event_id,
        event_type=event_type,
        group_scope="A",
        occurred_at=occurred_at,
        recorded_at="2026-10-21T00:00:01Z",
        correlation_id="corr-1",
        writer_id="identity",
        payload=dict(payload),
    )


def _journal() -> dict[str, str]:
    return {
        "as_of": "t",
        "hypothesis": "h",
        "advisory_inputs": "none",
        "risks": "gap",
        "expected_return": "0",
        "expected_downside": "0",
        "action": "abstain",
        "verdict_ref": "none",
    }


def _telegram() -> dict[str, str]:
    return {
        "message_id": "1",
        "principal": "owner",
        "scope": "A",
        "category": "halt",
        "severity": "critical",
        "resulting_event": "e-halt",
    }


class FactLogTests(unittest.TestCase):
    def test_chain_is_monotonic_and_idempotent(self) -> None:
        log = _log()
        first = _append(log, "e-1")
        again = _append(log, "e-1")
        second = _append(log, "e-2", occurred_at="2026-10-21T01:00:00Z")
        self.assertEqual(first.seq, 1)
        self.assertEqual(again.seq, 1)
        self.assertEqual(second.seq, 2)
        self.assertEqual(second.previous_hash, first.event_hash)
        validate_envelope(first.as_envelope())
        self.assertIsNone(log.verify(reader_id="identity"))

    def test_unauthorized_writer_is_rejected(self) -> None:
        log = _log()
        with self.assertRaises(Unauthorized):
            log.append(
                event_id="e-1",
                event_type="alert",
                group_scope="A",
                occurred_at="2026-10-21T00:00:00Z",
                recorded_at="2026-10-21T00:00:01Z",
                correlation_id="corr-1",
                writer_id="stranger",
                payload={},
            )

    def test_a_event_cannot_name_another_group(self) -> None:
        log = _log()
        with self.assertRaises(ValueError):
            _append(log, "e-1", group_id="B")

    def test_journal_requires_the_decision_fields(self) -> None:
        log = _log()
        with self.assertRaises(ValueError):
            _append(log, "e-1", event_type="journal", as_of="t", hypothesis="h")
        saved = _append(log, "e-2", event_type="journal", **_journal())
        self.assertEqual(saved.event_type, "journal")

    def test_query_and_export_are_scoped(self) -> None:
        log = _log()
        _append(log, "e-1", event_type="halt")
        _append(log, "e-2", event_type="alert")
        log.append(
            event_id="e-b",
            event_type="alert",
            group_scope="B",
            occurred_at="2026-10-21T00:00:00Z",
            recorded_at="2026-10-21T00:00:01Z",
            correlation_id="corr-b",
            writer_id="identity",
            payload={},
        )
        found = log.query(
            group_scope="A",
            occurred_from="2026-10-21T00:00:00Z",
            occurred_to="2026-10-21T00:00:00Z",
            event_type="halt",
            reader_id="identity",
        )
        self.assertEqual([row.event_id for row in found], ["e-1"])
        exported = log.export_audit(
            group_scope="A",
            occurred_from="2026-10-21T00:00:00Z",
            occurred_to="2026-10-22T00:00:00Z",
            reader_id="identity",
        )
        self.assertEqual({row["group_scope"] for row in exported}, {"A"})

    def test_verify_detects_a_broken_link(self) -> None:
        log = _log()
        _append(log, "e-1")
        _append(log, "e-2")
        log._conn.execute("DROP TRIGGER events_no_update")
        log._conn.execute("UPDATE events SET event_hash = 'broken' WHERE seq = 1")
        self.assertEqual(log.verify(reader_id="identity"), 1)

    def test_update_is_rejected_and_write_failure_is_not_fabricated(self) -> None:
        log = _log()
        _append(log, "e-1", event_type="capital_state")
        with self.assertRaises(sqlite3.IntegrityError):
            log._conn.execute("DELETE FROM events")
        log._conn.close()
        with self.assertRaises(FactLogWriteError) as caught:
            _append(log, "e-2", event_type="capital_state")
        self.assertEqual(caught.exception.policy, "BLOCK")

    def test_rows_cannot_be_updated(self) -> None:
        log = _log()
        _append(log, "e-1")
        with self.assertRaises(sqlite3.IntegrityError):
            log._conn.execute("UPDATE events SET writer_id = 'stranger'")

    def test_replay_stops_at_the_requested_time(self) -> None:
        log = _log()
        _append(log, "early", occurred_at="2026-10-21T00:00:00Z")
        _append(log, "late", occurred_at="2026-10-22T00:00:00Z")
        replayed = log.replay_through(
            group_scope="A", as_of="2026-10-21T12:00:00Z", reader_id="identity"
        )
        self.assertEqual([row.event_id for row in replayed], ["early"])

    def test_fresh_soak_has_not_met_the_gate(self) -> None:
        log = _log()
        status = log.soak_status(now="2026-10-21T00:00:00Z")
        self.assertEqual(status["elapsed_days"], 0.0)
        self.assertFalse(status["gate_met"])
        log.note_soak_start("2026-10-21T00:00:00Z")
        same_day = log.soak_status(now="2026-10-21T12:00:00Z")
        self.assertFalse(same_day["gate_met"])
        self.assertLess(same_day["elapsed_days"], 1)

    def test_log_does_not_increase_rcb(self) -> None:
        self.assertFalse(hasattr(FactLog, "increase_rcb"))

    def test_envelope_schema_requires_the_chain_fields(self) -> None:
        schema_path = Path(__file__).resolve().parents[2] / "schemas" / "event-envelope.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        required = set(schema["required"])
        for field in ("previous_hash", "payload_crc32", "event_type", "correlation_id", "category"):
            self.assertIn(field, required)

    def test_unknown_reader_is_rejected(self) -> None:
        log = _log()
        _append(log, "e-1")
        with self.assertRaises(Unauthorized):
            log.poll(after_seq=0, group_scope="A", reader_id="stranger")

    def test_correlation_links_one_scope(self) -> None:
        log = _log()
        log.append(
            event_id="intent",
            event_type="orders",
            group_scope="A",
            occurred_at="2026-10-21T00:00:00Z",
            recorded_at="2026-10-21T00:00:01Z",
            correlation_id="trade-1",
            writer_id="identity",
            payload={},
        )
        log.append(
            event_id="fill",
            event_type="fills",
            group_scope="A",
            occurred_at="2026-10-21T00:00:02Z",
            recorded_at="2026-10-21T00:00:03Z",
            correlation_id="trade-1",
            writer_id="identity",
            payload={},
        )
        log.append(
            event_id="other",
            event_type="fills",
            group_scope="B",
            occurred_at="2026-10-21T00:00:02Z",
            recorded_at="2026-10-21T00:00:03Z",
            correlation_id="trade-1",
            writer_id="identity",
            payload={},
        )
        linked = log.by_correlation(
            group_scope="A", correlation_id="trade-1", reader_id="identity"
        )
        self.assertEqual([row.event_id for row in linked], ["intent", "fill"])

    def test_correction_appends_and_leaves_the_original(self) -> None:
        log = _log()
        original = _append(log, "e-1", event_type="alert", note="first")
        corrected = log.compensate(
            event_id="e-2",
            corrects_event_id="e-1",
            event_type="alert",
            group_scope="A",
            occurred_at="2026-10-21T00:00:02Z",
            recorded_at="2026-10-21T00:00:03Z",
            correlation_id="corr-1",
            writer_id="identity",
            payload={"note": "second"},
        )
        stored = log.by_correlation(
            group_scope="A", correlation_id="corr-1", reader_id="identity"
        )
        self.assertEqual(stored[0].event_hash, original.event_hash)
        self.assertEqual(stored[0].payload["note"], "first")
        self.assertEqual(corrected.payload["corrects_event_id"], "e-1")

    def test_noncritical_write_failure_degrades(self) -> None:
        log = _log()
        log._conn.close()
        with self.assertRaises(FactLogWriteError) as caught:
            _append(log, "e-1", event_type="alert")
        self.assertEqual(caught.exception.policy, "DEGRADE")

    def test_every_event_class_can_be_stored(self) -> None:
        log = _log()
        for index, event_type in enumerate(EVENT_TYPES):
            extra: dict[str, object] = {}
            if event_type == "journal":
                extra = dict(_journal())
            elif event_type == "telegram":
                extra = dict(_telegram())
            _append(log, f"e-{index}", event_type=event_type, **extra)
        self.assertIsNone(log.verify(reader_id="identity"))

    def test_readonly_reader_can_poll_but_not_append(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.db"
            writer = open_log(path, writers=frozenset({"identity"}))
            _append(writer, "e-1")
            reader = open_log(
                path,
                writers=frozenset({"identity"}),
                readers=frozenset({"identity"}),
                readonly=True,
            )
            found = reader.poll(after_seq=0, group_scope="A", reader_id="identity")
            self.assertEqual([row.event_id for row in found], ["e-1"])
            with self.assertRaises(FactLogWriteError):
                _append(reader, "e-2")

    def test_bootstrap_records_soak_start_and_leaves_the_gate_closed(self) -> None:
        import os
        from tempfile import TemporaryDirectory

        from sate_factlog.bootstrap import main

        with TemporaryDirectory() as tmp:
            database = str(Path(tmp) / "staging.db")
            os.environ["SATE_FACTLOG_DB"] = database
            try:
                main()
                log = open_log(database, writers=frozenset({"identity"}))
                started = log.soak_started_at()
                self.assertIsNotNone(started)
                status = log.soak_status(now=str(started))
                self.assertFalse(status["gate_met"])
                self.assertEqual(status["elapsed_days"], 0.0)
                main()
                again = open_log(database, writers=frozenset({"identity"}))
                self.assertEqual(again.soak_started_at(), started)
            finally:
                os.environ.pop("SATE_FACTLOG_DB", None)


if __name__ == "__main__":
    unittest.main()
