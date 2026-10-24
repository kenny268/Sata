"""Fact-log persistence for advisory shadow (**A-COG-04** evidence)."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_cognitive.ingest import IngestResult
from sate_cognitive.shadow import ShadowReport

WRITER_ID = "cognitive-a"


def persist_ingest(
    log: FactLog,
    *,
    event_id: str,
    signal_id: str,
    result: IngestResult,
    at: str,
    correlation_id: str,
) -> None:
    log.append(
        event_id=event_id,
        event_type="advisory_signal",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id=correlation_id,
        writer_id=WRITER_ID,
        payload={
            "kind": "ingest",
            "signal_id": signal_id,
            "ok": result.ok,
            "reason": result.reason,
            "shadow_q": result.shadow_q,
            "shadow_c": result.shadow_c,
            "trading_view": result.trading_view,
        },
    )


def persist_weekly_shadow(
    log: FactLog,
    *,
    event_id: str,
    report: ShadowReport,
    at: str,
) -> None:
    log.append(
        event_id=event_id,
        event_type="advisory_signal",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id=f"shadow-{report.week}",
        writer_id=WRITER_ID,
        payload={"kind": "weekly_shadow", **report.export()},
    )
