"""SQLite registry for A-SIM and A-LIVE. History rows are append-only."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sate_identity.errors import IsolationError
from sate_identity.fingerprint import Fingerprint, parse_fingerprint, require_profile

DEFAULT_SCOPE = "A"
_FORBIDDEN_KEYS = frozenset({"combined_equity", "combined_rcb", "portfolio_total"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    profile_id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL CHECK (group_id = 'A'),
    broker_id TEXT NOT NULL CHECK (length(broker_id) > 0),
    environment TEXT NOT NULL CHECK (environment IN ('SIM', 'LIVE')),
    account_mode TEXT NOT NULL CHECK (account_mode IN ('SIM', 'LIVE')),
    CHECK (environment = account_mode)
);

CREATE TABLE IF NOT EXISTS fingerprint_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL REFERENCES profiles(profile_id),
    account_login TEXT NOT NULL,
    server TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS fingerprint_history_no_update
BEFORE UPDATE ON fingerprint_history
BEGIN
    SELECT RAISE(ABORT, 'fingerprint history is immutable');
END;

CREATE TRIGGER IF NOT EXISTS fingerprint_history_no_delete
BEFORE DELETE ON fingerprint_history
BEGIN
    SELECT RAISE(ABORT, 'fingerprint history is immutable');
END;

CREATE TABLE IF NOT EXISTS risk_projections (
    projection_id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL CHECK (group_id = 'A'),
    broker_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    account_mode TEXT NOT NULL CHECK (account_mode IN ('SIM', 'LIVE')),
    environment TEXT NOT NULL CHECK (environment IN ('SIM', 'LIVE')),
    CHECK (environment = account_mode)
);

CREATE TABLE IF NOT EXISTS projection_cursor (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    seq INTEGER NOT NULL
);
"""


class IdentityRegistry:
    def __init__(self, connection: sqlite3.Connection, *, scope: str = DEFAULT_SCOPE) -> None:
        if scope != DEFAULT_SCOPE:
            raise IsolationError(f"Group A registry refuses scope {scope!r}")
        self.scope = scope
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def register(
        self,
        *,
        profile_id: str,
        broker_id: str,
        account_login: str,
        server: str,
        recorded_at: str,
    ) -> None:
        environment = require_profile(profile_id)
        fingerprint = parse_fingerprint(account_login, server)
        broker = broker_id.strip()
        if not broker:
            raise IsolationError("broker_id is required")
        if not recorded_at.strip():
            raise IsolationError("recorded_at is required")
        try:
            self._conn.execute(
                """
                INSERT INTO profiles (profile_id, group_id, broker_id, environment, account_mode)
                VALUES (?, 'A', ?, ?, ?)
                """,
                (profile_id, broker, environment, environment),
            )
        except sqlite3.IntegrityError as exc:
            raise IsolationError(f"profile {profile_id} already exists") from exc
        self._append(profile_id, fingerprint, recorded_at)
        self._conn.commit()

    def change_fingerprint(
        self,
        *,
        profile_id: str,
        account_login: str,
        server: str,
        recorded_at: str,
    ) -> None:
        require_profile(profile_id)
        if self.current(profile_id) is None:
            raise IsolationError(f"profile {profile_id} is not registered")
        fingerprint = parse_fingerprint(account_login, server)
        self._append(profile_id, fingerprint, recorded_at)
        self._conn.commit()

    def history(self, profile_id: str) -> list[dict[str, str]]:
        require_profile(profile_id)
        rows = self._conn.execute(
            """
            SELECT account_login, server, recorded_at
            FROM fingerprint_history
            WHERE profile_id = ?
            ORDER BY history_id
            """,
            (profile_id,),
        ).fetchall()
        return [
            {"account_login": login, "server": server, "recorded_at": at}
            for login, server, at in rows
        ]

    def current(self, profile_id: str) -> dict[str, str] | None:
        rows = self.history(profile_id)
        if not rows:
            return None
        return rows[-1]

    def observe(self, profile_id: str, account_login: str, server: str) -> bool:
        current = self.current(profile_id)
        if current is None:
            raise IsolationError(f"profile {profile_id} is not registered")
        observed = parse_fingerprint(account_login, server)
        registered = Fingerprint(current["account_login"], current["server"])
        return registered.matches(observed)

    def has_risk_projection(self, projection_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM risk_projections WHERE projection_id = ?",
            (projection_id,),
        ).fetchone()
        return row is not None

    def projection_cursor(self) -> int:
        row = self._conn.execute("SELECT seq FROM projection_cursor WHERE id = 1").fetchone()
        if row is None:
            return 0
        return int(row[0])

    def store_projection_cursor(self, seq: int) -> None:
        self._conn.execute(
            """
            INSERT INTO projection_cursor (id, seq) VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET seq = excluded.seq
            """,
            (seq,),
        )
        self._conn.commit()

    def project_risk(self, event: dict[str, object]) -> dict[str, str]:
        overlap = _FORBIDDEN_KEYS.intersection(event)
        if overlap:
            names = ", ".join(sorted(overlap))
            raise IsolationError(f"reporting-only field cannot enter the risk store: {names}")
        group_id = event.get("group_id")
        if group_id != DEFAULT_SCOPE:
            raise IsolationError(f"risk projection refuses group {group_id!r}")
        account_mode = event.get("account_mode")
        environment = event.get("environment")
        if account_mode not in {"SIM", "LIVE"} or environment != account_mode:
            raise IsolationError("account_mode is required and must match environment")
        broker_id = str(event.get("broker_id", "")).strip()
        account_id = str(event.get("account_id", "")).strip()
        projection_id = str(event.get("projection_id", "")).strip()
        if not broker_id or not account_id or not projection_id:
            raise IsolationError("broker_id, account_id, and projection_id are required")
        try:
            self._conn.execute(
                """
                INSERT INTO risk_projections (
                    projection_id, group_id, broker_id, account_id, account_mode, environment
                ) VALUES (?, 'A', ?, ?, ?, ?)
                """,
                (projection_id, broker_id, account_id, account_mode, environment),
            )
        except sqlite3.IntegrityError as exc:
            raise IsolationError("risk projection violates the Group A store") from exc
        self._conn.commit()
        return {
            "projection_id": projection_id,
            "group_id": DEFAULT_SCOPE,
            "broker_id": broker_id,
            "account_id": account_id,
            "account_mode": str(account_mode),
            "environment": str(environment),
        }

    def _append(self, profile_id: str, fingerprint: Fingerprint, recorded_at: str) -> None:
        self._conn.execute(
            """
            INSERT INTO fingerprint_history (profile_id, account_login, server, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (profile_id, fingerprint.account_login, fingerprint.server, recorded_at.strip()),
        )


def open_registry(path: str | Path, *, scope: str = DEFAULT_SCOPE) -> IdentityRegistry:
    connection = sqlite3.connect(path)
    return IdentityRegistry(connection, scope=scope)


def open_configured(config_path: str | Path) -> IdentityRegistry:
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    scope = payload.get("group_scope")
    if scope != DEFAULT_SCOPE:
        raise IsolationError(f"configuration scope must be A, got {scope!r}")
    database = payload.get("database")
    if not isinstance(database, str) or not database:
        raise IsolationError("configuration database path is required")
    return open_registry(database, scope=scope)


def consume_fact_event(
    registry: IdentityRegistry,
    envelope: dict[str, object],
) -> dict[str, str] | None:
    """Project one fact-log envelope into the Group A risk store."""
    scope = envelope.get("group_scope")
    if scope != DEFAULT_SCOPE:
        raise IsolationError(f"fact event refuses group {scope!r}")
    if envelope.get("category") not in {"RISK_PROJECTION", "capital_state"}:
        return None
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise IsolationError("capital payload is required")
    if payload.get("group_id", DEFAULT_SCOPE) != scope:
        raise IsolationError("payload group does not match the fact-log scope")
    event = {str(key): value for key, value in payload.items()}
    event["group_id"] = DEFAULT_SCOPE
    return registry.project_risk(event)
