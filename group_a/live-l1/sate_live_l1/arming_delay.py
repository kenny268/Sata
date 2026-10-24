"""24h arming delay (**AM-01**, §4.3 step 3)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def arming_delay_hours() -> float:
    raw = os.environ.get("SATE_ARMING_DELAY_HOURS", "24").strip()
    try:
        return max(float(raw), 0.0)
    except ValueError:
        return 24.0


def arming_delay_elapsed(*, started_at: str, as_of: str) -> bool:
    if arming_delay_hours() == 0:
        return True
    start = datetime.strptime(started_at, _FORMAT)
    now = datetime.strptime(as_of, _FORMAT)
    return now - start >= timedelta(hours=arming_delay_hours())
