"""**INV-01–INV-11** harness status for LIVE gate."""

from __future__ import annotations

import os

INVARIANT_IDS = tuple(f"INV-{index:02d}" for index in range(1, 12))


def inv_suite_green(*, env_override: bool | None = None) -> bool:
    if env_override is not None:
        return env_override
    return os.environ.get("SATE_INV_SUITE_GREEN", "").lower() in {"1", "true", "yes"}


def inv_suite_block_reasons(*, env_override: bool | None = None) -> list[str]:
    if inv_suite_green(env_override=env_override):
        return []
    return ["inv_suite_not_green"]
