"""Tick freshness validation (**§5.2**, TS-10)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreshnessResult:
    ok: bool
    age_ms: int
    reason: str = ""


def validate_freshness(*, age_ms: int, max_age_ms: int = 5000) -> FreshnessResult:
    if age_ms < 0:
        return FreshnessResult(ok=False, age_ms=age_ms, reason="negative_age")
    if age_ms > max_age_ms:
        return FreshnessResult(ok=False, age_ms=age_ms, reason="stale_tick")
    return FreshnessResult(ok=True, age_ms=age_ms)
