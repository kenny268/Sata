"""Strategy configuration from deploy env."""

from __future__ import annotations

import os


def regime_unstable_limit() -> int | None:
    raw = os.environ.get("SATE_REGIME_UNSTABLE_N", "").strip()
    if not raw:
        return None
    if not raw.isdigit():
        raise ValueError("SATE_REGIME_UNSTABLE_N must be a positive integer")
    value = int(raw)
    if value <= 0:
        raise ValueError("SATE_REGIME_UNSTABLE_N must be positive")
    return value
