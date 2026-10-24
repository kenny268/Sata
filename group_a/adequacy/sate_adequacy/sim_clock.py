"""SIM calendar period tracking (**A-SIM-01**, Phase 23)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SIM_MONTHS_REQUIRED = 6.0
_DAY_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class SimPeriod:
    started_at: str
    as_of: str

    @property
    def months_elapsed(self) -> float:
        start = datetime.strptime(self.started_at, _DAY_FORMAT)
        end = datetime.strptime(self.as_of, _DAY_FORMAT)
        delta_days = (end - start).days
        return max(delta_days / 30.4375, 0.0)

    @property
    def calendar_gate_met(self) -> bool:
        return self.months_elapsed >= SIM_MONTHS_REQUIRED


def period_from_env(*, as_of: str, start: str | None) -> SimPeriod:
    if not start:
        raise ValueError("SIM period start is required")
    return SimPeriod(started_at=start, as_of=as_of)
