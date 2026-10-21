"""Create the Group A identity database. Does not open a broker connection."""

from __future__ import annotations

import os
from pathlib import Path

from sate_identity.registry import DEFAULT_SCOPE, open_registry


def main() -> None:
    scope = os.environ.get("SATE_GROUP_SCOPE", DEFAULT_SCOPE)
    database = os.environ.get("SATE_IDENTITY_DB", "")
    if not database:
        raise SystemExit("SATE_IDENTITY_DB is required")
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    registry = open_registry(path, scope=scope)
    print(f"identity store ready scope={registry.scope}")


if __name__ == "__main__":
    main()
