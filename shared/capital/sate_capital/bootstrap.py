"""Rebuild the Group capital projection from the fact log."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from sate_factlog.log import open_log

from sate_capital.ledger import CapitalState, export_state
from sate_capital.sourced import replay

_PARTY = frozenset({"capital"})


def main() -> None:
    scope = os.environ.get("SATE_GROUP_SCOPE", "A")
    fact_log = os.environ.get("SATE_FACTLOG_DB", "")
    database = os.environ.get("SATE_CAPITAL_DB", "")
    if not fact_log or not database:
        raise SystemExit("SATE_FACTLOG_DB and SATE_CAPITAL_DB are required")
    path = _wait(Path(fact_log))
    log = open_log(path, writers=_PARTY, readers=_PARTY, readonly=True)
    state = replay(log, scope)
    _store(Path(database), state)
    print(
        "capital ledger ready"
        f" scope={state.group_scope}"
        f" equity={state.equity}"
        f" realised_pnl={state.realised_pnl}"
        f" settled={state.settled}"
        f" reserved={state.reserved}"
        f" withdrawable={state.withdrawable}"
    )


def _wait(path: Path) -> Path:
    for _ in range(25):
        if path.exists():
            return path
        time.sleep(0.2)
    raise SystemExit("fact log database is not ready")


def _store(path: Path, state: CapitalState) -> None:
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
    payload = json.dumps(export_state(state), sort_keys=True)
    connection.execute(
        """
        INSERT INTO projection (id, payload_json) VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET payload_json = excluded.payload_json
        """,
        (payload,),
    )
    connection.commit()
    connection.close()


def matches_replay(database: Path, log, scope: str) -> bool:
    connection = sqlite3.connect(database)
    row = connection.execute("SELECT payload_json FROM projection").fetchone()
    connection.close()
    if row is None:
        return False
    stored = json.loads(row[0])
    return stored == export_state(replay(log, scope))


if __name__ == "__main__":
    main()
