"""Persist Phase 24 verification report."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_compliance.persist import WRITER_ID


def persist_phase24_report(
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
        correlation_id="broker-verification",
        writer_id=WRITER_ID,
        payload={"kind": "phase24_report", **report},
    )
