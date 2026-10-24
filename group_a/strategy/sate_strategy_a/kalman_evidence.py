"""Kalman threshold frozen on SIM evidence **A-SIG-01**."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_strategy_a.promotion import FROZEN_KALMAN_INNOVATION_SIGMA, FROZEN_SIM_EVIDENCE_MONTHS


def record_kalman_frozen(log: FactLog, *, at: str, months: int = FROZEN_SIM_EVIDENCE_MONTHS) -> None:
    log.append(
        event_id=f"kalman-frozen-{at}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="kalman-frozen",
        writer_id="strategy-a",
        payload={
            "artifact": "kalman_innovation_sigma",
            "value": str(FROZEN_KALMAN_INNOVATION_SIGMA),
            "frozen_sim_months": months,
        },
    )
