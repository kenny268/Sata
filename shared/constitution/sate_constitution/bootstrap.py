"""Verify the staging constitution and record its activation on the fact log."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from sate_factlog.log import open_log

from sate_constitution.service import view
from sate_constitution.sourced import replay, submit_activate

_ROOT = Path(__file__).resolve().parents[1]
_PARTY = frozenset({"constitution"})


def main() -> None:
    scope = os.environ.get("SATE_GROUP_SCOPE", "A")
    fact_log = os.environ.get("SATE_FACTLOG_DB", "")
    database = os.environ.get("SATE_CONSTITUTION_DB", "")
    if not fact_log or not database:
        raise SystemExit("SATE_FACTLOG_DB and SATE_CONSTITUTION_DB are required")
    pin = json.loads((_ROOT / "config" / "staging.json").read_text(encoding="utf-8"))
    signed_path = Path(os.environ.get("SATE_CONSTITUTION_FILE", str(_ROOT / "example" / "staging.signed.json")))
    envelope = json.loads(signed_path.read_text(encoding="utf-8"))
    public_key = bytes.fromhex(pin["public_key_hex"])
    key_id = str(pin["key_id"])
    path = _wait(Path(fact_log))
    log = open_log(path, writers=_PARTY, readers=_PARTY)
    state = replay(log, scope, public_key=public_key, key_id=key_id)
    if state.active_json is None:
        state = submit_activate(
            log,
            state,
            envelope,
            public_key=public_key,
            key_id=key_id,
            now=envelope["effective_at"],
            event_id="constitution-a-001-v1",
            recorded_at=envelope["effective_at"],
            correlation_id="constitution-a-001",
        )
    snapshot = view(state)
    _store(Path(database), snapshot)
    print(
        "constitution ready"
        f" scope={scope}"
        f" version={snapshot['active_version']}"
        f" live_permitted={snapshot['live_permitted']}"
    )


def _wait(path: Path) -> Path:
    for _ in range(25):
        if path.exists():
            return path
        time.sleep(0.2)
    raise SystemExit("fact log database is not ready")


def _store(path: Path, snapshot: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS projection (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            payload_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO projection (id, payload_json) VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET payload_json = excluded.payload_json
        """,
        (json.dumps(snapshot, sort_keys=True),),
    )
    connection.commit()
    connection.close()


def matches_replay(database: Path, log, scope: str, public_key: bytes, key_id: str) -> bool:
    connection = sqlite3.connect(database)
    row = connection.execute("SELECT payload_json FROM projection").fetchone()
    connection.close()
    if row is None:
        return False
    current = view(replay(log, scope, public_key=public_key, key_id=key_id))
    return json.loads(row[0]) == current


if __name__ == "__main__":
    main()
