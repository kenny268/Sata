"""Kernel safe window scheduling stub (§4.3 step 5)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SafeWindow:
    scheduled_at: str
    flat_required: bool = True

    def ready(self) -> bool:
        return True
