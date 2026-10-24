"""Promotion gate constants **A-PR-06** — live path cannot change params."""

from __future__ import annotations

FROZEN_KALMAN_INNOVATION_SIGMA = 2.5
FROZEN_SIM_EVIDENCE_MONTHS = 3
MP_INFRA_ONLY = ("MP-01", "MP-02", "MP-03")


def live_parameter_change_allowed() -> bool:
    return False
