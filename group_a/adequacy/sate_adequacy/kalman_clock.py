"""Kalman freeze clock for **A-SIM-07**."""

from __future__ import annotations

from sate_factlog.log import FactLog


def kalman_frozen_months_from_log(
    log: FactLog,
    *,
    reader_id: str = "sim-ops-a",
    as_of: str,
) -> float | None:
    rows = log.replay_through(group_scope="A", as_of=as_of, reader_id=reader_id)
    for row in reversed(rows):
        if row.payload.get("artifact") == "kalman_innovation_sigma":
            frozen_at = row.occurred_at
            start = frozen_at[:10] + "T00:00:00Z"
            from sate_adequacy.sim_clock import SimPeriod

            return SimPeriod(started_at=start, as_of=as_of).months_elapsed
    return None


def parameter_changes_last_3_months(frozen_months: float | None) -> int:
    if frozen_months is None:
        return 1
    return 0 if frozen_months >= 3.0 else 1
