"""Persist Appendix D assumption entries to the fact log."""

from __future__ import annotations

from sate_factlog.log import FactLog


def persist_assumption(log: FactLog, entry: dict[str, str], *, event_id: str, at: str) -> None:
    required = {"assumption_id", "assumption", "verification_method", "verified_at"}
    if not required.issubset(entry.keys()):
        raise ValueError("appendix D entry is incomplete")
    log.append(
        event_id=event_id,
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id=event_id,
        writer_id="monitoring",
        payload={"appendix_d": entry},
    )
