"""SEC-06 — every Telegram interaction is logged."""

from __future__ import annotations

from sate_factlog.log import FactLog


def log_telegram(
    log: FactLog,
    *,
    message_id: str,
    principal: str,
    scope: str,
    category: str,
    severity: str,
    resulting_event: str,
    event_id: str,
    occurred_at: str,
    recorded_at: str,
    correlation_id: str,
) -> None:
    if scope not in {"A", "B", "GLOBAL"}:
        raise ValueError("telegram scope must be A, B, or GLOBAL")
    log.append(
        event_id=event_id,
        event_type="telegram",
        group_scope=scope if scope != "GLOBAL" else "GLOBAL",
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        correlation_id=correlation_id,
        writer_id="notifier-bot",
        payload={
            "message_id": message_id,
            "principal": principal,
            "scope": scope,
            "category": category,
            "severity": severity,
            "resulting_event": resulting_event,
        },
    )
