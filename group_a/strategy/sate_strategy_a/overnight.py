"""No overnight directional bias by default **A-UNI-03**."""

from __future__ import annotations


def overnight_bias_allowed(*, constitution_allows: bool) -> bool:
    return constitution_allows


def reject_overnight_carry(*, hold_through_close: bool, constitution_allows: bool) -> bool:
    if not hold_through_close:
        return False
    return not overnight_bias_allowed(constitution_allows=constitution_allows)
