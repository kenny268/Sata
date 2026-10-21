"""Create the Group A identity database and apply fact-log events."""

from __future__ import annotations

import os
import time
from pathlib import Path

from sate_factlog.log import open_log

from sate_identity.registry import DEFAULT_SCOPE, open_registry
from sate_identity.sourced import apply_pending

_READERS = frozenset({"identity"})


def main() -> None:
    scope = os.environ.get("SATE_GROUP_SCOPE", DEFAULT_SCOPE)
    database = os.environ.get("SATE_IDENTITY_DB", "")
    if not database:
        raise SystemExit("SATE_IDENTITY_DB is required")
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    registry = open_registry(path, scope=scope)
    applied = _apply_fact_log(registry)
    print(f"identity store ready scope={registry.scope} applied={applied}")


def _apply_fact_log(registry) -> int:
    database = os.environ.get("SATE_FACTLOG_DB", "")
    if not database:
        return 0
    path = Path(database)
    for _ in range(25):
        if path.exists():
            break
        time.sleep(0.2)
    else:
        raise SystemExit("fact log database is not ready")
    log = open_log(path, writers=_READERS, readers=_READERS, readonly=True)
    start = registry.projection_cursor()
    cursor = apply_pending(log, registry, start)
    registry.store_projection_cursor(cursor)
    return cursor - start


if __name__ == "__main__":
    main()
