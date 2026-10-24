"""Wire continuous SIM runner into Phase 23 evidence ledger."""

from __future__ import annotations

import os

from sate_factlog.log import FactLog

from sate_adequacy.evidence_ledger import (
    WRITER_ID,
    period_start_from_log,
    persist_period_start,
    persist_session,
)


def sim_ops_writers() -> frozenset[str]:
    base = {"strategy-a", "kernel-a", "sim-ops-a"}
    return frozenset(base)


def ensure_period_started(log: FactLog, *, at: str) -> None:
    if period_start_from_log(log, reader_id=WRITER_ID, as_of=at):
        return
    start = os.environ.get("SATE_SIM_PERIOD_START", at)
    persist_period_start(log, started_at=start, recorded_at=at)


def record_sim_session(
    log: FactLog,
    *,
    session_id: str,
    journal_logged: bool,
    order_placed: bool,
    verdict: str,
    at: str,
) -> None:
    ensure_period_started(log, at=at)
    persist_session(
        log,
        day=at[:10],
        session_id=session_id,
        journal_logged=journal_logged,
        order_placed=order_placed,
        verdict=verdict,
        at=at,
    )
