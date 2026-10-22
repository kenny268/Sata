"""Rebuild the RCB projection from the fact log."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from sate_factlog.log import open_log

from sate_rcb.service import export_state
from sate_rcb.sourced import replay

_PARTY = frozenset({"rcb"})


def main() -> None:
    scope = os.environ.get("SATE_GROUP_SCOPE", "A")
    fact_log = os.environ.get("SATE_FACTLOG_DB", "")
    database = os.environ.get("SATE_RCB_DB", "")
    if not fact_log or not database:
        raise SystemExit("SATE_FACTLOG_DB and SATE_RCB_DB are required")
    path = _wait(Path(fact_log))
    log = open_log(path, writers=_PARTY, readers=_PARTY, readonly=True)
    state = replay(log, scope)
    view = export_state(state)
    _store(Path(database), view)
    print(
        "rcb ready"
        f" scope={scope}"
        f" version={state.version}"
        f" base={state.ratified_base}"
    )


def _wait(path: Path) -> Path:
    for _ in range(25):
        if path.exists():
            return path
        time.sleep(0.2)
    raise SystemExit("fact log database is not ready")


def _store(path: Path, view: dict[str, object]) -> None:
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
        (json.dumps(view, sort_keys=True),),
    )
    connection.commit()
    connection.close()


def matches_replay(database: Path, log, scope: str) -> bool:
    connection = sqlite3.connect(database)
    row = connection.execute("SELECT payload_json FROM projection").fetchone()
    connection.close()
    if row is None:
        return False
    return json.loads(row[0]) == export_state(replay(log, scope))


if __name__ == "__main__":
    main()
