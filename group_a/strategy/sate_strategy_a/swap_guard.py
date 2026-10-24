"""Swap-cost guard **TS-09**, **A-EXE-02** (strategy pre-kernel)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SwapGuardResult:
    allowed: bool
    reason: str = ""


def check_swap_guard(
    *,
    estimated_swap: float,
    swap_budget: float,
    hold_includes_wednesday: bool,
    wednesday_triple: bool = True,
) -> SwapGuardResult:
    cost = estimated_swap
    if wednesday_triple and hold_includes_wednesday:
        cost *= 3
    if cost > swap_budget:
        return SwapGuardResult(allowed=False, reason="swap_guard")
    return SwapGuardResult(allowed=True)
