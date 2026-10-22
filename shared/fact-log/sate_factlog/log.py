"""Hash-chained append-only log. Corrections are new events."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from sate_factlog.errors import FactLogWriteError, Unauthorized

EVENT_TYPES = (
    "orders",
    "fills",
    "positions",
    "broker_balances",
    "capital_state",
    "rcb_change",
    "constitution",
    "signature",
    "deployment",
    "verdict",
    "halt",
    "reimbursement",
    "invoice",
    "alert",
    "model_version",
    "advisory_signal",
    "state_transition",
    "reconciliation",
    "failure",
    "owner_action",
    "check_in",
    "journal",
    "telegram",
)
BLOCKING_TYPES = frozenset({
    "halt",
    "capital_state",
    "owner_action",
    "constitution",
    "failure",
    "state_transition",
    "verdict",
})
SCOPES = frozenset({"A", "B", "GLOBAL"})
GENESIS = "0" * 64
SCHEMA_VERSION = 1
JOURNAL_FIELDS = (
    "as_of",
    "hypothesis",
    "advisory_inputs",
    "risks",
    "expected_return",
    "expected_downside",
    "action",
    "verdict_ref",
)
TELEGRAM_FIELDS = (
    "message_id",
    "principal",
    "scope",
    "category",
    "severity",
    "resulting_event",
)
_ENVELOPE_FIELDS = (
    "event_id",
    "event_type",
    "group_scope",
    "occurred_at",
    "recorded_at",
    "correlation_id",
    "source",
    "payload_crc32",
    "schema_version",
    "previous_hash",
    "category",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    group_scope TEXT NOT NULL CHECK (group_scope IN ('A', 'B', 'GLOBAL')),
    occurred_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    writer_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_crc32 TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    provenance TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'fact log is append-only');
END;
CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'fact log is append-only');
END;
CREATE TABLE IF NOT EXISTS soak (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    started_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class FactRecord:
    seq: int
    event_id: str
    event_type: str
    group_scope: str
    occurred_at: str
    recorded_at: str
    correlation_id: str
    writer_id: str
    payload: dict[str, object]
    payload_crc32: str
    previous_hash: str
    event_hash: str
    provenance: str

    def as_envelope(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "category": self.event_type,
            "group_scope": self.group_scope,
            "occurred_at": self.occurred_at,
            "recorded_at": self.recorded_at,
            "correlation_id": self.correlation_id,
            "source": self.writer_id,
            "payload_crc32": self.payload_crc32,
            "previous_hash": self.previous_hash,
            "schema_version": SCHEMA_VERSION,
            "provenance": self.provenance,
            "payload": self.payload,
        }


class FactLog:
    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        writers: frozenset[str],
        readers: frozenset[str] | None = None,
        readonly: bool = False,
    ) -> None:
        if not writers:
            raise Unauthorized("at least one writer is required")
        allowed_readers = writers if readers is None else readers
        if not allowed_readers:
            raise Unauthorized("at least one reader is required")
        self._conn = connection
        self._writers = writers
        self._readers = allowed_readers
        self._readonly = readonly
        if not readonly:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def append(
        self,
        *,
        event_id: str,
        event_type: str,
        group_scope: str,
        occurred_at: str,
        recorded_at: str,
        correlation_id: str,
        writer_id: str,
        payload: dict[str, object],
        provenance: str = "",
    ) -> FactRecord:
        self._authorize(writer_id)
        self._validate(
            event_id,
            event_type,
            group_scope,
            occurred_at,
            recorded_at,
            correlation_id,
            payload,
        )
        policy = "BLOCK" if event_type in BLOCKING_TYPES else "DEGRADE"
        if self._readonly:
            raise FactLogWriteError("fact log is read-only", policy=policy)
        try:
            existing = self._by_id(event_id)
            if existing is not None:
                return existing
            seq = self._next_seq()
            previous = self._tip_hash()
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            crc = f"{zlib.crc32(encoded.encode()) & 0xFFFFFFFF:08x}"
            digest = _chain_hash(
                previous, crc, event_id, seq, event_type, group_scope, occurred_at, provenance
            )
            self._conn.execute(
                """
                INSERT INTO events (
                    seq, event_id, event_type, group_scope, occurred_at, recorded_at,
                    correlation_id, writer_id, payload_json, payload_crc32,
                    previous_hash, event_hash, schema_version, provenance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    seq,
                    event_id,
                    event_type,
                    group_scope,
                    occurred_at,
                    recorded_at,
                    correlation_id,
                    writer_id,
                    encoded,
                    crc,
                    previous,
                    digest,
                    SCHEMA_VERSION,
                    provenance,
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            try:
                self._conn.rollback()
            except sqlite3.Error:
                pass
            raise FactLogWriteError("fact log write failed", policy=policy) from exc
        stored = self._by_id(event_id)
        if stored is None:
            raise FactLogWriteError("fact log write failed", policy=policy)
        return stored

    def compensate(
        self,
        *,
        event_id: str,
        corrects_event_id: str,
        event_type: str,
        group_scope: str,
        occurred_at: str,
        recorded_at: str,
        correlation_id: str,
        writer_id: str,
        payload: dict[str, object],
        provenance: str = "",
    ) -> FactRecord:
        """Append a correction. The original row is left unchanged."""
        original = self._by_id(corrects_event_id)
        if original is None:
            raise ValueError("correction target does not exist")
        if original.group_scope != group_scope:
            raise ValueError("correction scope must match the original event")
        body = dict(payload)
        body["corrects_event_id"] = corrects_event_id
        return self.append(
            event_id=event_id,
            event_type=event_type,
            group_scope=group_scope,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            correlation_id=correlation_id,
            writer_id=writer_id,
            payload=body,
            provenance=provenance,
        )

    def poll(self, *, after_seq: int, group_scope: str, reader_id: str) -> list[FactRecord]:
        self._authorize_reader(reader_id)
        self._require_scope(group_scope)
        rows = self._conn.execute(
            """
            SELECT seq, event_id, event_type, group_scope, occurred_at, recorded_at,
                   correlation_id, writer_id, payload_json, payload_crc32,
                   previous_hash, event_hash, provenance
            FROM events
            WHERE seq > ? AND group_scope = ?
            ORDER BY seq
            """,
            (after_seq, group_scope),
        ).fetchall()
        return [_row(row) for row in rows]

    def query(
        self,
        *,
        group_scope: str,
        occurred_from: str,
        occurred_to: str,
        event_type: str | None = None,
        reader_id: str,
    ) -> list[FactRecord]:
        self._authorize_reader(reader_id)
        self._require_scope(group_scope)
        sql = """
            SELECT seq, event_id, event_type, group_scope, occurred_at, recorded_at,
                   correlation_id, writer_id, payload_json, payload_crc32,
                   previous_hash, event_hash, provenance
            FROM events
            WHERE group_scope = ? AND occurred_at >= ? AND occurred_at <= ?
        """
        params: list[object] = [group_scope, occurred_from, occurred_to]
        if event_type is not None:
            sql += " AND event_type = ?"
            params.append(event_type)
        sql += " ORDER BY seq"
        return [_row(row) for row in self._conn.execute(sql, params).fetchall()]

    def export_audit(
        self,
        *,
        group_scope: str,
        occurred_from: str,
        occurred_to: str,
        reader_id: str,
    ) -> list[dict[str, object]]:
        records = self.query(
            group_scope=group_scope,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            reader_id=reader_id,
        )
        exported: list[dict[str, object]] = []
        for record in records:
            envelope = record.as_envelope()
            exported.append(envelope | {"event_hash": record.event_hash, "seq": record.seq})
        return exported

    def by_correlation(
        self, *, group_scope: str, correlation_id: str, reader_id: str
    ) -> list[FactRecord]:
        self._authorize_reader(reader_id)
        self._require_scope(group_scope)
        rows = self._conn.execute(
            """
            SELECT seq, event_id, event_type, group_scope, occurred_at, recorded_at,
                   correlation_id, writer_id, payload_json, payload_crc32,
                   previous_hash, event_hash, provenance
            FROM events
            WHERE group_scope = ? AND correlation_id = ?
            ORDER BY seq
            """,
            (group_scope, correlation_id),
        ).fetchall()
        return [_row(row) for row in rows]

    def replay_through(self, *, group_scope: str, as_of: str, reader_id: str) -> list[FactRecord]:
        """Events for one scope whose broker time is at or before as_of."""
        self._authorize_reader(reader_id)
        self._require_scope(group_scope)
        rows = self._conn.execute(
            """
            SELECT seq, event_id, event_type, group_scope, occurred_at, recorded_at,
                   correlation_id, writer_id, payload_json, payload_crc32,
                   previous_hash, event_hash, provenance
            FROM events
            WHERE group_scope = ? AND occurred_at <= ?
            ORDER BY seq
            """,
            (group_scope, as_of),
        ).fetchall()
        return [_row(row) for row in rows]

    def verify(self, *, reader_id: str) -> int | None:
        """Return the first broken seq, or None when the chain is intact."""
        self._authorize_reader(reader_id)
        return self._verify()

    def _verify(self) -> int | None:
        previous = GENESIS
        expected_seq = 1
        rows = self._conn.execute(
            """
            SELECT seq, event_id, event_type, group_scope, occurred_at,
                   payload_crc32, previous_hash, event_hash, provenance
            FROM events ORDER BY seq
            """
        ).fetchall()
        for seq, event_id, event_type, scope, occurred_at, crc, prev, digest, provenance in rows:
            if seq != expected_seq or prev != previous:
                return int(seq)
            recomputed = _chain_hash(
                prev, crc, event_id, seq, event_type, scope, occurred_at, str(provenance)
            )
            if recomputed != digest:
                return int(seq)
            previous = digest
            expected_seq += 1
        return None

    def note_soak_start(self, started_at: str) -> None:
        self._conn.execute(
            "INSERT INTO soak (id, started_at) VALUES (1, ?) ON CONFLICT(id) DO NOTHING",
            (started_at,),
        )
        self._conn.commit()

    def soak_started_at(self) -> str | None:
        row = self._conn.execute("SELECT started_at FROM soak WHERE id = 1").fetchone()
        if row is None:
            return None
        return str(row[0])

    def soak_status(self, *, now: str, required_days: int = 7) -> dict[str, object]:
        """Report elapsed soak time. A fresh log has not met the gate."""
        started = self.soak_started_at()
        intact = self._verify() is None
        if started is None:
            return {"started_at": None, "elapsed_days": 0.0, "chain_ok": intact, "gate_met": False}
        elapsed = (_parse(now) - _parse(started)).total_seconds() / 86400
        return {
            "started_at": started,
            "elapsed_days": elapsed,
            "chain_ok": intact,
            "gate_met": intact and elapsed >= required_days,
        }

    def _authorize(self, writer_id: str) -> None:
        if writer_id not in self._writers:
            raise Unauthorized(f"writer {writer_id!r} cannot append")

    def _authorize_reader(self, reader_id: str) -> None:
        if reader_id not in self._readers:
            raise Unauthorized(f"reader {reader_id!r} cannot read")

    def _validate(
        self,
        event_id: str,
        event_type: str,
        group_scope: str,
        occurred_at: str,
        recorded_at: str,
        correlation_id: str,
        payload: dict[str, object],
    ) -> None:
        if not event_id.strip() or not occurred_at.strip() or not recorded_at.strip():
            raise ValueError("event_id and timestamps are required")
        if not correlation_id.strip():
            raise ValueError("correlation_id is required")
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event type {event_type!r}")
        if group_scope not in SCOPES:
            raise ValueError(f"unknown group scope {group_scope!r}")
        if group_scope == "A" and payload.get("group_id") not in (None, "A"):
            raise ValueError("an A event cannot carry another group's identity")
        if event_type == "journal":
            for key in JOURNAL_FIELDS:
                if not str(payload.get(key, "")).strip():
                    raise ValueError(f"journal event requires {key}")
        if event_type == "telegram":
            for key in TELEGRAM_FIELDS:
                if not str(payload.get(key, "")).strip():
                    raise ValueError(f"telegram event requires {key}")
            if payload.get("scope") != group_scope:
                raise ValueError("telegram scope must match group_scope")

    def _next_seq(self) -> int:
        row = self._conn.execute("SELECT COALESCE(MAX(seq), 0) FROM events").fetchone()
        return int(row[0]) + 1

    def _tip_hash(self) -> str:
        row = self._conn.execute(
            "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return GENESIS
        return str(row[0])

    def _by_id(self, event_id: str) -> FactRecord | None:
        row = self._conn.execute(
            """
            SELECT seq, event_id, event_type, group_scope, occurred_at, recorded_at,
                   correlation_id, writer_id, payload_json, payload_crc32,
                   previous_hash, event_hash, provenance
            FROM events WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()
        if row is None:
            return None
        return _row(row)

    def _require_scope(self, group_scope: str) -> None:
        if group_scope not in SCOPES:
            raise ValueError(f"unknown group scope {group_scope!r}")


def open_log(
    path: str | Path,
    *,
    writers: frozenset[str],
    readers: frozenset[str] | None = None,
    readonly: bool = False,
) -> FactLog:
    if readonly:
        resolved = quote(Path(path).resolve().as_posix())
        connection = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
    else:
        connection = sqlite3.connect(path)
    return FactLog(connection, writers=writers, readers=readers, readonly=readonly)


def validate_envelope(envelope: dict[str, object]) -> None:
    for field in _ENVELOPE_FIELDS:
        if field not in envelope:
            raise ValueError(f"envelope requires {field}")
    if envelope["group_scope"] not in SCOPES:
        raise ValueError("envelope group_scope is not valid")
    if envelope["category"] != envelope["event_type"]:
        raise ValueError("envelope category must match event_type")
    previous = str(envelope["previous_hash"])
    if len(previous) != 64:
        raise ValueError("envelope previous_hash is not a sha256 digest")
    crc = str(envelope["payload_crc32"])
    if len(crc) != 8:
        raise ValueError("envelope payload_crc32 is not a crc32")


def _chain_hash(
    previous: str,
    crc: str,
    event_id: str,
    seq: int,
    event_type: str,
    scope: str,
    occurred_at: str,
    provenance: str,
) -> str:
    material = "|".join(
        (previous, crc, event_id, str(seq), event_type, scope, occurred_at, provenance)
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _row(row: tuple) -> FactRecord:
    payload = json.loads(row[8])
    return FactRecord(
        seq=int(row[0]),
        event_id=str(row[1]),
        event_type=str(row[2]),
        group_scope=str(row[3]),
        occurred_at=str(row[4]),
        recorded_at=str(row[5]),
        correlation_id=str(row[6]),
        writer_id=str(row[7]),
        payload=payload,
        payload_crc32=str(row[9]),
        previous_hash=str(row[10]),
        event_hash=str(row[11]),
        provenance=str(row[12]),
    )
