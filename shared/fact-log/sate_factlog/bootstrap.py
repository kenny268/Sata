"""Create the fact-log database and start the staging soak clock."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sate_factlog.log import open_log

_WRITERS = frozenset({"identity", "kernel-a", "control-api", "rcb"})


def main() -> None:
    database = os.environ.get("SATE_FACTLOG_DB", "")
    if not database:
        raise SystemExit("SATE_FACTLOG_DB is required")
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    log = open_log(path, writers=_WRITERS, readers=_WRITERS)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log.note_soak_start(started)
    status = log.soak_status(now=log.soak_started_at() or started)
    print(f"fact log ready soak_gate_met={status['gate_met']}")


if __name__ == "__main__":
    main()
