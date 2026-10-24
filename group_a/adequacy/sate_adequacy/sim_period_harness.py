"""Accelerated 6-month SIM evidence for CI (**Phase 23** harness — not a calendar claim)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sate_factlog.log import FactLog
from sate_strategy_a.kalman_evidence import record_kalman_frozen

from sate_adequacy.evidence_ledger import SimDayRecord, persist_day, persist_period_start
from sate_adequacy.ops_drills import persist_drill, run_all_drills


def _add_months(iso: str, months: int) -> str:
    start = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
    return (start + timedelta(days=months * 30)).strftime("%Y-%m-%dT%H:%M:%SZ")


def seed_six_month_evidence(
    log: FactLog,
    *,
    period_start: str = "2026-04-23T00:00:00Z",
    as_of: str = "2026-10-23T21:00:00Z",
    days: int = 184,
) -> None:
    persist_period_start(log, started_at=period_start, recorded_at=period_start)
    frozen_at = _add_months(period_start, 3)
    record_kalman_frozen(log, at=frozen_at)
    for index in range(days):
        day = (datetime.strptime(period_start, "%Y-%m-%dT%H:%M:%SZ") + timedelta(days=index)).strftime(
            "%Y-%m-%d"
        )
        at = f"{day}T12:00:00Z"
        persist_day(
            log,
            SimDayRecord(
                day=day,
                sessions=2,
                recon_clean_sessions=2,
                trades=2,
                untradeable_sessions=0,
                l2_plus_events=0,
                floor_sizing=True,
            ),
            at=at,
        )
    for result in run_all_drills().results:
        persist_drill(log, result, at=as_of)
