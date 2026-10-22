"""Verify the staging kernel artifact and record its activation on the fact log."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from sate_factlog.log import open_log

from sate_release.artifact import Pins
from sate_release.service import view
from sate_release.sourced import replay, submit_activate, submit_stage

_ROOT = Path(__file__).resolve().parents[1]
_PARTY = frozenset({"release"})


def main() -> None:
    fact_log = os.environ.get("SATE_FACTLOG_DB", "")
    database = os.environ.get("SATE_RELEASE_DB", "")
    if not fact_log or not database:
        raise SystemExit("SATE_FACTLOG_DB and SATE_RELEASE_DB are required")
    pin = json.loads((_ROOT / "config" / "staging.json").read_text(encoding="utf-8"))
    pins = pins_from(pin)
    manifest = json.loads((_ROOT / "example" / "staging.manifest.json").read_text(encoding="utf-8"))
    authorization = json.loads((_ROOT / "example" / "staging.authorization.json").read_text(encoding="utf-8"))
    binary = (_ROOT / "example" / "kernel-a.stub").read_bytes()
    path = _wait(Path(fact_log))
    log = open_log(path, writers=_PARTY, readers=_PARTY)
    state = replay(log, pins)
    if state.active is None:
        now = str(authorization["authorization"]["authorized_at"])
        identity = {
            "event_id": "release-a-kernel-stage",
            "recorded_at": now,
            "correlation_id": "release-a-kernel",
            "occurred_at": now,
        }
        state = submit_stage(log, state, manifest, binary, now=now, **identity)
        state = submit_activate(
            log,
            state,
            authorization,
            now=now,
            event_id="release-a-kernel-activate",
            recorded_at=now,
            correlation_id="release-a-kernel",
            occurred_at=now,
        )
    snapshot = view(state)
    _store(Path(database), snapshot)
    print(
        "release ready"
        f" scope={snapshot['group_scope']}"
        f" binary={snapshot['active_binary_sha256']}"
        f" reprovision_required={snapshot['reprovision_required']}"
    )


def pins_from(pin: dict[str, object]) -> Pins:
    return Pins(
        build_key_id=str(pin["build_key_id"]),
        build_public_hex=str(pin["build_public_key_hex"]),
        deploy_key_id=str(pin["deploy_key_id"]),
        deploy_public_hex=str(pin["deploy_public_key_hex"]),
        constitution_key_id=str(pin["constitution_key_id"]),
        constitution_version=int(pin["constitution_version"]),
        constitution_hash=str(pin["constitution_hash"]),
    )


def matches_replay(database: Path, log, pins: Pins) -> bool:
    connection = sqlite3.connect(database)
    row = connection.execute("SELECT payload_json FROM projection").fetchone()
    connection.close()
    if row is None:
        return False
    return json.loads(row[0]) == view(replay(log, pins))


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


if __name__ == "__main__":
    main()
