"""Persist Phase 23 gate report to the fact log."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_adequacy.evidence_ledger import WRITER_ID


def persist_phase23_report(
    log: FactLog,
    *,
    event_id: str,
    report: dict[str, object],
    at: str,
) -> None:
    log.append(
        event_id=event_id,
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="sim-ops-phase23",
        writer_id=WRITER_ID,
        payload={"kind": "phase23_report", **report},
    )
