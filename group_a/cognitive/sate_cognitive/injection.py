"""Injection-safe handling **A-COG-03**."""

from __future__ import annotations

_FORBIDDEN = (
    "ignore previous",
    "system prompt",
    "execute order",
    "place trade",
    "kernel bypass",
    "disregard constitution",
)


def evidence_is_safe(text: str) -> bool:
    lowered = text.lower()
    return not any(needle in lowered for needle in _FORBIDDEN)
