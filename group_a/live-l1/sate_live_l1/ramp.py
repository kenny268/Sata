"""Ramp clock (**A-LAD-04–06**, §4.5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

RAMP_FACTOR_L1_START = "0.25"
RAMP_MIN_DAYS = 30
_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class RampState:
    started_at: str
    factor: str = RAMP_FACTOR_L1_START
    quiet_period: bool = True

    @property
    def days_elapsed(self) -> float:
        start = datetime.strptime(self.started_at, _FORMAT)
        end = datetime.now(UTC)
        return max((end - start).days, 0)

    def graduation_allowed(self, *, as_of: str) -> bool:
        start = datetime.strptime(self.started_at, _FORMAT)
        now = datetime.strptime(as_of, _FORMAT)
        return (now - start) >= timedelta(days=RAMP_MIN_DAYS)

    def mode_switch_allowed(self) -> bool:
        if not self.quiet_period:
            return True
        return self.days_elapsed >= RAMP_MIN_DAYS


def initial_ramp(*, started_at: str) -> RampState:
    return RampState(started_at=started_at, factor=RAMP_FACTOR_L1_START, quiet_period=True)
