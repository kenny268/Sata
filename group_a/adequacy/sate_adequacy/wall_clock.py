"""Operator wall-clock claim (**six_month_wall_clock_elapsed**)."""

from __future__ import annotations

import os

from sate_adequacy.sim_clock import SimPeriod


def operator_wall_clock_elapsed(*, period: SimPeriod) -> bool:
    """True only when operator explicitly attests live calendar elapsed."""
    flag = os.environ.get("SATE_SIM_WALL_CLOCK_ELAPSED", "").lower()
    if flag not in {"1", "true", "yes"}:
        return False
    return period.calendar_gate_met
