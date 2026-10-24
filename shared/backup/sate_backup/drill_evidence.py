"""Record monthly restore drill evidence in the fact log."""

from __future__ import annotations

from sate_factlog.log import FactLog


def record_monthly_drill(
    log: FactLog,
    *,
    month: str,
    chain_ok: bool,
    clean_host: bool,
    at: str,
) -> None:
    if not clean_host:
        raise ValueError("clean host required")
    log.append(
        event_id=f"restore-drill-{month}",
        event_type="deployment",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id=f"restore-drill-{month}",
        writer_id="backup",
        payload={
            "drill": "monthly_restore",
            "month": month,
            "chain_ok": chain_ok,
            "clean_host": clean_host,
        },
    )
